"""
TEMPLATE — Copy this file and rename it for your service.

Instructions:
1. Copy this file to your service folder
   e.g. services/s5_segmentation/dua_algorithms.py

2. Change service_id to your service number (1–6)

3. For each algorithm:
   - Change the class name
   - Set name, category, library, description
   - Implement fit() and predict()
   - Keep the @registry.register decorator

4. In run_benchmark.py, add this line at the top:
   from services.s5_segmentation.dua_algorithms import *

That's it. The benchmark runner does the rest.

RULES:
- Every class MUST have a unique `name` within your service
- fit() MUST return self
- predict() MUST return a numpy array the same length as X
- Never crash — if something fails, raise an exception and
  the benchmark runner will catch it and mark status="error"
"""

import numpy as np
from core.base import BaseAlgorithm
from core.registry import registry


# ── ALGORITHM TEMPLATE ────────────────────────────────────────────────
# Copy this block for each of your 80+ algorithms

@registry.register
class MyAlgorithmName(BaseAlgorithm):
    """One-line docstring describing what this algo does."""

    # ── Required class attributes ─────────────────────────────────────
    name        = "My Algorithm Name"        # Must be unique in your service
    service_id  = 5                          # Change to your service number
    category    = "clustering"               # e.g. hmm, clustering, statistical,
                                             # deep_learning, rule_based, ecological
    library     = "numpy"                    # Main library used
    animals     = ["all"]                    # or ["birds"], ["mammals"], etc.
    description = "Short description here"

    # ── Constructor ───────────────────────────────────────────────────
    def __init__(self, param1: int = 3, param2: float = 0.5):
        super().__init__(param1=param1, param2=param2)
        self.param1 = param1
        self.param2 = param2
        # Initialize your model here
        # self.model = SomeModel(param1)

    # ── Training ──────────────────────────────────────────────────────
    def fit(self, X: np.ndarray, y=None) -> "MyAlgorithmName":
        """
        X shape: (n_points, 8) — the 8 movement features
        Features: speed_ms, altitude_m, turning_angle, straightness,
                  speed_roll_mean, speed_roll_std, step_length_m, alt_roll_mean

        y: integer labels (0,1,2,...) or None for unsupervised algorithms

        Must return self.
        """
        # === YOUR TRAINING CODE HERE ===
        # Example:
        # self.model.fit(X, y)
        self.is_fitted = True
        return self   # <-- always return self

    # ── Prediction ────────────────────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Must return a numpy array of length len(X).

        For segmentation/classification: integer labels [0, 1, 2, ...]
        For anomaly detection: binary [0=normal, 1=anomaly]
        For time series: predicted values (same shape as input feature)
        """
        # === YOUR PREDICTION CODE HERE ===
        # Example:
        # return self.model.predict(X)
        return np.zeros(len(X), dtype=int)   # placeholder


# ── HOW TO ADD 80 MORE ALGORITHMS ────────────────────────────────────
#
# Just keep adding classes with @registry.register above each one.
# The pattern is always the same:
#
# @registry.register
# class Algorithm2(BaseAlgorithm):
#     name = "Algorithm 2"
#     service_id = 5
#     ...
#
# @registry.register
# class Algorithm3(BaseAlgorithm):
#     name = "Algorithm 3"
#     service_id = 5
#     ...
#
# Python will auto-register all of them when the file is imported.
