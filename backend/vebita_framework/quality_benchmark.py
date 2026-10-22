"""
quality_benchmark.py
Run all S3 and S6 algorithms on a real CSV and record actual quality metrics.
Usage: /usr/bin/python3 quality_benchmark.py
"""
import sys, os, time, warnings
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from services.s3_environment.sarah_algorithms import *
from services.s6_classification.arshan_algorithms import *
from core.registry      import registry
from core.data_pipeline import DataPipeline
from core.evaluator     import Evaluator
import numpy as np

CSV = "/Users/I776893/Downloads/Movement Project/backend/uploads/7968800f8abb4990af5de0d18ed958ab_African cuckoo in Nigeria (data from Iwajomo et al. 2018).csv"

print("Loading African cuckoo dataset...")
pipeline = DataPipeline(csv_path=CSV, scaler="standard")
X_train, X_test, y_train, y_test = pipeline.get_splits()
print(f"Train: {len(X_train)}  Test: {len(X_test)}  Labels: {pipeline.label_names}\n")

# ── KMeans auto-label if no true_behavior ────────────────────────────────────
if y_train is None or len(y_train) == 0:
    from sklearn.cluster import KMeans
    print("No true_behavior column — auto-labelling with KMeans(4)...")
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    y_all = km.fit_predict(np.vstack([X_train, X_test]))
    y_train = y_all[:len(X_train)]
    y_test  = y_all[len(X_train):]
    print(f"KMeans labels assigned.\n")

# ── Run S6 ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("SERVICE 6 — Behavioural Classification")
print("=" * 60)

s6_algos = [(a.name, a) for a in registry.get_by_service(6)]
s6_results = []

for name, AlgoClass in sorted(s6_algos, key=lambda x: x[0]):
    algo = AlgoClass()
    try:
        t0 = time.time()
        algo.fit(X_train, y_train)
        y_pred = algo.predict(X_test)
        elapsed = round(time.time() - t0, 3)
        metrics = Evaluator.compute_metrics(y_test, y_pred, service_id=6)
        acc   = metrics.get("accuracy", 0)
        f1w   = metrics.get("f1_weighted", 0)
        f1m   = metrics.get("f1_macro", 0)
        prec  = metrics.get("precision", 0)
        rec   = metrics.get("recall", 0)
        s6_results.append((name, acc, f1w, f1m, prec, rec, elapsed, "ok"))
        print(f"  {name:<45} F1w={f1w:.3f}  Acc={acc:.3f}  t={elapsed}s")
    except Exception as e:
        s6_results.append((name, 0, 0, 0, 0, 0, 0, f"ERROR: {e}"))
        print(f"  {name:<45} ERROR: {e}")

# Sort by f1_weighted descending
s6_results.sort(key=lambda x: x[2], reverse=True)

print("\n── S6 RANKED BY F1_WEIGHTED ──")
print(f"{'Rank':<5} {'Algorithm':<45} {'F1w':>5} {'F1m':>5} {'Acc':>5} {'Prec':>5} {'Rec':>5} {'Time':>6}")
print("-" * 85)
for i, (name, acc, f1w, f1m, prec, rec, elapsed, status) in enumerate(s6_results, 1):
    if status == "ok":
        print(f"  {i:<3}  {name:<45} {f1w:>5.3f} {f1m:>5.3f} {acc:>5.3f} {prec:>5.3f} {rec:>5.3f} {elapsed:>6}s")
    else:
        print(f"  {i:<3}  {name:<45} {status}")

# ── Run S3 ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SERVICE 3 — Environmental Factors")
print("=" * 60)

# For S3 we need a continuous score as y_true — use first PC of X_test as proxy
from sklearn.decomposition import PCA
pca = PCA(n_components=1)
pca.fit(X_train)
y_true_s3 = pca.transform(X_test).flatten()
# Normalise to 0-1
y_true_s3 = (y_true_s3 - y_true_s3.min()) / (y_true_s3.max() - y_true_s3.min() + 1e-9)

s3_algos = [(a.name, a) for a in registry.get_by_service(3)]
s3_results = []

for name, AlgoClass in sorted(s3_algos, key=lambda x: x[0]):
    algo = AlgoClass()
    try:
        t0 = time.time()
        algo.fit(X_train, y_train)
        y_pred = algo.predict(X_test)
        elapsed = round(time.time() - t0, 3)
        # Normalise prediction to 0-1
        y_p = np.array(y_pred, dtype=float)
        rng = y_p.max() - y_p.min()
        if rng > 0:
            y_p = (y_p - y_p.min()) / rng
        metrics = Evaluator.compute_metrics(y_true_s3, y_p, service_id=3)
        pearson  = metrics.get("pearson_r", 0)
        spearman = metrics.get("spearman_r", 0)
        r2       = metrics.get("r2", 0)
        s3_results.append((name, pearson, spearman, r2, elapsed, "ok"))
        print(f"  {name:<50} pearson={pearson:>6.3f}  spearman={spearman:>6.3f}  r2={r2:>6.3f}  t={elapsed}s")
    except Exception as e:
        s3_results.append((name, 0, 0, 0, 0, f"ERROR: {e}"))
        print(f"  {name:<50} ERROR: {e}")

s3_results.sort(key=lambda x: x[1], reverse=True)

print("\n── S3 RANKED BY PEARSON R ──")
print(f"{'Rank':<5} {'Algorithm':<50} {'Pearson':>8} {'Spearman':>9} {'R2':>7} {'Time':>6}")
print("-" * 90)
for i, row in enumerate(s3_results, 1):
    name, pearson, spearman, r2, elapsed, status = row
    if status == "ok":
        print(f"  {i:<3}  {name:<50} {pearson:>8.3f} {spearman:>9.3f} {r2:>7.3f} {elapsed:>6}s")
    else:
        print(f"  {i:<3}  {name:<50} {status}")

# ── Save results ──────────────────────────────────────────────────────────────
import csv as csvlib
with open("results/s6_quality_results.csv", "w", newline="") as f:
    w = csvlib.writer(f)
    w.writerow(["rank","algo_name","f1_weighted","f1_macro","accuracy","precision","recall","runtime_s","status"])
    for i, (name, acc, f1w, f1m, prec, rec, elapsed, status) in enumerate(s6_results, 1):
        w.writerow([i, name, f1w, f1m, acc, prec, rec, elapsed, status])

with open("results/s3_quality_results.csv", "w", newline="") as f:
    w = csvlib.writer(f)
    w.writerow(["rank","algo_name","pearson_r","spearman_r","r2","runtime_s","status"])
    for i, row in enumerate(s3_results, 1):
        name, pearson, spearman, r2, elapsed, status = row
        w.writerow([i, name, pearson, spearman, r2, elapsed, status])

print("\nSaved: results/s6_quality_results.csv")
print("Saved: results/s3_quality_results.csv")
