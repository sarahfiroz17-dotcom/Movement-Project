"""
services/example_algorithms.py
================================
VEBITA — Example algorithms for ALL 6 services.

This file shows each team member EXACTLY how to add their algorithms.
Copy this pattern, change the class name, change fit() and predict().
That's it.

Each team member works in their own file:
    services/s1_timeseries/     → Abdul Rehman
    services/s2_patterns/       → Ritikha
    services/s3_environment/    → Sarah
    services/s4_anomaly/        → Arshan
    services/s5_segmentation/   → Dua  (already has 83 algos)
    services/s6_classification/ → Syeda Hiba
"""

import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA

from core.base import BaseAlgorithm
from core.registry import registry


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 1 — Time Series Analysis (Abdul Rehman)
# ═══════════════════════════════════════════════════════════════════════

@registry.register
class MovingAverageForecast(BaseAlgorithm):
    """Predict next speed value using rolling mean."""
    name        = "Moving Average Forecast"
    service_id  = 1
    category    = "statistical"
    library     = "numpy"
    animals     = ["all"]
    description = "Rolling window mean forecast for speed time series"

    def __init__(self, window: int = 5):
        super().__init__(window=window)
        self.window = window
        self.mean_  = None

    def fit(self, X, y=None):
        self.mean_ = np.convolve(
            X[:, 0], np.ones(self.window) / self.window, mode="same"
        )
        self.is_fitted = True
        return self

    def predict(self, X):
        return np.convolve(
            X[:, 0], np.ones(self.window) / self.window, mode="same"
        )


@registry.register
class ExponentialSmoothingForecast(BaseAlgorithm):
    """Exponential weighted moving average."""
    name        = "Exponential Smoothing"
    service_id  = 1
    category    = "statistical"
    library     = "numpy"
    animals     = ["all"]
    description = "Exponential weighted smoothing of speed signal"

    def __init__(self, alpha: float = 0.3):
        super().__init__(alpha=alpha)
        self.alpha = alpha

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        speed = X[:, 0]
        result = np.zeros_like(speed)
        result[0] = speed[0]
        for i in range(1, len(speed)):
            result[i] = self.alpha * speed[i] + (1 - self.alpha) * result[i-1]
        return result


@registry.register
class LinearTrendForecast(BaseAlgorithm):
    """Fit linear trend to speed over time."""
    name        = "Linear Trend"
    service_id  = 1
    category    = "statistical"
    library     = "sklearn"
    animals     = ["all"]
    description = "Linear regression trend on speed feature"

    def __init__(self):
        super().__init__()
        self.model = LinearRegression()

    def fit(self, X, y=None):
        t = np.arange(len(X)).reshape(-1, 1)
        self.model.fit(t, X[:, 0])
        self.is_fitted = True
        return self

    def predict(self, X):
        t = np.arange(len(X)).reshape(-1, 1)
        return self.model.predict(t)


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 2 — Pattern Recognition / Trajectory Clustering (Ritikha)
# ═══════════════════════════════════════════════════════════════════════

class KMeansTrajectory(BaseAlgorithm):
    """K-means clustering of movement features."""
    name        = "K-Means Trajectory Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "K-means on movement feature vectors"

    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        super().__init__(n_clusters=n_clusters)
        self.model = KMeans(n_clusters=n_clusters,
                            random_state=random_state, n_init=10)

    def fit(self, X, y=None):
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)


class DBSCANTrajectory(BaseAlgorithm):
    """DBSCAN density-based trajectory clustering."""
    name        = "DBSCAN Trajectory"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Density-based spatial clustering of movement"

    def __init__(self, eps: float = 0.5, min_samples: int = 10):
        super().__init__(eps=eps, min_samples=min_samples)
        self.model = DBSCAN(eps=eps, min_samples=min_samples)

    def fit(self, X, y=None):
        self.labels_ = self.model.fit_predict(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.fit_predict(X)


class PCAMotifDetection(BaseAlgorithm):
    """PCA-based dimensionality reduction for motif discovery."""
    name        = "PCA Motif Detection"
    service_id  = 2
    category    = "dimensionality_reduction"
    library     = "sklearn"
    animals     = ["all"]
    description = "PCA projection then k-means cluster assignment"

    def __init__(self, n_components: int = 2, n_clusters: int = 4):
        super().__init__(n_components=n_components, n_clusters=n_clusters)
        self.pca = PCA(n_components=n_components)
        self.km  = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)

    def fit(self, X, y=None):
        X_low = self.pca.fit_transform(X)
        self.km.fit(X_low)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.km.predict(self.pca.transform(X))


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 3 — Environmental Factors Integration (Sarah)
# ═══════════════════════════════════════════════════════════════════════

@registry.register
class SpeedAltitudeCorrelation(BaseAlgorithm):
    """Correlate speed with altitude as environmental proxy."""
    name        = "Speed-Altitude Correlation"
    service_id  = 3
    category    = "correlation"
    library     = "numpy"
    animals     = ["all"]
    description = "Linear regression: speed ~ altitude"

    def __init__(self):
        super().__init__()
        self.model = LinearRegression()

    def fit(self, X, y=None):
        altitude = X[:, 1].reshape(-1, 1)
        speed    = X[:, 0]
        self.model.fit(altitude, speed)
        self.is_fitted = True
        return self

    def predict(self, X):
        altitude = X[:, 1].reshape(-1, 1)
        return self.model.predict(altitude)


class StraightnessBarrierDetector(BaseAlgorithm):
    """Use straightness index to detect barrier effect."""
    name        = "Straightness Barrier Detector"
    service_id  = 3
    category    = "environmental"
    library     = "numpy"
    animals     = ["mammals", "birds"]
    description = "Low straightness = possible barrier encountered"

    def __init__(self, threshold: float = 0.3):
        super().__init__(threshold=threshold)
        self.threshold = threshold

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        straightness = X[:, 3]
        return (straightness < self.threshold).astype(int)


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 4 — Anomaly Detection (Arshan)
# ═══════════════════════════════════════════════════════════════════════

@registry.register
class IsolationForestAnomaly(BaseAlgorithm):
    """Isolation Forest anomaly detection."""
    name        = "Isolation Forest"
    service_id  = 4
    category    = "anomaly_detection"
    library     = "sklearn"
    animals     = ["all"]
    description = "Tree-based anomaly scoring. High score = anomaly."

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        super().__init__(contamination=contamination)
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
        )

    def fit(self, X, y=None):
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        # Returns 1 (normal) or -1 (anomaly) → convert to 0/1
        raw = self.model.predict(X)
        return (raw == -1).astype(int)


@registry.register
class SpeedZScoreAnomaly(BaseAlgorithm):
    """Flag points where speed deviates >3 std from mean."""
    name        = "Speed Z-Score Anomaly"
    service_id  = 4
    category    = "statistical"
    library     = "numpy"
    animals     = ["all"]
    description = "Z-score threshold on speed feature"

    def __init__(self, threshold: float = 3.0):
        super().__init__(threshold=threshold)
        self.threshold = threshold
        self.mean_ = None
        self.std_  = None

    def fit(self, X, y=None):
        self.mean_ = X[:, 0].mean()
        self.std_  = X[:, 0].std() + 1e-9
        self.is_fitted = True
        return self

    def predict(self, X):
        z = np.abs((X[:, 0] - self.mean_) / self.std_)
        return (z > self.threshold).astype(int)


class TurningAngleAnomaly(BaseAlgorithm):
    """Flag sudden extreme turning angles as anomalies."""
    name        = "Turning Angle Anomaly"
    service_id  = 4
    category    = "statistical"
    library     = "numpy"
    animals     = ["birds", "mammals"]
    description = "Extreme turning angles indicate barrier or threat response"

    def __init__(self, threshold: float = 150.0):
        super().__init__(threshold=threshold)
        self.threshold = threshold

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        turning = X[:, 2]
        return (turning > self.threshold).astype(int)


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 5 — Trajectory Segmentation (Dua) — 3 examples shown
# Full 83 algorithms already in services/s5_segmentation/
# ═══════════════════════════════════════════════════════════════════════

@registry.register
class KMeansSegmentation(BaseAlgorithm):
    """K-means as simple segmentation baseline."""
    name        = "K-Means Segmentation"
    service_id  = 5
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Assign each GPS point to nearest behavioral centroid"

    def __init__(self, n_states: int = 3, random_state: int = 42):
        super().__init__(n_states=n_states)
        self.model = KMeans(n_clusters=n_states,
                            random_state=random_state, n_init=10)

    def fit(self, X, y=None):
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)


class SpeedThresholdSegmentation(BaseAlgorithm):
    """Rule-based: segment by speed thresholds."""
    name        = "Speed Threshold Segmentation"
    service_id  = 5
    category    = "rule_based"
    library     = "numpy"
    animals     = ["all"]
    description = "Fast=migration, slow=foraging, near-zero=roosting"

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        speed = X[:, 0]
        labels = np.zeros(len(speed), dtype=int)
        labels[speed > 1.5] = 1   # migration
        labels[speed < 0.3] = 2   # roosting
        return labels


# ═══════════════════════════════════════════════════════════════════════
# SERVICE 6 — Behavioural Classification (Syeda Hiba)
# ═══════════════════════════════════════════════════════════════════════

@registry.register
class RandomForestBehavior(BaseAlgorithm):
    """Random Forest supervised behavioral classifier."""
    name        = "Random Forest Classifier"
    service_id  = 6
    category    = "supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "Supervised RF on labeled behavioral segments"

    def __init__(self, n_estimators: int = 100, random_state: int = 42):
        super().__init__(n_estimators=n_estimators)
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state,
        )

    def fit(self, X, y=None):
        if y is None:
            raise ValueError("RandomForestBehavior needs labels y")
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)


@registry.register
class NearestCentroidBehavior(BaseAlgorithm):
    """Classify behavior by nearest class centroid."""
    name        = "Nearest Centroid Classifier"
    service_id  = 6
    category    = "supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "Assigns label of nearest class mean vector"

    def __init__(self):
        super().__init__()
        self.centroids_ = {}

    def fit(self, X, y=None):
        if y is None:
            raise ValueError("NearestCentroidBehavior needs labels y")
        for label in np.unique(y):
            self.centroids_[label] = X[y == label].mean(axis=0)
        self.is_fitted = True
        return self

    def predict(self, X):
        labels  = list(self.centroids_.keys())
        centers = np.array([self.centroids_[l] for l in labels])
        dists   = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        return np.array([labels[i] for i in np.argmin(dists, axis=1)])
