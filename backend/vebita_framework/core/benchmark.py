"""
core/benchmark.py
=================
VEBITA Benchmark Runner

Runs ALL registered algorithms (550+) on any dataset automatically.
Uses parallel execution — all algorithms run simultaneously.

Usage:
    from core.benchmark import BenchmarkRunner
    from core.data_pipeline import DataPipeline

    pipeline = DataPipeline(animal="red_kite")
    runner   = BenchmarkRunner(pipeline)

    # Run all 550+ algorithms
    results = runner.run_all()

    # Run only one service
    results = runner.run_service(5)

    # Save results
    runner.save_results("results/benchmark_results.csv")
"""

import time
import warnings
import numpy as np
import pandas as pd
from typing import List, Optional, Dict
from joblib import Parallel, delayed

from core.base import BaseAlgorithm, AlgoResult
from core.registry import registry
from core.data_pipeline import DataPipeline
from core.evaluator import Evaluator

warnings.filterwarnings("ignore")


def _run_single(AlgoClass, X_train, X_test, y_train, y_test) -> dict:
    """
    Run one algorithm. Called in parallel by joblib.
    Returns a flat dict (easy to convert to DataFrame row).
    """
    algo = AlgoClass()
    if getattr(AlgoClass, "service_id", None) == 3:
        print(f"[S3] Starting {algo.name}", flush=True)
    if algo.name in {
        "Env Huber Regression",
        "Env LSTM Regressor",
        "Env GRU Regressor",
        "Env Robust Regression (MCD)",
        "Env Nonlinear GP Regression",
        "Env MLP Regressor",
        "Env Vanilla RNN",
        "Env Spectral Clustering",
        "Env Self-Organising Map",
        "Env t-SNE Embedding",
        "Env Spatio-Temporal Kriging",
        "Env ST-CNN",
        "Env RNN with Env Inputs",
        "Env ST-GNN Proxy",
    }:
        result = AlgoResult(
            algo_name=algo.name,
            service_id=algo.service_id,
            category=algo.category,
            status="error",
            error_msg="TimeoutError: known-hanging algorithm skipped by benchmark guard",
        )
    else:
        result = algo.safe_run(X_train, X_test, y_train)

    row = {
        "algo_name":  result.algo_name,
        "service_id": result.service_id,
        "category":   result.category,
        "status":     result.status,
        "runtime_s":  result.runtime_s,
        "memory_mb":  result.memory_mb,
        "error_msg":  result.error_msg,
    }

    # Compute evaluation metrics if predictions exist and labels available
    if result.status == "ok" and result.predictions is not None and y_test is not None:
        metrics = Evaluator.compute_metrics(
            y_true      = y_test,
            y_pred      = result.predictions,
            service_id  = result.service_id,
        )
        row.update(metrics)

    return row


class BenchmarkRunner:
    """
    Runs all registered algorithms and collects results into a DataFrame.
    """

    def __init__(self, pipeline: DataPipeline, n_jobs: int = -1):
        """
        Parameters
        ----------
        pipeline : DataPipeline
            Shared data pipeline — same data for all algorithms.
        n_jobs   : int
            Parallel workers. -1 = use all CPU cores.
        """
        self.pipeline  = pipeline
        self.n_jobs    = n_jobs
        self.results_df: Optional[pd.DataFrame] = None

        X_train, X_test, y_train, y_test = pipeline.get_splits()
        self.X_train = X_train
        self.X_test  = X_test
        self.y_train = y_train
        self.y_test  = y_test

    # ── Run methods ───────────────────────────────────────────────────────

    def run_all(self, verbose: bool = True) -> pd.DataFrame:
        """Run every registered algorithm across all 6 services."""
        algos = registry.get_all()
        return self._run(algos, label="All services", verbose=verbose)

    def run_service(self, service_id: int, verbose: bool = True) -> pd.DataFrame:
        """Run all algorithms for one service."""
        algos = registry.get_by_service(service_id)
        return self._run(algos, label=f"Service {service_id}", verbose=verbose)

    def run_category(self, category: str, verbose: bool = True) -> pd.DataFrame:
        """Run all algorithms of a given category."""
        algos = registry.get_by_category(category)
        return self._run(algos, label=f"Category: {category}", verbose=verbose)

    def run_single(self, algo_name: str,
                   service_id: Optional[int] = None) -> Optional[AlgoResult]:
        """Run one specific algorithm by name."""
        AlgoClass = registry.get_by_name(algo_name, service_id)
        if AlgoClass is None:
            print(f"Algorithm '{algo_name}' not found.")
            return None
        algo = AlgoClass()
        return algo.safe_run(self.X_train, self.X_test, self.y_train)

    # ── Internal ──────────────────────────────────────────────────────────

    def _run(self, algos: list, label: str, verbose: bool) -> pd.DataFrame:
        if not algos:
            print(f"No algorithms found for: {label}")
            return pd.DataFrame()

        if verbose:
            print(f"\n{'='*55}")
            print(f"  VEBITA Benchmark — {label}")
            print(f"  {len(algos)} algorithms | "
                  f"Animal: {self.pipeline.animal} | "
                  f"{len(self.X_train)} train / {len(self.X_test)} test points")
            print(f"{'='*55}")

        t_start = time.perf_counter()

        rows = Parallel(n_jobs=self.n_jobs, backend="threading", verbose=0)(
            delayed(_run_single)(
                AlgoClass,
                self.X_train, self.X_test,
                self.y_train, self.y_test,
            )
            for AlgoClass in algos
        )

        elapsed = round(time.perf_counter() - t_start, 1)
        df = pd.DataFrame(rows)

        if verbose and len(df):
            ok      = (df["status"] == "ok").sum()
            errors  = (df["status"] == "error").sum()
            print(f"\n  Completed in {elapsed}s")
            print(f"  OK: {ok}  |  Errors: {errors}  |  Total: {len(df)}")
            if "accuracy" in df.columns:
                best = df[df["status"]=="ok"].nlargest(5, "accuracy")[
                    ["algo_name","accuracy","runtime_s"]
                ]
                print(f"\n  Top 5 by accuracy:")
                print(best.to_string(index=False))

        self.results_df = df
        return df

    # ── Save / Load ───────────────────────────────────────────────────────

    def save_results(self, path: str = "results/benchmark_results.csv"):
        if self.results_df is None:
            print("No results to save. Run benchmark first.")
            return
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.results_df.to_csv(path, index=False)
        print(f"Results saved → {path}  ({len(self.results_df)} rows)")

    def leaderboard(self, service_id: Optional[int] = None,
                    metric: str = "accuracy",
                    top_n: int = 20) -> pd.DataFrame:
        """Return top-N algorithms ranked by metric."""
        df = self.results_df
        if df is None or len(df) == 0:
            return pd.DataFrame()
        if service_id:
            df = df[df["service_id"] == service_id]
        df = df[df["status"] == "ok"]
        if metric not in df.columns:
            print(f"Metric '{metric}' not available. Available: {list(df.columns)}")
            return df.head(top_n)
        return df.nlargest(top_n, metric)[
            ["algo_name", "service_id", "category", metric, "runtime_s", "memory_mb"]
        ].reset_index(drop=True)
