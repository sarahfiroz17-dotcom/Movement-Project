import time
import traceback
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


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


class BaseAlgorithm(ABC):

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
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def fit_predict(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> np.ndarray:
        return self.fit(X, y).predict(X)

    def info(self) -> dict:
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
