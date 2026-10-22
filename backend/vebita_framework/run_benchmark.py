"""
run_benchmark.py
================
VEBITA Master Benchmark Script

Run this to execute ALL registered algorithms across ALL 6 services.
Each team member's algorithms auto-register when their module is imported.

Usage:
    # Run everything
    python run_benchmark.py

    # Run one service only
    python run_benchmark.py --service 5

    # Run on a specific animal
    python run_benchmark.py --animal mongolian_gazelle

    # Run with a real Movebank CSV
    python run_benchmark.py --csv path/to/movebank_data.csv
"""

import argparse
import sys
import os

# Prevent nested BLAS/OpenMP threads from crashing when joblib threading backend
# spawns multiple Python threads that each call numpy/sklearn simultaneously.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Import all service algorithm modules ─────────────────────────────────
# Each import auto-registers all algorithms in that module.
# To add your algorithms: create your file, import it here.

from services.example_algorithms import *   # demo algorithms for all services

# When each team member finishes their file, add it here:
from services.s1_timeseries.abdul_algorithms import *
from services.s2_patterns.hiba_algorithms import *
from services.s3_environment.sarah_algorithms import *
from services.s4_anomaly.dua_algorithms import *
from services.s5_segmentation.ritika_algorithms import *
from services.s6_classification.arshan_algorithms import *

from core.registry      import registry
from core.data_pipeline import DataPipeline
from core.benchmark     import BenchmarkRunner


def main():
    parser = argparse.ArgumentParser(description="VEBITA Benchmark Runner")
    parser.add_argument("--service", type=int, default=None,
                        help="Run only this service (1-6). Default: all.")
    parser.add_argument("--animal", type=str, default="red_kite",
                        help="Animal type for data generation.")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to real Movebank CSV file.")
    parser.add_argument("--points", type=int, default=1200,
                        help="Number of GPS points to generate.")
    parser.add_argument("--jobs", type=int, default=2,
                        help="Parallel workers. -1 = all CPUs. Default: 2 (safe for low-RAM).")
    parser.add_argument("--output", type=str,
                        default="results/benchmark_results.csv",
                        help="Output CSV path.")
    args = parser.parse_args()

    # ── Print registry summary ────────────────────────────────────────────
    registry.print_summary()

    # ── Build data pipeline ───────────────────────────────────────────────
    print(f"Loading data: animal={args.animal}, points={args.points}")
    pipeline = DataPipeline(
        animal   = args.animal,
        n_points = args.points,
        csv_path = args.csv,
    )
    info = pipeline.info()
    print(f"Data ready: {info['train_points']} train / "
          f"{info['test_points']} test | "
          f"behaviors: {info['behaviors']}\n")

    # ── Run benchmark ─────────────────────────────────────────────────────
    runner = BenchmarkRunner(pipeline, n_jobs=args.jobs)

    if args.service:
        results = runner.run_service(args.service)
    else:
        results = runner.run_all()

    # ── Save results ──────────────────────────────────────────────────────
    runner.save_results(args.output)

    # ── Print leaderboard ─────────────────────────────────────────────────
    print("\n── Overall leaderboard (top 15 by accuracy) ──")
    lb = runner.leaderboard(metric="accuracy", top_n=15)
    if len(lb):
        print(lb.to_string(index=False))

    print(f"\nDone. Full results saved to: {args.output}")


if __name__ == "__main__":
    main()
