"""
main.py  —  Vebita FastAPI Backend
===================================
Run with:  uvicorn main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""

import sys, os, time, json, uuid, math, shutil
from functools import lru_cache

# Make vebita_framework importable
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vebita_framework"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

import pandas as pd
import numpy as np
from sklearn.metrics import (
    f1_score, accuracy_score, precision_score, recall_score
)
from sklearn.preprocessing import LabelEncoder

# ── Database ──────────────────────────────────────────────────────────────────
from database import init_db, get_db

# ── Algorithm framework ───────────────────────────────────────────────────────
from vebita_framework.core.registry import registry
from vebita_framework.core.data_pipeline import (
    load_movebank_csv, extract_features, FEATURE_COLS, generate_animal_track
)
from vebita_framework.core.streaming_pipeline import load_and_extract_features_streaming

# ── Import all service algorithm files ────────────────────────────────────────
# Add each team member's file here as they complete it.
# The registry auto-discovers everything — no other changes needed.
try:
    from vebita_framework.services.example_algorithms import *
except Exception as e:
    print(f"⚠ Shared example algorithms failed to load: {e}")

try:
    from vebita_framework.services.s3_environment.sarah_algorithms import *
    print("✓ Service 3 (Environmental Factors) loaded")
except Exception as e:
    print(f"⚠ Service 3 failed to load: {e}")

try:
    from vebita_framework.services.s6_classification.arshan_algorithms import *
    print("✓ Service 6 (Behavioural Classification) loaded")
except Exception as e:
    print(f"⚠ Service 6 failed to load: {e}")

try:
    from vebita_framework.services.s4_anomaly.dua_algorithms import *
    print("✓ Service 4 (Anomaly Detection) loaded")
except Exception as e:
    print(f"⚠ Service 4 failed to load: {e}")

try:
    from vebita_framework.services.s1_timeseries.abdul_algorithms import *
    print("✓ Service 1 (Time Series Patterns) loaded")
except Exception as e:
    print(f"⚠ Service 1 failed to load: {e}")

try:
    from vebita_framework.services.s2_patterns.hiba_algorithms import *
    print("✓ Service 2 (Movement Patterns) loaded")
except Exception as e:
    print(f"⚠ Service 2 failed to load: {e}")

try:
    from vebita_framework.services.s5_segmentation.ritika_algorithms import *
    print("✓ Service 5 (Trajectory Segmentation) loaded")
except Exception as e:
    print(f"⚠ Service 5 failed to load: {e}")

# ── Service metadata ──────────────────────────────────────────────────────────
SERVICES = {
    1: {"name": "Time Series Patterns",        "color": "#378ADD"},
    2: {"name": "Movement Patterns",            "color": "#ED93B1"},
    3: {"name": "Environmental Factors",        "color": "#5DCAA5"},
    4: {"name": "Anomaly Detection",            "color": "#D85A30"},
    5: {"name": "Trajectory Segmentation",      "color": "#AFA9EC"},
    6: {"name": "Behavioural Classification",   "color": "#EF9F27"},
}

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vebita API",
    description="Animal movement analysis platform — VEBITA group project",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_pred, label_names):
    """Return dict of per-class and overall metrics."""
    if y_true is None or len(np.unique(y_true)) < 2:
        return {"f1": None, "accuracy": None,
                "precision": None, "recall": None, "per_class_f1": {}}
    try:
        classes = np.unique(y_true)
        per_class = f1_score(y_true, y_pred, average=None,
                             labels=classes, zero_division=0)
        per_class_dict = {}
        for i, c in enumerate(classes):
            name = label_names[c] if c < len(label_names) else str(c)
            per_class_dict[name] = round(float(per_class[i]), 4)

        return {
            "f1":          round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
            "accuracy":    round(float(accuracy_score(y_true, y_pred)), 4),
            "precision":   round(float(precision_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
            "recall":      round(float(recall_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
            "per_class_f1": per_class_dict,
        }
    except Exception:
        return {"f1": None, "accuracy": None,
                "precision": None, "recall": None, "per_class_f1": {}}


def _json_safe(obj):
    """Recursively replace NaN/Infinity with None so FastAPI's strict JSON
    encoder (allow_nan=False) never chokes on a real-world dataset that has
    missing GPS fixes, gaps, or other holes that surface as float('nan')
    or float('inf') anywhere in a response payload."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


# Feature-cache lives on DISK now, not in a Python-level LRU cache in RAM
# (a "cached" DataFrame for a 15-20GB+ dataset is itself 15-20GB+ of RAM
# just to hold the cache; the streaming pipeline below only ever needs a
# small, constant amount of RAM to BUILD its output, but the output
# itself — the X/y/lats/lons the algorithms run against — still has to
# live somewhere while the app uses it. Putting it in memmap-backed .dat
# files under FEATURE_CACHE_DIR means the OS page-cache, not the Python
# process, is what actually holds it in RAM, and the OS is free to page
# it in/out under memory pressure instead of the process getting OOM
# killed).
FEATURE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "feature_cache")
# Wipe any stale cache from a previous run on every fresh server start —
# the in-memory "which dataset is cached" bookkeeping below also resets
# on restart, so an orphaned on-disk cache would just be dead weight.
shutil.rmtree(FEATURE_CACHE_DIR, ignore_errors=True)
os.makedirs(FEATURE_CACHE_DIR, exist_ok=True)

_loaded_dataset = {"filename": None, "result": None}


def _cache_slug(filename: str) -> str:
    """Filesystem-safe subdirectory name for one dataset's on-disk cache."""
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in filename)


def load_dataset_features(filename: str):
    """Load CSV, extract features, return (X, y, label_names, lats, lons).

    Out-of-core: uses `load_and_extract_features_streaming`, which reads
    the CSV in bounded chunks, sorts it with an external (disk-based)
    merge sort, and extracts windowed features one small block at a
    time — never holding the whole dataset in RAM at once, regardless of
    how large the file is. Returned arrays are memmaps backed by files
    under FEATURE_CACHE_DIR, opened read-only.

    Only the most-recently-used dataset is kept (in memory bookkeeping
    AND on disk): every /run call used to re-read and re-process the
    ENTIRE CSV from scratch, even though most of a session is spent
    comparing many different algorithm pairs against the SAME
    already-uploaded dataset. Switching to a different dataset deletes
    the previous one's on-disk cache directory so repeated
    uploads/switches don't pile up unbounded disk usage over a session.
    """
    if _loaded_dataset["filename"] == filename and _loaded_dataset["result"] is not None:
        return _loaded_dataset["result"]

    path = os.path.join(UPLOAD_DIR, filename)
    cache_dir = os.path.join(FEATURE_CACHE_DIR, _cache_slug(filename))

    if _loaded_dataset["filename"] is not None and _loaded_dataset["filename"] != filename:
        old_dir = os.path.join(FEATURE_CACHE_DIR, _cache_slug(_loaded_dataset["filename"]))
        shutil.rmtree(old_dir, ignore_errors=True)

    X, y, label_names, lats, lons = load_and_extract_features_streaming(path, cache_dir)

    # Belt-and-suspenders: the streaming pipeline already hands back
    # read-only memmaps, but explicitly marking them read-only here keeps
    # the same safety guarantee the old in-memory cache made — if any
    # algorithm's fit()/predict() ever mutated its input in place, it
    # raises a clear, per-algorithm error instead of silently corrupting
    # this shared cached data for every later run against this dataset.
    X.setflags(write=False)
    lats.setflags(write=False)
    lons.setflags(write=False)
    if y is not None:
        y.setflags(write=False)

    result = (X, y, label_names, lats, lons)
    _loaded_dataset["filename"] = filename
    _loaded_dataset["result"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    total = sum(len(registry.get_by_service(sid)) for sid in range(1, 7))
    return {
        "status": "running",
        "total_algorithms": total,
        "services": {sid: SERVICES[sid]["name"] for sid in SERVICES},
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — DATASETS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a Movebank CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_name)

    # Stream the upload straight to disk instead of `await file.read()`
    # (which buffers the entire file in memory first) - on a multi-GB file
    # that alone was enough to exhaust memory before parsing even started.
    CHUNK = 1024 * 1024
    with open(path, "wb") as out:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            out.write(chunk)

    # Parse for metadata. Row count and species only need the header plus
    # a cheap line count - pd.read_csv(path) with no usecols/chunksize
    # re-parses every column of the whole file (the same cost problem
    # load_movebank_csv had) just to answer two small questions.
    try:
        with open(path, "rb") as fh:
            header_line = fh.readline().decode("utf-8", errors="ignore")
            n_fixes = sum(1 for _ in fh)  # remaining lines = data rows (header already consumed)

        header_cols = [c.strip().strip('"') for c in header_line.strip().split(",")]
        species = "Unknown"
        for col in ["species", "individual-taxon-canonical-name", "taxon-canonical-name"]:
            if col in header_cols:
                first_row = pd.read_csv(path, usecols=[col], nrows=1)
                species = str(first_row[col].iloc[0])
                break
        file_size_kb = round(os.path.getsize(path) / 1024, 1)
    except Exception as e:
        os.remove(path)
        raise HTTPException(400, f"Could not parse CSV: {e}")

    db = get_db()
    cur = db.execute(
        "INSERT INTO datasets (filename, original_name, species, n_fixes, file_size_kb) "
        "VALUES (?,?,?,?,?)",
        (safe_name, file.filename, species, n_fixes, file_size_kb),
    )
    db.commit()
    dataset_id = cur.lastrowid
    db.close()

    return {
        "dataset_id":   dataset_id,
        "filename":     file.filename,
        "species":      species,
        "n_fixes":      n_fixes,
        "file_size_kb": file_size_kb,
    }


@app.get("/datasets")
def list_datasets():
    """Return all uploaded datasets."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM datasets ORDER BY uploaded_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int):
    """Delete a dataset record (file stays on disk)."""
    db = get_db()
    db.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    db.commit()
    db.close()
    return {"deleted": dataset_id}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — ALGORITHMS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/algorithms/{service_id}")
def list_algorithms(service_id: int):
    """Return all algorithms registered for a given service."""
    algos = registry.get_by_service(service_id)
    if not algos:
        return []
    result = []
    for a in algos:
        result.append({
            "name":        a.name,
            "category":    a.category,
            "library":     a.library,
            "description": a.description,
            "animals":     getattr(a, "animals", ["all"]),
        })
    return sorted(result, key=lambda x: (x["category"], x["name"]))


@app.get("/algorithms")
def list_all_algorithms():
    """Return all algorithms across all services."""
    out = {}
    for sid in range(1, 7):
        algos = registry.get_by_service(sid)
        out[sid] = [{"name": a.name, "category": a.category} for a in algos]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — RUN ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    dataset_id: int
    service_id: int
    algo_a:     str
    algo_b:     str


@app.post("/run")
def run_comparison(req: RunRequest):
    """
    Run two algorithms on a dataset and return full comparison results.
    This is the core endpoint — called when user clicks 'Run analysis'.
    """
    # Load dataset record
    db = get_db()
    row = db.execute(
        "SELECT * FROM datasets WHERE id=?", (req.dataset_id,)
    ).fetchone()
    db.close()

    if row is None:
        raise HTTPException(404, f"Dataset {req.dataset_id} not found")

    service_name = SERVICES.get(req.service_id, {}).get("name", "Unknown")

    # Load features
    try:
        X, y, label_names, lats, lons = load_dataset_features(row["filename"])
    except Exception as e:
        raise HTTPException(500, f"Failed to load dataset: {e}")

    # Train/test split (temporal — no shuffling)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train = y[:split] if y is not None else None
    y_test  = y[split:] if y is not None else None
    lats_test = lats[split:].tolist() if lats is not None and len(lats) else []
    lons_test = lons[split:].tolist() if lons is not None and len(lons) else []

    # Auto-assign movement labels when dataset has no true_behavior column.
    # Uses KMeans on speed + altitude + turning angle so boundaries are
    # non-linear — algorithms with different decision boundaries will genuinely
    # disagree rather than all converging on the same speed-rank split.
    effective_label_names = label_names
    if not label_names and req.service_id != 3:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        def _cluster_labels(X_split):
            # cols: 0=speed, 1=altitude, 2=turning_angle (if available)
            n_cols = X_split.shape[1]
            feat_idx = [i for i in [0, 1, 2] if i < n_cols]
            feats = X_split[:, feat_idx].astype(float)
            feats = np.nan_to_num(feats, nan=0.0)
            scaler = StandardScaler()
            feats_s = scaler.fit_transform(feats)
            km = KMeans(n_clusters=4, random_state=42, n_init=10)
            raw = km.fit_predict(feats_s)
            # Re-order clusters by mean speed so labels are interpretable
            centers = km.cluster_centers_
            speed_idx = 0  # speed is first feature after scaling
            order = np.argsort(centers[:, speed_idx])
            remap = {old: new for new, old in enumerate(order)}
            return np.array([remap[c] for c in raw])

        y_train = _cluster_labels(X_train)
        y_test  = _cluster_labels(X_test)
        effective_label_names = ["Resting", "Foraging", "Traveling", "Migrating"]

    # Find algorithm classes
    all_algos = registry.get_by_service(req.service_id)
    algo_map  = {a.name: a for a in all_algos}

    def run_one(name: str):
        if name not in algo_map:
            return {"name": name, "error": f"'{name}' not found in service {req.service_id}",
                    "f1": None, "accuracy": None, "precision": None, "recall": None,
                    "runtime": None, "predictions": [], "per_class_f1": {},
                    "service_type": "classification"}
        try:
            inst = algo_map[name]()
            t0   = time.time()
            inst.fit(X_train, y_train)
            raw  = inst.predict(X_test)
            rt   = round(time.time() - t0, 3)

            # S3 (Environmental Factors) returns continuous scores — send as-is
            if req.service_id == 3:
                raw_finite = np.nan_to_num(raw.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
                r_min, r_max = float(raw_finite.min()), float(raw_finite.max())
                r_range = r_max - r_min if r_max != r_min else 1.0
                scores_norm = ((raw_finite - r_min) / r_range).tolist()
                return {
                    "name":         name,
                    "service_type": "regression",
                    "score_label":  inst.description or name,
                    "scores":       scores_norm,
                    "score_min":    round(r_min, 4),
                    "score_max":    round(r_max, 4),
                    "predictions":  [],
                    "f1": None, "accuracy": None, "precision": None,
                    "recall": None, "per_class_f1": {},
                    "runtime": rt, "error": None,
                }

            # Clamp predictions to valid integer labels
            preds = np.clip(np.round(raw).astype(int), 0, 99).tolist()

            metrics = compute_metrics(y_test, preds, effective_label_names)

            def _safe(v):
                if v is None: return None
                try:
                    return None if (np.isnan(v) or np.isinf(v)) else round(float(v), 4)
                except Exception:
                    return None

            return {
                "name":          name,
                "service_type":  "classification",
                "f1":            _safe(metrics["f1"]),
                "accuracy":      _safe(metrics["accuracy"]),
                "precision":     _safe(metrics["precision"]),
                "recall":        _safe(metrics["recall"]),
                "per_class_f1":  {k: _safe(v) for k, v in metrics["per_class_f1"].items()},
                "runtime":       rt,
                "predictions":   preds,
                "error":         None,
            }
        except Exception as e:
            return {"name": name, "service_type": "classification", "error": str(e),
                    "f1": None, "accuracy": None, "precision": None,
                    "recall": None, "runtime": None,
                    "predictions": [], "per_class_f1": {}}

    result_a = run_one(req.algo_a)
    result_b = run_one(req.algo_b)

    # Permutation importance — classification only, capped at 2000 rows for speed
    from sklearn.inspection import permutation_importance as _perm_imp
    from sklearn.metrics import accuracy_score

    def _perm_scorer(estimator, X, y):
        raw = estimator.predict(X)
        preds = np.clip(np.round(np.array(raw).astype(float)), 0, 99).astype(int)
        return accuracy_score(y, preds)

    def _feature_importance(inst, X, y, names):
        if y is None or req.service_id == 3:
            return {}
        try:
            X_imp = np.array(X[:2000]); y_imp = np.array(y[:2000])
            r = _perm_imp(inst, X_imp, y_imp, scoring=_perm_scorer,
                          n_repeats=5, random_state=42, n_jobs=1)
            return {names[i]: round(float(r.importances_mean[i]), 6) for i in range(len(names))}
        except Exception as e:
            print(f"[importance] {inst.__class__.__name__} failed: {e}")
            return {}

    # Re-instantiate fitted models to run importance (run_one already called fit internally)
    def _fitted_inst(name):
        try:
            inst = algo_map[name]()
            inst.fit(X_train, y_train)
            return inst
        except Exception:
            return None

    if req.service_id != 3 and y_test is not None:
        inst_a = _fitted_inst(req.algo_a)
        inst_b = _fitted_inst(req.algo_b)
        result_a["feature_importances"] = _feature_importance(inst_a, X_test, y_test, FEATURE_COLS) if inst_a else {}
        result_b["feature_importances"] = _feature_importance(inst_b, X_test, y_test, FEATURE_COLS) if inst_b else {}
    else:
        result_a["feature_importances"] = {}
        result_b["feature_importances"] = {}

    # Save to DB
    db = get_db()
    db.execute("""
        INSERT INTO results (
            dataset_id, service_id, service_name,
            algo_a, algo_b,
            f1_a, f1_b, accuracy_a, accuracy_b,
            precision_a, precision_b, recall_a, recall_b,
            runtime_a, runtime_b,
            n_train, n_test, n_classes,
            label_names, predictions_a, predictions_b,
            per_class_f1_a, per_class_f1_b,
            error_a, error_b
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        req.dataset_id, req.service_id, service_name,
        req.algo_a, req.algo_b,
        result_a["f1"], result_b["f1"],
        result_a["accuracy"], result_b["accuracy"],
        result_a["precision"], result_b["precision"],
        result_a["recall"], result_b["recall"],
        result_a["runtime"], result_b["runtime"],
        len(X_train), len(X_test),
        len(label_names),
        json.dumps(label_names),
        json.dumps(result_a["predictions"]),
        json.dumps(result_b["predictions"]),
        json.dumps(result_a["per_class_f1"]),
        json.dumps(result_b["per_class_f1"]),
        result_a.get("error"), result_b.get("error"),
    ))
    db.commit()
    result_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()

    # Cap visual arrays sent to the browser — algorithms already ran on the
    # full test set so metrics are accurate. Only map dots, chart points, and
    # score arrays need to be sampled; 20 000 points renders fine and keeps
    # the JSON response under ~10 MB regardless of dataset size.
    # Also skip any row where lat or lon is NaN — Leaflet crashes on null coords.
    MAX_VIS = 20_000
    n_vis   = len(lats_test)

    lats_arr = np.array(lats_test, dtype=float)
    lons_arr = np.array(lons_test, dtype=float)
    valid_mask = np.isfinite(lats_arr) & np.isfinite(lons_arr)
    valid_idx  = np.where(valid_mask)[0]

    if len(valid_idx) > MAX_VIS:
        step = max(1, len(valid_idx) // MAX_VIS)
        valid_idx = valid_idx[::step][:MAX_VIS]

    lats_vis = lats_arr[valid_idx].tolist()
    lons_vis = lons_arr[valid_idx].tolist()

    # Real feature arrays for the test set — sampled with the same valid_idx
    # Columns: 0=speed_ms, 1=altitude_m, 2=turning_angle, 3=straightness, 6=step_length_m
    X_test_arr = np.array(X_test)
    def _feat_col(col):
        if X_test_arr.shape[1] > col:
            return [round(float(X_test_arr[i, col]), 4) for i in valid_idx if i < len(X_test_arr)]
        return []

    speeds_vis      = _feat_col(0)
    altitudes_vis   = _feat_col(1)
    turns_vis       = _feat_col(2)
    straightness_vis = _feat_col(3)
    steps_vis       = _feat_col(6)

    def _sample_list(lst):
        if not lst: return lst
        arr = lst if isinstance(lst, (list,)) else list(lst)
        return [arr[i] for i in valid_idx if i < len(arr)]

    def _sample_algo(res):
        out = dict(res)
        if out.get("predictions"):
            out["predictions"] = _sample_list(out["predictions"])
        if out.get("scores"):
            out["scores"] = _sample_list(out["scores"])
        return out

    result_a_vis = _sample_algo(result_a)
    result_b_vis = _sample_algo(result_b)

    return _json_safe({
        "result_id":    result_id,
        "service_id":   req.service_id,
        "service_name": service_name,
        "dataset":      dict(row),
        "n_train":      len(X_train),
        "n_test":       len(X_test),
        "label_names":  effective_label_names,
        "lats":         lats_vis,
        "lons":         lons_vis,
        "speeds":       speeds_vis,
        "altitudes":    altitudes_vis,
        "turns":        turns_vis,
        "straightness": straightness_vis,
        "steps":        steps_vis,
        "algo_a":       result_a_vis,
        "algo_b":       result_b_vis,
        "feature_names": FEATURE_COLS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/history")
def get_history(limit: int = 50):
    """Return past analysis runs with dataset info joined."""
    db = get_db()
    rows = db.execute("""
        SELECT r.id, r.service_name, r.algo_a, r.algo_b,
               r.f1_a, r.f1_b, r.accuracy_a, r.accuracy_b,
               r.runtime_a, r.runtime_b,
               r.n_train, r.n_test, r.n_classes,
               r.error_a, r.error_b, r.run_at,
               d.original_name as dataset_name, d.species
        FROM results r
        JOIN datasets d ON r.dataset_id = d.id
        ORDER BY r.run_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@app.get("/history/{result_id}")
def get_result(result_id: int):
    """Return a single result with full predictions."""
    db = get_db()
    row = db.execute("SELECT * FROM results WHERE id=?", (result_id,)).fetchone()
    db.close()
    if row is None:
        raise HTTPException(404, "Result not found")
    r = dict(row)
    for key in ["label_names", "predictions_a", "predictions_b",
                "per_class_f1_a", "per_class_f1_b"]:
        if r.get(key):
            try:
                r[key] = json.loads(r[key])
            except Exception:
                pass
    return r


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — DEMO DATA (no upload needed)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/demo")
def run_demo(payload: dict = None):
    """
    Generate a synthetic Movebank track and run two algorithms on it.
    Useful for testing the website without a real CSV.
    """
    payload = payload or {}
    animal   = payload.get("animal", "red_kite")
    algo_a   = payload.get("algo_a", "Beh Random Forest Classifier")
    algo_b   = payload.get("algo_b", "Beh HMM 4-State")
    service  = payload.get("service_id", 6)
    n_points = payload.get("n_points", 800)

    # Use a random seed each call so different algo pairs get varied demo data
    seed = int(time.time() * 1000) % 100000
    raw_df   = generate_animal_track(animal, n_points, seed=seed)
    feat_df  = extract_features(raw_df)
    X        = feat_df[FEATURE_COLS].fillna(0).values
    le       = LabelEncoder()
    y        = le.fit_transform(feat_df["true_behavior"].values)
    label_names = list(le.classes_)
    lats     = raw_df["location-lat"].tolist()
    lons     = raw_df["location-long"].tolist()

    split    = int(len(X) * 0.8)
    X_train, X_test   = X[:split], X[split:]
    y_train, y_test   = y[:split], y[split:]
    lats_test = lats[split:]
    lons_test = lons[split:]

    all_algos = registry.get_by_service(service)
    algo_map  = {a.name: a for a in all_algos}

    def run_one(name):
        if name not in algo_map:
            return {"name": name, "error": f"Not found", "f1": None,
                    "accuracy": None, "precision": None, "recall": None,
                    "runtime": None, "predictions": [], "per_class_f1": {},
                    "feature_importances": {}}
        try:
            inst = algo_map[name]()
            t0   = time.time()
            inst.fit(X_train, y_train)
            preds = np.clip(np.round(inst.predict(X_test)).astype(int), 0, 99).tolist()
            rt    = round(time.time() - t0, 3)
            m     = compute_metrics(y_test, preds, label_names)
            # Permutation importance capped at 2000 rows
            from sklearn.inspection import permutation_importance as _perm_imp
            try:
                X_imp, y_imp = X_test[:2000], y_test[:2000]
                r = _perm_imp(inst, X_imp, y_imp, n_repeats=5, random_state=42, n_jobs=1)
                fi = {FEATURE_COLS[i]: round(float(r.importances_mean[i]), 6) for i in range(len(FEATURE_COLS))}
            except Exception:
                fi = {}
            return {**m, "name": name, "runtime": rt,
                    "predictions": preds, "error": None, "feature_importances": fi}
        except Exception as e:
            return {"name": name, "error": str(e), "f1": None,
                    "accuracy": None, "precision": None, "recall": None,
                    "runtime": None, "predictions": [], "per_class_f1": {},
                    "feature_importances": {}}

    result_a_demo = run_one(algo_a)
    result_b_demo = run_one(algo_b)

    return _json_safe({
        "service_id":    service,
        "service_name":  SERVICES.get(service, {}).get("name", "Demo"),
        "dataset":       {"original_name": f"{animal}_demo.csv", "species": animal},
        "n_train":       len(X_train),
        "n_test":        len(X_test),
        "label_names":   label_names,
        "lats":          lats_test,
        "lons":          lons_test,
        "speeds":        [round(float(X_test[i, 0]), 4) for i in range(len(X_test))],
        "altitudes":     [round(float(X_test[i, 1]), 4) for i in range(len(X_test))],
        "turns":         [round(float(X_test[i, 2]), 4) for i in range(len(X_test))],
        "straightness":  [round(float(X_test[i, 3]), 4) for i in range(len(X_test))],
        "steps":         [round(float(X_test[i, 6]), 4) for i in range(len(X_test))],
        "algo_a":        result_a_demo,
        "algo_b":        result_b_demo,
        "feature_names": FEATURE_COLS,
    })