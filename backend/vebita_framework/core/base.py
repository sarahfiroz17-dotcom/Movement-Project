"""
core/base.py
============
VEBITA Shared Framework — Base Algorithm Interface

EVERY algorithm across all 6 services must inherit from BaseAlgorithm.
This guarantees the benchmark runner can run all 550+ algorithms
with zero custom code per algorithm.

HOW TO USE (for each team member):
------------------------------------
1. Inherit from BaseAlgorithm
2. Set service_id, category, library in your class
3. Implement fit() and predict()
4. Register with @registry.register decorator
5. Done — benchmark runner picks it up automatically

Example:
    from core.base import BaseAlgorithm
    from core.registry import registry

    @registry.register
    class MyAlgorithm(BaseAlgorithm):
        service_id = 5
        category   = "hmm"
        library    = "numpy"

        def fit(self, X, y=None):
            # train your model on X
            return self

        def predict(self, X):
            # return array of labels or scores
            return labels
"""

import time
import traceback
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# ── Result container returned by every algorithm run ─────────────────────
@dataclass
class AlgoResult:
    algo_name:      str
    service_id:     int
    category:       str
    status:         str           # "ok" | "error" | "timeout"
    predictions:    Optional[np.ndarray] = None
    scores:         Optional[np.ndarray] = None  # anomaly scores / probabilities
    runtime_s:      float = 0.0
    memory_mb:      float = 0.0
    error_msg:      str   = ""
    params:         Dict[str, Any] = field(default_factory=dict)
    metadata:       Dict[str, Any] = field(default_factory=dict)


# ── Base class every algorithm inherits ──────────────────────────────────
class BaseAlgorithm(ABC):
    """
    Abstract base class for all VEBITA algorithms.

    Class-level attributes (set in your subclass):
        name       : human-readable name shown in reports
        service_id : 1–6 (which service this belongs to)
        category   : e.g. "hmm", "clustering", "deep_learning", "statistical"
        library    : e.g. "numpy", "sklearn", "pytorch", "hmmlearn"
        animals    : list of animal types this works for
        description: one-line description for the dashboard
    """

    name:        str = "Unnamed Algorithm"
    service_id:  int = 0
    category:    str = "uncategorized"
    library:     str = "numpy"
    animals:     list = ["all"]
    description: str = ""

    def __init__(self, **params):
        self.params      = params
        self.is_fitted   = False
        self._fit_time   = 0.0

    @abstractmethod
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> "BaseAlgorithm":
        """
        Train the algorithm on feature matrix X.
        y is optional ground-truth labels (for supervised algorithms).
        Must return self.
        """
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Return predictions for X.
        For segmentation/classification: integer or string labels per point.
        For anomaly detection: anomaly scores (higher = more anomalous).
        For time series: transformed or forecasted values.
        """
        ...

    def fit_predict(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        """Convenience: fit then predict on same data."""
        return self.fit(X, y).predict(X)

    def info(self) -> dict:
        """Return metadata dict for the registry and dashboard."""
        return {
            "name":        self.name,
            "service_id":  self.service_id,
            "category":    self.category,
            "library":     self.library,
            "animals":     self.animals,
            "description": self.description,
            "params":      self.params,
        }

    def safe_run(self, X_train: np.ndarray, X_test: np.ndarray,
                 y_train: Optional[np.ndarray] = None,
                 timeout_s: float = 120.0) -> AlgoResult:
        """
        Run fit + predict safely, catching all errors and measuring time.
        Called by the benchmark runner — do not override this.
        """
        import tracemalloc
        result = AlgoResult(
            algo_name  = self.name,
            service_id = self.service_id,
            category   = self.category,
            status     = "error",
            params     = self.params,
        )

        try:
            tracemalloc.start()
            t0 = time.perf_counter()

            self.fit(X_train, y_train)
            preds = self.predict(X_test)

            result.runtime_s   = round(time.perf_counter() - t0, 4)
            _, peak            = tracemalloc.get_traced_memory()
            result.memory_mb   = round(peak / 1_048_576, 2)
            result.predictions = np.array(preds)
            result.status      = "ok"

        except Exception as e:
            result.error_msg = f"{type(e).__name__}: {str(e)}"
            result.status    = "error"

        finally:
            tracemalloc.stop()

        return result
