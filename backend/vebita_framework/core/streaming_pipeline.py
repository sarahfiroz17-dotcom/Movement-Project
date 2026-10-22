"""
core/streaming_pipeline.py
===========================
Memory-BOUNDED ("out-of-core") loading + feature extraction for Movebank
CSVs too large to fit in RAM at once — a 15-20GB+ file should load in
roughly the same peak memory as a 3GB one.

Why this is needed (not just "read in chunks"):
-------------------------------------------------
`data_pipeline.load_movebank_csv` already reads the CSV in chunks, but
still concatenates every chunk into ONE full-size in-memory DataFrame and
then sorts the whole thing by timestamp. `extract_features` then builds
~8 more full-length derived columns on top of that. All of that is
O(total rows) memory — it just moves the ceiling up a bit, it doesn't
remove it. A file a few times bigger than the current largest ~3GB one
will blow straight through it.

The sort is the part that actually forces everything into memory at once,
and it can't just be skipped: real Movebank exports are NOT reliably in
timestamp order (verified directly on the real SW Germany stork file —
sampling every 500,000th row, 12 of 27 samples were out of order, almost
certainly because multiple individuals' fixes are interleaved), and every
downstream feature here (bearing, turning angle, straightness, the
rolling stats) depends on true chronological order per point.

So this module does a real *external merge sort* (the classic
bounded-memory algorithm for "sort a file bigger than RAM"):

  1. RUN GENERATION — stream the CSV in chunks, sort each chunk (small,
     bounded size) in memory, and spill each sorted chunk's columns to
     disk as flat, memmap-friendly .npy files ("runs").
  2. K-WAY MERGE — merge all the sorted runs into true global timestamp
     order using only a small read-buffer per run at any time (not the
     whole run, and never the whole dataset).
  3. STREAMING FEATURE EXTRACTION — as globally-sorted rows come off the
     merge, compute the *exact same* vectorised formulas as
     `data_pipeline.extract_features`, but on small overlapping blocks
     (carrying `window` rows of real context from one block to the next)
     instead of the whole array, writing results directly into pre-sized
     output files on disk (numpy memmap) instead of an in-RAM array.

Peak memory throughout is bounded by chunk/buffer sizes, which are fixed
constants — NOT by the number of rows in the file.

The public entry point, `load_and_extract_features_streaming()`, returns
memmap-backed numpy arrays with the identical shape/dtype/semantics as
what `main.load_dataset_features()` used to build in memory: X
(FEATURE_COLS, float32), y (int, or None), label_names (list[str]), lats,
lons (float64). Every existing caller already only ever reads bounded
slices out of these (thanks to the earlier `_subsample`/batching fixes
across all 150 algorithms), so a memmap is a drop-in replacement — no
algorithm code needs to change.
"""

import os
import glob
import shutil
import sys
import numpy as np
import pandas as pd

if sys.platform != "win32":
    import resource

from .data_pipeline import _MOVEBANK_USE_COLS, _MOVEBANK_DTYPES, FEATURE_COLS

R_EARTH = 6_371_000


def _raise_open_file_limit():
    """
    The external merge sort keeps one open (memmapped) file handle per
    sorted run per column (up to 6 columns: ts/lat/lon/speed/alt/beh).
    At normal scale (a handful to a few dozen runs) this is a non-issue,
    but a very large dataset can produce enough runs that the process's
    default open-file limit becomes the real ceiling -- especially on
    macOS, where a plain shell's default soft limit is often just 256.
    Raise it, best-effort, so "biggest file possible" isn't quietly
    capped by file descriptors rather than memory or disk. Safe to call
    repeatedly; never raises on its own.
    """
    if sys.platform == "win32":
        return  # Windows manages file handles differently; no action needed
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        ceiling = hard if hard != resource.RLIM_INFINITY else 1_000_000
        target = min(ceiling, 65_536)
        if soft < target:
            resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    except Exception:
        pass  # best-effort only -- fall back to whatever limit already applies


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — run generation: chunk, sort each chunk, spill to disk
# ─────────────────────────────────────────────────────────────────────────────

def _make_run_dir(cache_dir):
    run_dir = os.path.join(cache_dir, "_runs")
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir)
    os.makedirs(run_dir)
    return run_dir


def _generate_sorted_runs(filepath, run_dir, chunk_rows, has_speed, has_alt, has_behavior, behavior_vocab):
    """
    Stream the CSV in chunks of `chunk_rows`, sort each chunk by timestamp
    (bounded-size in-memory sort), and write each sorted chunk's columns
    as separate flat .npy files under run_dir/run_<k>_<col>.npy.

    Returns (n_runs, total_n).
    """
    usecols = ["timestamp", "location-lat", "location-long"]
    if has_speed:
        usecols.append("ground-speed")
    if has_alt:
        usecols.append("height-above-msl")
    if has_behavior:
        usecols.append("true_behavior")
    dtypes = {c: t for c, t in _MOVEBANK_DTYPES.items() if c in usecols}

    n_runs = 0
    total_n = 0
    for chunk in pd.read_csv(
        filepath, usecols=usecols, dtype=dtypes,
        parse_dates=["timestamp"], chunksize=chunk_rows,
    ):
        n = len(chunk)
        if n == 0:
            continue

        ts_ns = chunk["timestamp"].values.astype("datetime64[ns]").astype(np.int64)
        lat   = chunk["location-lat"].values.astype(np.float64)
        lon   = chunk["location-long"].values.astype(np.float64)

        order = np.argsort(ts_ns, kind="stable")
        ts_ns = ts_ns[order]
        lat   = lat[order]
        lon   = lon[order]

        np.save(os.path.join(run_dir, f"run_{n_runs}_ts.npy"), ts_ns)
        np.save(os.path.join(run_dir, f"run_{n_runs}_lat.npy"), lat)
        np.save(os.path.join(run_dir, f"run_{n_runs}_lon.npy"), lon)

        if has_speed:
            speed = chunk["ground-speed"].values.astype(np.float32)[order]
            np.save(os.path.join(run_dir, f"run_{n_runs}_speed.npy"), speed)
        if has_alt:
            alt = chunk["height-above-msl"].values.astype(np.float32)[order]
            np.save(os.path.join(run_dir, f"run_{n_runs}_alt.npy"), alt)
        if has_behavior:
            beh_raw = chunk["true_behavior"].values[order]
            beh_code = np.array(
                [behavior_vocab.get(v if pd.notna(v) else "__nan__", -1) for v in beh_raw],
                dtype=np.int32,
            )
            np.save(os.path.join(run_dir, f"run_{n_runs}_beh.npy"), beh_code)

        n_runs += 1
        total_n += n

        # Free this chunk's memory before reading the next one — pandas'
        # own chunked reader already only holds one chunk at a time, but
        # being explicit here costs nothing and removes any doubt.
        del chunk, ts_ns, lat, lon, order

    return n_runs, total_n


def _collect_behavior_vocab(filepath, has_behavior):
    """
    Build the true_behavior -> integer code mapping ONCE, up front, the
    same way sklearn's LabelEncoder does (codes assigned in sorted order
    of the unique string values) — but from a single cheap single-column
    pass instead of holding the whole dataset in memory to call
    LabelEncoder on it directly. Missing/NaN values are bucketed under
    the sentinel key "__nan__" so they still get a stable code rather
    than crashing a downstream sort/compare on a real float NaN mixed
    with strings.

    Returns (vocab_dict, label_names) — label_names is already in the
    same order as the assigned codes (label_names[code] == original
    string), matching LabelEncoder.classes_ semantics. If the file has no
    real (non-null) behavior values at all, returns ({}, []) so callers
    can treat this exactly like "no true_behavior column".
    """
    if not has_behavior:
        return {}, []

    seen = set()
    for chunk in pd.read_csv(filepath, usecols=["true_behavior"], chunksize=1_000_000):
        vals = chunk["true_behavior"].dropna().unique()
        seen.update(vals.tolist())

    if not seen:
        return {}, []

    label_names = sorted(seen)
    vocab = {name: i for i, name in enumerate(label_names)}
    return vocab, label_names


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 + 3 — k-way merge of the sorted runs, streamed straight into the
# same windowed feature formulas as data_pipeline.extract_features
# ─────────────────────────────────────────────────────────────────────────────

class _RunReader:
    """A small read-ahead buffer over one sorted run's on-disk columns.

    Backed by memmap so refilling the buffer only pages in the slice
    actually requested, not the whole run file.
    """

    def __init__(self, run_dir, idx, has_speed, has_alt, has_behavior, buf_size):
        self.ts_mm = np.load(os.path.join(run_dir, f"run_{idx}_ts.npy"), mmap_mode="r")
        self.lat_mm = np.load(os.path.join(run_dir, f"run_{idx}_lat.npy"), mmap_mode="r")
        self.lon_mm = np.load(os.path.join(run_dir, f"run_{idx}_lon.npy"), mmap_mode="r")
        self.speed_mm = (
            np.load(os.path.join(run_dir, f"run_{idx}_speed.npy"), mmap_mode="r") if has_speed else None
        )
        self.alt_mm = (
            np.load(os.path.join(run_dir, f"run_{idx}_alt.npy"), mmap_mode="r") if has_alt else None
        )
        self.beh_mm = (
            np.load(os.path.join(run_dir, f"run_{idx}_beh.npy"), mmap_mode="r") if has_behavior else None
        )
        self.n = len(self.ts_mm)
        self.pos = 0          # how many rows of this run have been consumed so far
        self.buf_size = buf_size
        self.buf_ts = np.empty(0, dtype=np.int64)
        self.buf_lat = np.empty(0, dtype=np.float64)
        self.buf_lon = np.empty(0, dtype=np.float64)
        self.buf_speed = np.empty(0, dtype=np.float32) if has_speed else None
        self.buf_alt = np.empty(0, dtype=np.float32) if has_alt else None
        self.buf_beh = np.empty(0, dtype=np.int32) if has_behavior else None

    def exhausted(self):
        return self.pos >= self.n and len(self.buf_ts) == 0

    def ensure_buffer(self):
        """Top the buffer back up from disk if it's run low and more data remains."""
        if len(self.buf_ts) > 0 or self.pos >= self.n:
            return
        end = min(self.pos + self.buf_size, self.n)
        self.buf_ts = np.array(self.ts_mm[self.pos:end])
        self.buf_lat = np.array(self.lat_mm[self.pos:end])
        self.buf_lon = np.array(self.lon_mm[self.pos:end])
        if self.speed_mm is not None:
            self.buf_speed = np.array(self.speed_mm[self.pos:end])
        if self.alt_mm is not None:
            self.buf_alt = np.array(self.alt_mm[self.pos:end])
        if self.beh_mm is not None:
            self.buf_beh = np.array(self.beh_mm[self.pos:end])
        self.pos = end

    def take(self, k):
        """Remove and return the first k rows of the current buffer."""
        out_ts, self.buf_ts = self.buf_ts[:k], self.buf_ts[k:]
        out_lat, self.buf_lat = self.buf_lat[:k], self.buf_lat[k:]
        out_lon, self.buf_lon = self.buf_lon[:k], self.buf_lon[k:]
        out_speed = out_alt = out_beh = None
        if self.buf_speed is not None:
            out_speed, self.buf_speed = self.buf_speed[:k], self.buf_speed[k:]
        if self.buf_alt is not None:
            out_alt, self.buf_alt = self.buf_alt[:k], self.buf_alt[k:]
        if self.buf_beh is not None:
            out_beh, self.buf_beh = self.buf_beh[:k], self.buf_beh[k:]
        return out_ts, out_lat, out_lon, out_speed, out_alt, out_beh


def _kway_merge_blocks(run_dir, n_runs, has_speed, has_alt, has_behavior, buf_size):
    """
    Generator yielding successive globally-sorted blocks of
    (ts_ns, lat, lon, speed_or_None, alt_or_None, beh_or_None) arrays,
    merged from all sorted runs, using only `n_runs * buf_size` rows of
    memory at any time — never the full dataset.

    Correctness of the batching: at each step, threshold = the smallest
    "last value currently buffered" across all runs that still have data.
    Every row <= threshold, from ANY run, is safe to emit now, because no
    run can still be hiding an unseen value smaller than its own current
    buffer's last (largest-so-far) value — runs are internally sorted.
    """
    readers = [_RunReader(run_dir, i, has_speed, has_alt, has_behavior, buf_size) for i in range(n_runs)]

    while True:
        for r in readers:
            r.ensure_buffer()
        active = [r for r in readers if len(r.buf_ts) > 0]
        if not active:
            return

        threshold = min(r.buf_ts[-1] for r in active)

        pieces = []
        for r in active:
            k = int(np.searchsorted(r.buf_ts, threshold, side="right"))
            if k > 0:
                pieces.append(r.take(k))

        merged_ts = np.concatenate([p[0] for p in pieces])
        order = np.argsort(merged_ts, kind="stable")
        merged_ts = merged_ts[order]
        merged_lat = np.concatenate([p[1] for p in pieces])[order]
        merged_lon = np.concatenate([p[2] for p in pieces])[order]
        merged_speed = np.concatenate([p[3] for p in pieces])[order] if has_speed else None
        merged_alt = np.concatenate([p[4] for p in pieces])[order] if has_alt else None
        merged_beh = np.concatenate([p[5] for p in pieces])[order] if has_behavior else None

        yield merged_ts, merged_lat, merged_lon, merged_speed, merged_alt, merged_beh


def _rechunk(gen, block_rows):
    """Re-buffer a stream of variable-size merged blocks into fixed-size
    `block_rows` blocks (except possibly the very last, shorter one), so
    the windowed feature step below gets predictable, bounded-size input
    regardless of how the k-way merge happened to batch things."""
    carry = None
    for ts, lat, lon, speed, alt, beh in gen:
        if carry is not None:
            ts = np.concatenate([carry[0], ts])
            lat = np.concatenate([carry[1], lat])
            lon = np.concatenate([carry[2], lon])
            speed = np.concatenate([carry[3], speed]) if speed is not None else None
            alt = np.concatenate([carry[4], alt]) if alt is not None else None
            beh = np.concatenate([carry[5], beh]) if beh is not None else None
        while len(ts) >= block_rows:
            yield (ts[:block_rows], lat[:block_rows], lon[:block_rows],
                   speed[:block_rows] if speed is not None else None,
                   alt[:block_rows] if alt is not None else None,
                   beh[:block_rows] if beh is not None else None)
            ts, lat, lon = ts[block_rows:], lat[block_rows:], lon[block_rows:]
            speed = speed[block_rows:] if speed is not None else None
            alt = alt[block_rows:] if alt is not None else None
            beh = beh[block_rows:] if beh is not None else None
        carry = (ts, lat, lon, speed, alt, beh)
    if carry is not None and len(carry[0]) > 0:
        yield carry


def _compute_block_features(ts_ns, lat, lon, speed, alt, window):
    """
    The exact same formulas as data_pipeline.extract_features, applied to
    one in-memory block (which may include `window` rows of real overlap
    context on either side — see the caller for how those get trimmed).
    """
    n = len(lat)
    times = np.floor(ts_ns.astype(np.float64) / 1e9)

    step_len = np.zeros(n, dtype=np.float32)
    time_delta = np.zeros(n, dtype=np.float32)
    bearings = np.zeros(n, dtype=np.float32)

    if n > 1:
        phi1 = np.radians(lat[:-1]); phi2 = np.radians(lat[1:])
        dphi = phi2 - phi1
        dlambda = np.radians(lon[1:] - lon[:-1])
        a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
        step_len[1:] = R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        time_delta[1:] = times[1:] - times[:-1]

        x = np.sin(dlambda) * np.cos(phi2)
        y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)
        bearings[1:] = (np.degrees(np.arctan2(x, y)) + 360) % 360

    turning = np.zeros(n, dtype=np.float32)
    if n > 2:
        diff = bearings[2:].astype(np.float64) - bearings[1:-1].astype(np.float64)
        turning[1:-1] = np.abs((diff + 180) % 360 - 180)

    straight = np.zeros(n, dtype=np.float32)
    if n > window:
        lat_a = lat[:n - window]; lat_b = lat[window:]
        lon_a = lon[:n - window]; lon_b = lon[window:]
        phi1 = np.radians(lat_a); phi2 = np.radians(lat_b)
        dphi = phi2 - phi1
        dl = np.radians(lon_b - lon_a)
        a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dl / 2) ** 2
        net = R_EARTH * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        tot_full = pd.Series(step_len.astype(np.float64)).rolling(window=window).sum().values
        tot = tot_full[window:n]

        with np.errstate(divide="ignore", invalid="ignore"):
            vals = np.where(tot > 0, net / np.where(tot > 0, tot, 1), 0.0)
        straight[window:n] = vals

    speed_ms = np.zeros(n, dtype=np.float32)
    if speed is not None:
        sp = speed.astype(np.float64)
        fallback = step_len.astype(np.float64) / np.where(time_delta > 0, time_delta, 1)
        sp = np.where(np.isnan(sp), fallback, sp)
        # The position-based fallback can itself be NaN (e.g. a fix whose
        # lat/lon were ALSO missing), matching the old pipeline's
        # two-stage `.fillna(fallback).fillna(0)` -- zero-fill anything
        # still NaN here, BEFORE it feeds the rolling mean/std below, so
        # those rolling windows see the same values old pipeline did
        # rather than silently skipping NaN entries (which changes the
        # computed average, not just leaves a placeholder).
        speed_ms = np.nan_to_num(sp, nan=0.0).astype(np.float32)
    else:
        speed_ms = (step_len.astype(np.float64) / np.where(time_delta > 0, time_delta, 1)).astype(np.float32)

    if alt is not None:
        altitude_m = np.nan_to_num(alt.astype(np.float32), nan=0.0)
    else:
        altitude_m = np.zeros(n, dtype=np.float32)

    speed_roll_mean = pd.Series(speed_ms).rolling(window, center=True, min_periods=1).mean().astype(np.float32).values
    speed_roll_std = pd.Series(speed_ms).rolling(window, center=True, min_periods=1).std().fillna(0).astype(np.float32).values
    alt_roll_mean = pd.Series(altitude_m).rolling(window, center=True, min_periods=1).mean().astype(np.float32).values

    # Column order must match FEATURE_COLS in data_pipeline.py exactly.
    X_block = np.stack(
        [speed_ms, altitude_m, turning, straight,
         speed_roll_mean, speed_roll_std, step_len, alt_roll_mean],
        axis=1,
    ).astype(np.float32)

    # The old in-memory pipeline's final step was
    # `feat_df[FEATURE_COLS].fillna(0).values` -- a blanket NaN->0 fill
    # across the whole feature matrix, catching cases the per-column
    # handling above doesn't (e.g. a raw GPS fix with a missing/NaN
    # lat or lon propagating NaN through step length, bearing, turning
    # angle, straightness, and the rolling stats derived from them).
    # Replicate that exactly here so every algorithm downstream sees the
    # same "no NaNs in X, ever" guarantee it always has.
    np.nan_to_num(X_block, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    return X_block


def _extract_features_streaming(merged_block_gen, total_n, window,
                                  X_mm, lat_mm, lon_mm, beh_mm, has_behavior):
    """
    Consume globally-sorted blocks ONE AT A TIME (plus a single one-block
    lookahead peek, never the whole generator) and write windowed
    features straight into the pre-sized output memmaps.

    Each block's OWN rows are finalised using: the real trailing `window`
    rows of the block before it (for correct lookback — omitted only for
    the true first block, which needs the natural zero-padded start
    anyway), and a `window`-row peek borrowed from the head of the NEXT
    block (for correct lookahead — omitted only for the true last block).
    Peak memory is at most ~2 blocks + two small `window`-row slices at
    any time, regardless of total dataset size.

    (An earlier version of this function tried to carry the trailing
    overlap of block i FORWARD as leading-context for block i+1 without
    ever finalising it there or in block i — silently dropping `window`
    real rows at every block boundary. Peeking one block ahead instead of
    carrying one behind is what actually gives every row both a real
    predecessor and a real successor window.)
    """
    overlap = window

    def _cat_list(parts):
        parts = [p for p in parts if p is not None]
        if not parts:
            return np.empty(0)
        if len(parts) == 1:
            return parts[0]
        return np.concatenate(parts)

    it = iter(merged_block_gen)
    current = next(it, None)
    if current is None:
        assert total_n == 0, f"expected 0 rows, dataset reports {total_n}"
        return

    prev_tail = None
    global_pos = 0

    while current is not None:
        nxt = next(it, None)
        is_first = prev_tail is None

        cur_ts, cur_lat, cur_lon, cur_speed, cur_alt, cur_beh = current
        core_len = len(cur_ts)

        next_head = None
        if nxt is not None:
            next_head = tuple((arr[:overlap] if arr is not None else None) for arr in nxt)

        def field(i):
            pieces = []
            if prev_tail is not None:
                pieces.append(prev_tail[i])
            pieces.append(current[i])
            if next_head is not None:
                pieces.append(next_head[i])
            return _cat_list(pieces)

        buf_ts = field(0)
        buf_lat = field(1)
        buf_lon = field(2)
        buf_speed = field(3) if cur_speed is not None else None
        buf_alt = field(4) if cur_alt is not None else None
        buf_beh = field(5) if has_behavior else None

        prefix_len = 0 if is_first else len(prev_tail[0])

        X_block = _compute_block_features(buf_ts, buf_lat, buf_lon, buf_speed, buf_alt, window)

        left = prefix_len
        right = prefix_len + core_len

        X_mm[global_pos:global_pos + core_len] = X_block[left:right]
        lat_mm[global_pos:global_pos + core_len] = buf_lat[left:right]
        lon_mm[global_pos:global_pos + core_len] = buf_lon[left:right]
        if has_behavior:
            beh_mm[global_pos:global_pos + core_len] = buf_beh[left:right]

        keep = min(overlap, core_len)
        prev_tail = tuple(
            (arr[-keep:].copy() if arr is not None else None)
            for arr in (cur_ts, cur_lat, cur_lon, cur_speed, cur_alt, cur_beh)
        )

        global_pos += core_len
        current = nxt

    assert global_pos == total_n, f"streaming pipeline lost/gained rows: wrote {global_pos}, expected {total_n}"


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def load_and_extract_features_streaming(
    filepath,
    cache_dir,
    window=5,
    chunk_rows=1_000_000,
    merge_buf_rows=200_000,
    block_rows=200_000,
):
    """
    Out-of-core replacement for
    `extract_features(load_movebank_csv(filepath))` + the X/y/lats/lons
    assembly `main.load_dataset_features` used to do in RAM.

    Returns memmap-backed (X, y_or_None, label_names, lats, lons) with the
    same dtypes/shapes/semantics the old in-memory version produced.
    Everything under `cache_dir` is scratch space owned by this call —
    callers are responsible for cleaning up the PREVIOUS dataset's
    cache_dir when they load a new one (see main.py's cache wrapper).
    """
    _raise_open_file_limit()
    os.makedirs(cache_dir, exist_ok=True)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
        header = fh.readline().strip()
    available = set(c.strip('"') for c in header.split(","))
    has_speed = "ground-speed" in available
    has_alt = "height-above-msl" in available
    has_behavior = "true_behavior" in available

    behavior_vocab, label_names = _collect_behavior_vocab(filepath, has_behavior)
    has_behavior = has_behavior and len(label_names) > 0

    run_dir = _make_run_dir(cache_dir)
    n_runs, total_n = _generate_sorted_runs(
        filepath, run_dir, chunk_rows, has_speed, has_alt, has_behavior, behavior_vocab
    )

    if total_n == 0:
        X = np.zeros((0, len(FEATURE_COLS)), dtype=np.float32)
        lats = np.zeros(0, dtype=np.float64)
        lons = np.zeros(0, dtype=np.float64)
        return X, None, [], lats, lons

    X_path = os.path.join(cache_dir, "X.dat")
    lat_path = os.path.join(cache_dir, "lats.dat")
    lon_path = os.path.join(cache_dir, "lons.dat")
    beh_path = os.path.join(cache_dir, "beh.dat")

    X_mm = np.memmap(X_path, dtype=np.float32, mode="w+", shape=(total_n, len(FEATURE_COLS)))
    lat_mm = np.memmap(lat_path, dtype=np.float64, mode="w+", shape=(total_n,))
    lon_mm = np.memmap(lon_path, dtype=np.float64, mode="w+", shape=(total_n,))
    beh_mm = np.memmap(beh_path, dtype=np.int32, mode="w+", shape=(total_n,)) if has_behavior else None

    merge_gen = _kway_merge_blocks(run_dir, n_runs, has_speed, has_alt, has_behavior, merge_buf_rows)
    block_gen = _rechunk(merge_gen, block_rows)
    _extract_features_streaming(block_gen, total_n, window, X_mm, lat_mm, lon_mm, beh_mm, has_behavior)

    X_mm.flush(); lat_mm.flush(); lon_mm.flush()
    if beh_mm is not None:
        beh_mm.flush()

    # Sorted runs are fully consumed at this point — free the disk space
    # immediately rather than leaving 1x the raw-column size lying around
    # for the lifetime of the cache entry.
    shutil.rmtree(run_dir, ignore_errors=True)

    # Re-open read-only memmaps to hand back (the w+ handles above stay
    # writable, which we don't want callers doing by accident).
    X_ro = np.memmap(X_path, dtype=np.float32, mode="r", shape=(total_n, len(FEATURE_COLS)))
    lat_ro = np.memmap(lat_path, dtype=np.float64, mode="r", shape=(total_n,))
    lon_ro = np.memmap(lon_path, dtype=np.float64, mode="r", shape=(total_n,))

    y = None
    if has_behavior:
        beh_ro = np.memmap(beh_path, dtype=np.int32, mode="r", shape=(total_n,))
        y = beh_ro

    return X_ro, y, label_names, lat_ro, lon_ro
