
import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split



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
    np.random.seed(seed)
    profile = ANIMAL_PROFILES.get(animal, ANIMAL_PROFILES["red_kite"])
    behaviors = profile["behaviors"]
    spd_min, spd_max = profile["speed_range"]
    alt_min, alt_max = profile["alt_range"]

    n_phases = min(len(behaviors), 4)
    boundaries = sorted(np.random.choice(range(100, n_points - 100), n_phases - 1, replace=False))
    boundaries = [0] + list(boundaries) + [n_points]

    records = []
    lat, lon = 50.82 + np.random.uniform(-2, 2), 8.77 + np.random.uniform(-2, 2)
    t = pd.Timestamp("2024-03-01 06:00:00")

    for i in range(n_phases):
        behavior = behaviors[i % len(behaviors)]
        n = boundaries[i + 1] - boundaries[i]

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
        else:
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


_MOVEBANK_USE_COLS = [
    "timestamp", "location-lat", "location-long",
    "ground-speed", "height-above-msl", "true_behavior",
]
_MOVEBANK_DTYPES = {
    "ground-speed":     "float32",
    "height-above-msl": "float32",
}


def load_movebank_csv(filepath: str, chunksize: int = 500_000) -> pd.DataFrame:
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



def extract_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    R = 6_371_000
    feat = df
    lats  = feat["location-lat"].values.astype(np.float64)
    lons  = feat["location-long"].values.astype(np.float64)
    times = (pd.to_datetime(feat["timestamp"]).astype(np.int64) // 1e9).values.astype(np.float64)

    n = len(feat)
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

    turning = np.zeros(n, dtype=np.float32)
    if n > 2:
        diff = bearings[2:].astype(np.float64) - bearings[1:-1].astype(np.float64)
        turning[1:-1] = np.abs((diff + 180) % 360 - 180)
    feat["turning_angle"] = turning

    straight = np.zeros(n, dtype=np.float32)
    if n > window:
        lat_a = lats[:n - window]; lat_b = lats[window:]
        lon_a = lons[:n - window]; lon_b = lons[window:]
        phi1 = np.radians(lat_a); phi2 = np.radians(lat_b)
        dphi = phi2 - phi1
        dl   = np.radians(lon_b - lon_a)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dl/2)**2
        net = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        tot_full = pd.Series(step_len.astype(np.float64)).rolling(window=window).sum().values
        tot = tot_full[window:n]

        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.where(tot > 0, net / np.where(tot > 0, tot, 1), 0.0)
        straight[window:n] = vals
    feat["straightness"] = straight

    feat["speed_ms"] = (feat.get("ground-speed", pd.Series(np.zeros(n))).fillna(
        pd.Series(step_len.astype(np.float64) / np.where(time_delta > 0, time_delta, 1))
    ).fillna(0)).astype(np.float32)

    feat["altitude_m"] = feat.get("height-above-msl", pd.Series(np.zeros(n))).fillna(0).astype(np.float32)

    feat["speed_roll_mean"] = feat["speed_ms"].rolling(window, center=True, min_periods=1).mean().astype(np.float32)
    feat["speed_roll_std"]  = feat["speed_ms"].rolling(window, center=True, min_periods=1).std().fillna(0).astype(np.float32)
    feat["alt_roll_mean"]   = feat["altitude_m"].rolling(window, center=True, min_periods=1).mean().astype(np.float32)

    return feat


FEATURE_COLS = [
    "speed_ms", "altitude_m", "turning_angle", "straightness",
    "speed_roll_mean", "speed_roll_std", "step_length_m", "alt_roll_mean",
]



class DataPipeline:

    def __init__(
        self,
        animal:    str = "red_kite",
        n_points:  int = 1200,
        scaler:    str = "standard",
        test_size: float = 0.2,
        seed:      int = 42,
        csv_path:  Optional[str] = None,
        keep_intermediate: bool = False,
    ):
        self.animal    = animal
        self.n_points  = n_points
        self.test_size = test_size
        self.seed      = seed

        if csv_path:
            raw_df = load_movebank_csv(csv_path)
        else:
            raw_df = generate_animal_track(animal, n_points, seed)

        feat_df = extract_features(raw_df)

        X_full = feat_df[FEATURE_COLS].fillna(0).values

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

        if keep_intermediate:
            self.raw_df  = raw_df
            self.feat_df = feat_df
        else:
            self.raw_df  = None
            self.feat_df = None
            del raw_df, feat_df
            import gc
            gc.collect()

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

        split = int(len(X_full) * (1 - test_size))
        self.X_train = X_full[:split]
        self.X_test  = X_full[split:]
        self.y_train = y_full[:split] if y_full is not None else None
        self.y_test  = y_full[split:] if y_full is not None else None

    def get_splits(self) -> Tuple:
        return self.X_train, self.X_test, self.y_train, self.y_test

    def get_full(self) -> Tuple:
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
