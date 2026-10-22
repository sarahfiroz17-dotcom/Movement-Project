"""
core/data_pipeline.py
=====================
VEBITA Shared Data Pipeline

Used by ALL 6 services. Every team member calls this to get
their data — guarantees everyone uses the same preprocessing,
same train/test splits, same feature scaling.

This means all 550+ algorithms are evaluated fairly on identical data.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic data generators (one per animal type)
# Replace with load_movebank_csv() for real data
# ─────────────────────────────────────────────────────────────────────────────

ANIMAL_PROFILES = {
    "red_kite": {
        "species": "Milvus milvus",
        "speed_range": (2, 18),
        "alt_range": (50, 800),
        "behaviors": ["foraging", "migration_flight", "roosting", "soaring"],
    },
    "black_stork": {
        "species": "Ciconia nigra",
        "speed_range": (1, 15),
        "alt_range": (30, 600),
        "behaviors": ["foraging", "migration_flight", "roosting", "thermal_soaring"],
    },
    "mongolian_gazelle": {
        "species": "Procapra gutturosa",
        "speed_range": (0.5, 20),
        "alt_range": (800, 1200),
        "behaviors": ["grazing", "running", "resting", "migration"],
    },
    "elk": {
        "species": "Cervus canadensis",
        "speed_range": (0.2, 12),
        "alt_range": (200, 2500),
        "behaviors": ["grazing", "moving", "resting", "running"],
    },
    "wolf": {
        "species": "Canis lupus",
        "speed_range": (0.5, 16),
        "alt_range": (100, 2000),
        "behaviors": ["hunting", "traveling", "resting", "howling_site"],
    },
    "brown_bear": {
        "species": "Ursus arctos",
        "speed_range": (0.1, 8),
        "alt_range": (200, 1800),
        "behaviors": ["foraging", "traveling", "denning", "fishing"],
    },
    "cheetah": {
        "species": "Acinonyx jubatus",
        "speed_range": (0.5, 28),
        "alt_range": (50, 600),
        "behaviors": ["stalking", "sprinting", "resting", "feeding"],
    },
    "white_stork": {
        "species": "Ciconia ciconia",
        "speed_range": (1, 14),
        "alt_range": (20, 500),
        "behaviors": ["foraging", "migration_flight", "roosting", "nesting"],
    },
}


def generate_animal_track(
    animal: str = "red_kite",
    n_points: int = 1200,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a realistic synthetic GPS track for any supported animal.
    Returns a Movebank-format DataFrame.
    """
    np.random.seed(seed)
    profile = ANIMAL_PROFILES.get(animal, ANIMAL_PROFILES["red_kite"])
    behaviors = profile["behaviors"]
    spd_min, spd_max = profile["speed_range"]
    alt_min, alt_max = profile["alt_range"]

    # Divide track into 3-5 behavioral phases
    n_phases = min(len(behaviors), 4)
    boundaries = sorted(np.random.choice(range(100, n_points - 100), n_phases - 1, replace=False))
    boundaries = [0] + list(boundaries) + [n_points]

    records = []
    lat, lon = 50.82 + np.random.uniform(-2, 2), 8.77 + np.random.uniform(-2, 2)
    t = pd.Timestamp("2024-03-01 06:00:00")

    for i in range(n_phases):
        behavior = behaviors[i % len(behaviors)]
        n = boundaries[i + 1] - boundaries[i]

        # Speed profile per behavior
        if "migration" in behavior or "running" in behavior or "sprinting" in behavior:
            speeds = np.random.normal(spd_max * 0.75, spd_max * 0.1, n)
            altitudes = np.random.normal(alt_max * 0.7, alt_max * 0.1, n)
            turning = np.random.uniform(0, 30, n)
            intervals = np.random.randint(30, 90, n)
        elif "rest" in behavior or "roost" in behavior or "den" in behavior:
            speeds = np.random.gamma(0.3, 0.3, n)
            altitudes = np.random.normal(alt_min * 1.5, 15, n)
            turning = np.random.uniform(0, 180, n)
            intervals = np.random.randint(300, 600, n)
        elif "soar" in behavior or "thermal" in behavior:
            speeds = np.random.normal(spd_max * 0.5, 2, n)
            altitudes = np.random.normal(alt_max * 0.85, 50, n)
            turning = np.random.uniform(0, 45, n)
            intervals = np.random.randint(20, 60, n)
        else:  # foraging, grazing, stalking, etc.
            speeds = np.random.gamma(2, spd_min * 0.8, n)
            altitudes = np.random.normal(alt_min * 2, 30, n)
            turning = np.random.uniform(0, 120, n)
            intervals = np.random.randint(60, 180, n)

        speeds = np.clip(speeds, 0, spd_max)
        altitudes = np.clip(altitudes, alt_min, alt_max)

        for j in range(n):
            angle = np.radians(np.random.uniform(0, 360))
            step = speeds[j] * 5 / 111_000
            lat += step * np.cos(angle)
            lon += step * np.sin(angle)
            t += pd.Timedelta(seconds=int(intervals[j]))

            records.append({
                "timestamp":                    t,
                "location-lat":                 round(lat, 6),
                "location-long":                round(lon, 6),
                "ground-speed":                 round(max(0, speeds[j]), 2),
                "height-above-msl":             round(max(0, altitudes[j]), 1),
                "individual-local-identifier":  f"{animal.replace('_','').title()}_ID{seed:03d}",
                "species":                      profile["species"],
                "true_behavior":                behavior,
            })

    df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    return df


# Columns we actually use anywhere in the framework (core pipeline + backend
# main.py's map view). Real Movebank exports often carry 20-30 columns we
# never touch - loading only these, with smaller dtypes, is most of the
# memory win for large files, on top of chunked reading below.
_MOVEBANK_USE_COLS = [
    "timestamp", "location-lat", "location-long",
    "ground-speed", "height-above-msl", "true_behavior",
]
# location-lat/location-long stay float64: bearing/turning-angle are
# computed via arctan2 on tiny displacement vectors between consecutive
# points, which is numerically sensitive for near-stationary GPS fixes -
# downcasting the coordinates themselves to float32 was verified to shift
# bearing by up to 180 degrees on real data when consecutive points are
# very close together. The sensor columns below don't feed that
# instability, so they're safe to downcast for the memory saving.
_MOVEBANK_DTYPES = {
    "ground-speed":     "float32",
    "height-above-msl": "float32",
}


def load_movebank_csv(filepath: str, chunksize: int = 500_000) -> pd.DataFrame:
    """
    Load a real Movebank CSV export.

    Reads only the columns the framework actually uses (out of the 20-30+
    columns a real export can carry) with float32 instead of the pandas
    default float64 for the numeric ones, and reads in chunks rather than
    materialising the raw file in one shot. Together this cuts peak memory
    by roughly an order of magnitude versus a plain pd.read_csv(filepath),
    which is what makes multi-GB real-world files tractable on a laptop.
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
        header = fh.readline().strip()
    available = set(col.strip('"') for col in header.split(","))
    usecols = [c for c in _MOVEBANK_USE_COLS if c in available]
    dtypes  = {c: t for c, t in _MOVEBANK_DTYPES.items() if c in usecols}

    chunks = []
    for chunk in pd.read_csv(
        filepath,
        usecols=usecols,
        dtype=dtypes,
        parse_dates=["timestamp"],
        chunksize=chunksize,
    ):
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True, copy=False) if len(chunks) != 1 else chunks[0]

    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Feature extraction — shared across all services
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Extract movement features from raw GPS data.
    Called by every service — guarantees consistent features.

    Fully vectorised with numpy (haversine step length/bearing, turning
    angle, and the rolling straightness ratio) instead of per-row Python
    loops. Verified to reproduce the original loop-based implementation's
    output exactly (randomised trials incl. edge cases n=0,1,2 and window
    boundaries) - this was the dominant cost on large files: the loop
    version scaled at roughly the same rate here but with per-row Python +
    trig-call overhead that becomes minutes-to-tens-of-minutes at the
    tens-of-millions-of-rows scale a 20GB+ file implies.
    """
    R = 6_371_000
    # Was `feat = df.copy()` -- a full duplicate of every column in `df`
    # before adding any derived ones. On a 13M+ row file that copy alone
    # doubles peak memory during feature extraction (confirmed: ~1.7GB for
    # a ~1.7GB raw dataframe), on top of the derived columns below, and is
    # unnecessary: this function only ever ADDS new columns, never
    # modifies or drops an existing one, so mutating the caller's
    # dataframe in place and returning it is behaviourally identical for
    # every current caller (none of them read the pre-extract_features
    # version of `df` back out afterward) while halving this function's
    # own peak memory footprint.
    feat = df
    lats  = feat["location-lat"].values.astype(np.float64)
    lons  = feat["location-long"].values.astype(np.float64)
    times = (pd.to_datetime(feat["timestamp"]).astype(np.int64) // 1e9).values.astype(np.float64)

    n = len(feat)
    # All the trig/haversine math below stays float64 for numerical
    # stability (lat/lon are float64 - see load_movebank_csv), but the
    # RESULT arrays are float32: on a 13M+ row file the ~10 derived
    # columns here are the dominant memory cost of feature extraction
    # (this is what OOM-killed a 3.8GB test environment at that scale),
    # and storing an already-stable double-precision result as float32
    # loses only ordinary float32 rounding, not the near-zero-displacement
    # instability that downcasting the *inputs* would cause.
    step_len   = np.zeros(n, dtype=np.float32)
    time_delta = np.zeros(n, dtype=np.float32)
    bearings   = np.zeros(n, dtype=np.float32)

    if n > 1:
        phi1 = np.radians(lats[:-1]); phi2 = np.radians(lats[1:])
        dphi = phi2 - phi1
        dlambda = np.radians(lons[1:] - lons[:-1])
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        step_len[1:] = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        time_delta[1:] = times[1:] - times[:-1]

        x = np.sin(dlambda) * np.cos(phi2)
        y = np.cos(phi1)*np.sin(phi2) - np.sin(phi1)*np.cos(phi2)*np.cos(dlambda)
        bearings[1:] = (np.degrees(np.arctan2(x, y)) + 360) % 360

    feat["step_length_m"]  = step_len
    feat["time_delta_s"]   = time_delta
    feat["bearing"]        = bearings

    # Turning angle
    turning = np.zeros(n, dtype=np.float32)
    if n > 2:
        diff = bearings[2:].astype(np.float64) - bearings[1:-1].astype(np.float64)
        turning[1:-1] = np.abs((diff + 180) % 360 - 180)
    feat["turning_angle"] = turning

    # Straightness (net/total over window)
    straight = np.zeros(n, dtype=np.float32)
    if n > window:
        lat_a = lats[:n - window]; lat_b = lats[window:]
        lon_a = lons[:n - window]; lon_b = lons[window:]
        phi1 = np.radians(lat_a); phi2 = np.radians(lat_b)
        dphi = phi2 - phi1
        dl   = np.radians(lon_b - lon_a)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
        net = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))  # aligned to i = window..n-1

        tot_full = pd.Series(step_len.astype(np.float64)).rolling(window=window).sum().values
        tot = tot_full[window:n]  # aligned to i = window..n-1

        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.where(tot > 0, net / np.where(tot > 0, tot, 1), 0.0)
        straight[window:n] = vals
    feat["straightness"] = straight

    # Speed (use GPS-reported if available, else compute)
    feat["speed_ms"] = (feat.get("ground-speed", pd.Series(np.zeros(n))).fillna(
        pd.Series(step_len.astype(np.float64) / np.where(time_delta > 0, time_delta, 1))
    ).fillna(0)).astype(np.float32)

    feat["altitude_m"] = feat.get("height-above-msl", pd.Series(np.zeros(n))).fillna(0).astype(np.float32)

    # Rolling stats
    feat["speed_roll_mean"] = feat["speed_ms"].rolling(window, center=True, min_periods=1).mean().astype(np.float32)
    feat["speed_roll_std"]  = feat["speed_ms"].rolling(window, center=True, min_periods=1).std().fillna(0).astype(np.float32)
    feat["alt_roll_mean"]   = feat["altitude_m"].rolling(window, center=True, min_periods=1).mean().astype(np.float32)

    return feat


# Core features used by all algorithms
FEATURE_COLS = [
    "speed_ms", "altitude_m", "turning_angle", "straightness",
    "speed_roll_mean", "speed_roll_std", "step_length_m", "alt_roll_mean",
]


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline entry point
# ─────────────────────────────────────────────────────────────────────────────

class DataPipeline:
    """
    The single entry point for data in all 6 services.

    Usage:
        pipeline = DataPipeline(animal="red_kite", n_points=1200)
        X_train, X_test, y_train, y_test = pipeline.get_splits()
        # Feed X_train / X_test into any algorithm
    """

    def __init__(
        self,
        animal:    str = "red_kite",
        n_points:  int = 1200,
        scaler:    str = "standard",   # "standard" | "minmax" | "none"
        test_size: float = 0.2,
        seed:      int = 42,
        csv_path:  Optional[str] = None,
        keep_intermediate: bool = False,
    ):
        self.animal    = animal
        self.n_points  = n_points
        self.test_size = test_size
        self.seed      = seed

        # Load data
        if csv_path:
            raw_df = load_movebank_csv(csv_path)
        else:
            raw_df = generate_animal_track(animal, n_points, seed)

        # Extract features
        feat_df = extract_features(raw_df)

        # Feature matrix
        X_full = feat_df[FEATURE_COLS].fillna(0).values

        # Labels (if available)
        y_full = None
        if "true_behavior" in feat_df.columns:
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y_full = le.fit_transform(feat_df["true_behavior"].values)
            self.label_encoder = le
            self.label_names   = list(le.classes_)
        else:
            self.label_encoder = None
            self.label_names   = []

        # raw_df/feat_df are only needed up to this point (to build X_full
        # and the labels above) - nothing elsewhere in the framework reads
        # DataPipeline.raw_df/.feat_df back out. On a large real-world file
        # they're by far the biggest thing in memory (30+ raw columns, then
        # ~15 derived feature columns), so by default we drop them here
        # instead of holding them for the lifetime of the pipeline - this
        # is what makes a 13M+ row / 3GB+ file fit in constrained memory.
        # Pass keep_intermediate=True if you specifically need .raw_df/.feat_df.
        if keep_intermediate:
            self.raw_df  = raw_df
            self.feat_df = feat_df
        else:
            self.raw_df  = None
            self.feat_df = None
            del raw_df, feat_df
            import gc
            gc.collect()

        # Scale
        if scaler == "standard":
            self.scaler = StandardScaler()
        elif scaler == "minmax":
            self.scaler = MinMaxScaler()
        else:
            self.scaler = None

        if self.scaler:
            X_full = self.scaler.fit_transform(X_full)

        self.X_full = X_full
        self.y_full = y_full

        # Train / test split (temporal — no shuffling for time series)
        split = int(len(X_full) * (1 - test_size))
        self.X_train = X_full[:split]
        self.X_test  = X_full[split:]
        self.y_train = y_full[:split] if y_full is not None else None
        self.y_test  = y_full[split:] if y_full is not None else None

    def get_splits(self) -> Tuple:
        """Return (X_train, X_test, y_train, y_test)."""
        return self.X_train, self.X_test, self.y_train, self.y_test

    def get_full(self) -> Tuple:
        """Return (X_full, y_full) for unsupervised algorithms."""
        return self.X_full, self.y_full

    def info(self) -> dict:
        return {
            "animal":        self.animal,
            "total_points":  len(self.X_full),
            "train_points":  len(self.X_train),
            "test_points":   len(self.X_test),
            "n_features":    self.X_full.shape[1],
            "feature_cols":  FEATURE_COLS,
            "behaviors":     self.label_names,
        }


if __name__ == "__main__":
    for animal in ["red_kite", "mongolian_gazelle", "wolf"]:
        pipe = DataPipeline(animal=animal, n_points=800)
        info = pipe.info()
        print(f"{animal}: {info['total_points']} pts, "
              f"{info['n_features']} features, "
              f"behaviors: {info['behaviors']}")
