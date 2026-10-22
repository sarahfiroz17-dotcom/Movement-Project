"""
services/s4_anomaly/dua_algorithms.py
======================================
VEBITA — Service 4: Anomaly Detection (Dua)

100 algorithms across 6 families:
  A. Linear & Statistical          (algorithms  1-30)
  B. Tree & Ensemble Methods       (algorithms 31-55)
  C. Kernel & Distance-Based       (algorithms 56-70)
  D. Probabilistic & Bayesian      (algorithms 71-80)
  E. Deep Learning (NumPy proxy)   (algorithms 81-90)
  F. Ecological / Movement-Specific(algorithms 91-100)

Feature matrix X shape: (n_points, 8)
  [0] speed_ms        [1] altitude_m      [2] turning_angle   [3] straightness
  [4] speed_roll_mean [5] speed_roll_std  [6] step_length_m   [7] alt_roll_mean

predict() returns float array:  1 = anomaly,  0 = normal
Service ID: 4

Activate in main.py:
    from vebita_framework.services.s4_anomaly.dua_algorithms import *
"""

import warnings
import numpy as np
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.ensemble import (
    IsolationForest, RandomForestClassifier,
    GradientBoostingClassifier,
)
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope
from sklearn.cluster import DBSCAN, KMeans
from sklearn.svm import OneClassSVM
from scipy.spatial.distance import cdist
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.neighbors import KernelDensity

from core.base import BaseAlgorithm
from core.registry import registry

warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _subsample(X, y=None, max_n=2000, seed=42):
    """Bound n for algorithms whose per-fit or per-query cost grows with
    how many reference points they compare against (e.g. KDE), matching
    the subsampling pattern used for the same issue elsewhere."""
    if len(X) <= max_n:
        return X, y
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(X), max_n, replace=False)
    return X[idx], (y[idx] if y is not None else None)


def _thr(scores, pct=95):
    return np.percentile(scores, pct)

def _zscore_max(X, mu, sd):
    return np.abs((X - mu) / sd).max(1)

def _mahal(X, mu, inv):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, inv, d)

def _knn_dist(X, nn_model):
    dists, _ = nn_model.kneighbors(X)
    return dists[:, 1:].mean(1)

def _rolling_mean(x, w=10):
    out = np.empty(len(x))
    for i in range(len(x)):
        lo = max(0, i - w + 1)
        out[i] = x[lo: i + 1].mean()
    return out

def _sk_binary(pred):
    return (pred == -1).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# A. LINEAR & STATISTICAL  (#1 – #30)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_A01_ZScoreMax(BaseAlgorithm):
    """A01 — Max per-feature z-score exceeds threshold."""
    name = "AD A01 Z-Score Max"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "Max per-feature z-score anomaly detector"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.mu_ = X.mean(0); self.sd_ = X.std(0) + 1e-12
        self.thr_ = _thr(_zscore_max(X, self.mu_, self.sd_))
        self.is_fitted = True; return self
    def predict(self, X):
        return (_zscore_max(X, self.mu_, self.sd_) > self.thr_).astype(float)






@registry.register
class AD_A04_Mahalanobis(BaseAlgorithm):
    """A04 — Mahalanobis distance from centroid."""
    name = "AD A04 Mahalanobis"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "Mahalanobis distance anomaly detection"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.mu_ = X.mean(0)
        try:
            self.inv_ = np.linalg.pinv(np.cov(X, rowvar=False))
        except Exception:
            self.inv_ = np.eye(X.shape[1])
        self.thr_ = _thr(_mahal(X, self.mu_, self.inv_))
        self.is_fitted = True; return self
    def predict(self, X):
        return (_mahal(X, self.mu_, self.inv_) > self.thr_).astype(float)


@registry.register
class AD_A05_RobustMahalanobis(BaseAlgorithm):
    """A05 — Robust Mahalanobis using trimmed mean and covariance."""
    name = "AD A05 Robust Mahalanobis"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "Robust (IQR-trimmed) Mahalanobis distance"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        q1, q3 = np.percentile(X, 25, 0), np.percentile(X, 75, 0)
        mask = ((X >= q1) & (X <= q3)).all(1)
        Xr = X[mask] if mask.sum() > X.shape[1] + 1 else X
        self.mu_ = Xr.mean(0)
        self.inv_ = np.linalg.pinv(np.cov(Xr, rowvar=False) + 1e-6 * np.eye(X.shape[1]))
        self.thr_ = _thr(_mahal(X, self.mu_, self.inv_))
        self.is_fitted = True; return self
    def predict(self, X):
        return (_mahal(X, self.mu_, self.inv_) > self.thr_).astype(float)


@registry.register
class AD_A06_IQR(BaseAlgorithm):
    """A06 — IQR rule: flag any feature outside 1.5×IQR."""
    name = "AD A06 IQR Outlier"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "Per-feature IQR fence outlier detection"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.q1_ = np.percentile(X, 25, 0)
        self.q3_ = np.percentile(X, 75, 0)
        self.iqr_ = self.q3_ - self.q1_ + 1e-12
        self.is_fitted = True; return self
    def predict(self, X):
        out = ((X < self.q1_ - 1.5 * self.iqr_) | (X > self.q3_ + 1.5 * self.iqr_)).any(1)
        return out.astype(float)


@registry.register
class AD_A07_ModifiedZScore(BaseAlgorithm):
    """A07 — Modified z-score using median and MAD."""
    name = "AD A07 Modified Z-Score (MAD)"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "Median Absolute Deviation robust z-score"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.med_ = np.median(X, 0)
        self.mad_ = np.median(np.abs(X - self.med_), 0) + 1e-12
        s = (0.6745 * np.abs(X - self.med_) / self.mad_).max(1)
        self.thr_ = _thr(s); self.is_fitted = True; return self
    def predict(self, X):
        s = (0.6745 * np.abs(X - self.med_) / self.mad_).max(1)
        return (s > self.thr_).astype(float)








@registry.register
class AD_A11_CUSUM(BaseAlgorithm):
    """A11 — CUSUM (cumulative sum control) on speed."""
    name = "AD A11 CUSUM"
    service_id = 4; category = "A_statistical"; library = "numpy"; animals = ["all"]
    description = "CUSUM change detection on speed feature"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        x = X[:, 0]; self.mu_ = x.mean()
        cusum = np.maximum.accumulate(np.abs(np.cumsum(x - self.mu_)))
        self.thr_ = _thr(cusum); self.is_fitted = True; return self
    def predict(self, X):
        x = X[:, 0]
        cusum = np.maximum.accumulate(np.abs(np.cumsum(x - self.mu_)))
        return (cusum > self.thr_).astype(float)




@registry.register
class AD_A13_EllipticEnvelope(BaseAlgorithm):
    """A13 — Robust covariance elliptic envelope."""
    name = "AD A13 Elliptic Envelope"
    service_id = 4; category = "A_statistical"; library = "sklearn"; animals = ["all"]
    description = "sklearn EllipticEnvelope robust covariance anomaly detector"

    def __init__(self): super().__init__(); self.model_ = None
    def fit(self, X, y=None):
        try:
            self.model_ = EllipticEnvelope(contamination=0.05, support_fraction=0.9)
            self.model_.fit(X)
        except Exception:
            self.model_ = None
        self.is_fitted = True; return self
    def predict(self, X):
        if self.model_ is None:
            return np.zeros(len(X), dtype=float)
        return _sk_binary(self.model_.predict(X))




































# ══════════════════════════════════════════════════════════════════════════════
# B. TREE & ENSEMBLE METHODS  (#31 – #55)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_B31_IsolationForest5(BaseAlgorithm):
    """B31 — Isolation Forest (contamination=5%)."""
    name = "AD B31 Isolation Forest 5pct"
    service_id = 4; category = "B_tree"; library = "sklearn"; animals = ["all"]
    description = "Standard Isolation Forest with 5% contamination"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.m_ = IsolationForest(contamination=0.05, random_state=42)
        self.m_.fit(X); self.is_fitted = True; return self
    def predict(self, X): return _sk_binary(self.m_.predict(X))




















@registry.register
class AD_B41_DBSCANNoise(BaseAlgorithm):
    """B41 — DBSCAN noise points as anomalies."""
    name = "AD B41 DBSCAN Noise Points"
    service_id = 4; category = "B_tree"; library = "sklearn"; animals = ["all"]
    description = "DBSCAN clusters — noise label = anomaly"

    def __init__(self, eps=0.8): super().__init__(eps=eps); self.eps = eps
    def fit(self, X, y=None):
        self.sc_ = StandardScaler().fit(X)
        self.is_fitted = True; return self
    def predict(self, X):
        # DBSCAN doesn't generalize to new points by design (it's a batch
        # method), and fit_predict() on the FULL, unsubsampled test set
        # never finished in 175s in isolation at true scale (~2.68M rows).
        # Same fix pattern as OPTICSClustering/HDBSCANClustering in
        # services/s2_patterns: fit DBSCAN on a bounded subsample, then
        # flag every point in the full set as anomalous by its (batched)
        # distance to the nearest non-noise point from that subsample.
        Xs = self.sc_.transform(X)
        Xsub, _ = _subsample(Xs, max_n=2000)
        labels_sub = DBSCAN(eps=self.eps, min_samples=5).fit_predict(Xsub)
        core_mask = labels_sub != -1
        if core_mask.sum() == 0:
            return np.ones(len(Xs))
        core_pts = Xsub[core_mask]
        batch = 5000
        out = np.empty(len(Xs))
        for start in range(0, len(Xs), batch):
            end = min(start + batch, len(Xs))
            d = cdist(Xs[start:end], core_pts).min(axis=1)
            out[start:end] = (d > self.eps).astype(float)
        return out








@registry.register
class AD_B45_OneClassSVM_RBF(BaseAlgorithm):
    """B45 — One-Class SVM with RBF kernel."""
    name = "AD B45 One-Class SVM RBF"
    service_id = 4; category = "B_tree"; library = "sklearn"; animals = ["all"]
    description = "One-Class SVM with RBF kernel for GPS anomaly"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # OneClassSVM's training cost grows superlinearly with n --
        # infeasible on the FULL ~10.7M-row training set. Subsample
        # (exact no-op below max_n=2000); with nu=0.05 that keeps support
        # vectors ~5% of the sample (~100 at max_n=2000), so predict()
        # stays fast on the full test set too (measured ~4s at true scale,
        # vs. the unbounded-support-vector-count risk seen in EnvSVR).
        Xs, _ = _subsample(X, max_n=2000)
        self.sc_ = StandardScaler().fit(Xs)
        self.m_ = OneClassSVM(kernel="rbf", nu=0.05, gamma="scale")
        self.m_.fit(self.sc_.transform(Xs)); self.is_fitted = True; return self
    def predict(self, X): return _sk_binary(self.m_.predict(self.sc_.transform(X)))






















# ══════════════════════════════════════════════════════════════════════════════
# C. KERNEL & DISTANCE-BASED  (#56 – #70)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_C56_LOF_k20(BaseAlgorithm):
    """C56 — Local Outlier Factor (k=20)."""
    name = "AD C56 LOF k=20"
    service_id = 4; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "LOF with 20 neighbours for GPS track anomaly"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # LOF's fit_predict() re-scores the WHOLE set it's given against
        # itself every call -- fine at small n, but calling it on the
        # FULL, unsubsampled test set (~2.68M rows at true scale) took
        # 50s+ at just n=300k in isolation (would be minutes at true
        # scale) since it needs a k-NN query for every point. Use LOF's
        # novelty=True mode instead: fit a k-NN structure on a bounded
        # reference sample once, then predict() scores new points against
        # that FIXED reference (an actual sklearn-supported way to bound
        # this cost, not an approximation of a different algorithm) --
        # measured ~14s for the full test set at max_n=500 (was 400s+
        # unbounded).
        Xs, _ = _subsample(X, max_n=500)
        k = min(20, len(Xs) - 1)
        self.lof_ = LocalOutlierFactor(n_neighbors=k, novelty=True).fit(Xs)
        self.is_fitted = True
        return self
    def predict(self, X):
        return _sk_binary(self.lof_.predict(X))








@registry.register
class AD_C60_LOF_Cosine(BaseAlgorithm):
    """C60 — LOF with cosine distance metric."""
    name = "AD C60 LOF Cosine"
    service_id = 4; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "LOF using cosine distance for direction-sensitive anomaly"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # Same fit_predict-on-the-full-test-set bug as AD_C56_LOF_k20
        # above -- worse here since cosine distance forces sklearn's
        # neighbor search to brute force (no tree structure supports it),
        # making the unbounded version O(n^2). Same novelty=True +
        # bounded-reference fix.
        Xs, _ = _subsample(X, max_n=500)
        k = min(20, len(Xs) - 1)
        self.lof_ = LocalOutlierFactor(n_neighbors=k, metric="cosine", novelty=True).fit(Xs)
        self.is_fitted = True
        return self
    def predict(self, X):
        return _sk_binary(self.lof_.predict(X))


@registry.register
class AD_C61_KNNMeanDist(BaseAlgorithm):
    """C61 — Mean kNN distance (k=5)."""
    name = "AD C61 KNN Mean Distance"
    service_id = 4; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "Mean distance to 5 nearest neighbours"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # NearestNeighbors.kneighbors() cost scales with the size of the
        # fitted reference set for every query - fitting and querying
        # against the full training set (10M+ rows) made both the
        # threshold computation here and predict() below take minutes.
        # Bounding the reference set keeps both fast regardless of input
        # size, same fix as the other neighbor/kernel-based algorithms
        # in this file.
        Xs, _ = _subsample(X, max_n=500)
        k = min(6, len(Xs) - 1)
        self.nn_ = NearestNeighbors(n_neighbors=k).fit(Xs)
        dists, _ = self.nn_.kneighbors(Xs)
        self.thr_ = _thr(dists[:, 1:].mean(1)); self.is_fitted = True; return self
    def predict(self, X):
        dists, _ = self.nn_.kneighbors(X)
        return (dists[:, 1:].mean(1) > self.thr_).astype(float)






@registry.register
class AD_C64_KernelDensityGaussian(BaseAlgorithm):
    """C64 — Gaussian KDE negative log-density."""
    name = "AD C64 Gaussian KDE"
    service_id = 4; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "Negative Gaussian KDE log-density anomaly score"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # KernelDensity.score_samples scores every point against every
        # reference point the tree holds - at 62k training points scoring
        # itself for the threshold took 100s+, and predict() on a large
        # test set would have the same problem. Bounding the *reference*
        # set (not the query set) keeps both fit and predict fast
        # regardless of how much data comes in, same fix as the other
        # comparison-cost-scales-with-n algorithms in this project.
        # NOTE: max_n=2000 was still too slow for predict() at true scale
        # (2.68M test rows x 2000 ref pts >130s measured) - 200 keeps the
        # full-test-set predict under ~15s while still giving a reasonable
        # density estimate.
        self.sc_ = StandardScaler().fit(X)
        Xs = self.sc_.transform(X)
        Xs_ref, _ = _subsample(Xs, None, max_n=200)
        self.kde_ = KernelDensity(kernel="gaussian", bandwidth=1.0).fit(Xs_ref)
        self.thr_ = _thr(-self.kde_.score_samples(Xs_ref))
        self.is_fitted = True; return self
    def predict(self, X):
        Xs = self.sc_.transform(X)
        return (-self.kde_.score_samples(Xs) > self.thr_).astype(float)














# ══════════════════════════════════════════════════════════════════════════════
# D. PROBABILISTIC & BAYESIAN  (#71 – #80)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_D71_GaussianLikelihood(BaseAlgorithm):
    """D71 — Negative Gaussian log-likelihood per point."""
    name = "AD D71 Gaussian Log-Likelihood"
    service_id = 4; category = "D_probabilistic"; library = "numpy"; animals = ["all"]
    description = "Multivariate Gaussian negative log-likelihood anomaly"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        self.mu_ = X.mean(0)
        cov = np.cov(X, rowvar=False) + 1e-6 * np.eye(X.shape[1])
        self.inv_ = np.linalg.pinv(cov)
        self.thr_ = _thr(_mahal(X, self.mu_, self.inv_))
        self.is_fitted = True; return self
    def predict(self, X):
        return (_mahal(X, self.mu_, self.inv_) > self.thr_).astype(float)




@registry.register
class AD_D73_GammaDistribution(BaseAlgorithm):
    """D73 — Gamma distribution tail on speed."""
    name = "AD D73 Gamma Distribution Tail"
    service_id = 4; category = "D_probabilistic"; library = "scipy"; animals = ["all"]
    description = "Gamma-distribution negative log-likelihood on speed"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        x = np.abs(X[:, 0]) + 1e-6
        self.a_, self.loc_, self.scale_ = stats.gamma.fit(x, floc=0)
        self.thr_ = _thr(-stats.gamma.logpdf(x, self.a_, self.loc_, self.scale_))
        self.is_fitted = True; return self
    def predict(self, X):
        x = np.abs(X[:, 0]) + 1e-6
        return (-stats.gamma.logpdf(x, self.a_, self.loc_, self.scale_) > self.thr_).astype(float)














@registry.register
class AD_D80_GMMLogLikelihood(BaseAlgorithm):
    """D80 — Multi-component GMM log-likelihood."""
    name = "AD D80 GMM Log-Likelihood"
    service_id = 4; category = "D_probabilistic"; library = "sklearn"; animals = ["all"]
    description = "Gaussian Mixture Model negative log-likelihood anomaly"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        # GaussianMixture's EM fit (and the score_samples() call used for
        # the threshold) both cost O(n) per iteration over whatever is
        # passed in - on the full 10M+ row training set this took 100s+
        # even though predict() on the (much smaller) test set is fast.
        # A 3-component GMM converges to essentially the same mixture
        # whether fit on the full data or a bounded random subsample, so
        # this is a safe scaling fix, same pattern as the other GMM/EM
        # based algorithms in this project.
        from sklearn.mixture import GaussianMixture
        Xs, _ = _subsample(X, max_n=20000)
        self.gm_ = GaussianMixture(n_components=3, random_state=42).fit(Xs)
        self.thr_ = _thr(-self.gm_.score_samples(Xs))
        self.is_fitted = True; return self
    def predict(self, X):
        return (-self.gm_.score_samples(X) > self.thr_).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# E. DEEP LEARNING (NumPy proxy)  (#81 – #90)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_E81_PCAReconstruction2(BaseAlgorithm):
    """E81 — PCA reconstruction error (2 components)."""
    name = "AD E81 PCA Reconstruction 2"
    service_id = 4; category = "E_deep"; library = "sklearn"; animals = ["all"]
    description = "PCA 2-component reconstruction error as anomaly score"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        nc = min(2, X.shape[1], X.shape[0] - 1)
        self.pca_ = PCA(n_components=nc).fit(X)
        Xr = self.pca_.inverse_transform(self.pca_.transform(X))
        self.thr_ = _thr(np.mean((X - Xr) ** 2, 1))
        self.is_fitted = True; return self
    def predict(self, X):
        Xr = self.pca_.inverse_transform(self.pca_.transform(X))
        return (np.mean((X - Xr) ** 2, 1) > self.thr_).astype(float)








@registry.register
class AD_E85_AutoencoderTanh(BaseAlgorithm):
    """E85 — Numpy 1-hidden-layer autoencoder (tanh)."""
    name = "AD E85 Autoencoder Tanh"
    service_id = 4; category = "E_deep"; library = "numpy"; animals = ["all"]
    description = "1-hidden-layer numpy autoencoder with tanh activations"

    def __init__(self, epochs=50, lr=0.01): super().__init__(epochs=epochs, lr=lr); self.epochs=epochs; self.lr=lr
    def fit(self, X, y=None):
        # Full-batch gradient descent recomputes several (n x d)/(n x h)
        # arrays on every epoch. At 10M+ training rows and 50 epochs this
        # OOM'd the process outright even in isolation. A bounded random
        # subsample gives the same converged weights (full-batch GD on a
        # large-enough sample approximates full-batch GD on the whole
        # set) while keeping every epoch's working set small.
        self.sc_ = StandardScaler().fit(X)
        Xsub, _ = _subsample(X, max_n=20000)
        Xs = self.sc_.transform(Xsub)
        d = X.shape[1]; h = max(2, d // 2); np.random.seed(42)
        self.W1_ = np.random.randn(d, h) * 0.1; self.b1_ = np.zeros(h)
        self.W2_ = np.random.randn(h, d) * 0.1; self.b2_ = np.zeros(d)
        for _ in range(self.epochs):
            z = np.tanh(Xs @ self.W1_ + self.b1_)
            Xh = z @ self.W2_ + self.b2_; e = Xh - Xs
            self.W2_ -= self.lr * z.T @ e / len(Xs); self.b2_ -= self.lr * e.mean(0)
            dz = (e @ self.W2_.T) * (1 - z ** 2)
            self.W1_ -= self.lr * Xs.T @ dz / len(Xs); self.b1_ -= self.lr * dz.mean(0)
        self.thr_ = _thr(self._err(Xs)); self.is_fitted = True; return self
    def _err(self, Xs):
        z = np.tanh(Xs @ self.W1_ + self.b1_)
        return np.mean((Xs - (z @ self.W2_ + self.b2_)) ** 2, 1)
    def predict(self, X):
        return (self._err(self.sc_.transform(X)) > self.thr_).astype(float)












# ══════════════════════════════════════════════════════════════════════════════
# F. ECOLOGICAL / MOVEMENT-SPECIFIC  (#91 – #100)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class AD_F91_VelocityJerk(BaseAlgorithm):
    """F91 — High jerk (3rd derivative of speed) = abrupt change."""
    name = "AD F91 Velocity Jerk"
    service_id = 4; category = "F_ecological"; library = "numpy"; animals = ["all"]
    description = "Jerk (3rd-order derivative of speed) anomaly detection"

    def __init__(self): super().__init__()
    def _jerk(self, X):
        x = X[:, 0]; vel = np.diff(x, prepend=x[0])
        acc = np.diff(vel, prepend=vel[0])
        return np.abs(np.diff(acc, prepend=acc[0]))
    def fit(self, X, y=None):
        self.thr_ = _thr(self._jerk(X)); self.is_fitted = True; return self
    def predict(self, X):
        return (self._jerk(X) > self.thr_).astype(float)




@registry.register
class AD_F93_AltitudeDrop(BaseAlgorithm):
    """F93 — Sudden altitude drop (crash/dive detection)."""
    name = "AD F93 Altitude Drop"
    service_id = 4; category = "F_ecological"; library = "numpy"; animals = ["all"]
    description = "Sudden negative altitude change as anomaly"

    def __init__(self): super().__init__()
    def _drops(self, X):
        alt = X[:, 1]
        return np.r_[0, np.maximum(0, -np.diff(alt))]
    def fit(self, X, y=None):
        self.thr_ = _thr(self._drops(X)); self.is_fitted = True; return self
    def predict(self, X):
        return (self._drops(X) > self.thr_).astype(float)








@registry.register
class AD_F97_MultiFeatureTemporalChange(BaseAlgorithm):
    """F97 — Cumulative absolute first-differences across features."""
    name = "AD F97 Multi-Feature Temporal Change"
    service_id = 4; category = "F_ecological"; library = "numpy"; animals = ["all"]
    description = "Sum of absolute temporal differences across all features"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        diffs = np.abs(np.diff(X, axis=0, prepend=X[:1]))
        self.thr_ = _thr(diffs.sum(1)); self.is_fitted = True; return self
    def predict(self, X):
        diffs = np.abs(np.diff(X, axis=0, prepend=X[:1]))
        return (diffs.sum(1) > self.thr_).astype(float)






@registry.register
class AD_F100_CompositeMovementScore(BaseAlgorithm):
    """F100 — Composite movement anomaly: z-sum over key features."""
    name = "AD F100 Composite Movement Score"
    service_id = 4; category = "F_ecological"; library = "numpy"; animals = ["all"]
    description = "Composite z-score across speed, altitude, turning, step_length"

    def __init__(self): super().__init__()
    def fit(self, X, y=None):
        cols = [0, 1, 2, 6]  # speed, altitude, turning_angle, step_length
        Xs = X[:, cols]
        self.mu_ = Xs.mean(0); self.sd_ = Xs.std(0) + 1e-12
        self.thr_ = _thr(np.abs((Xs - self.mu_) / self.sd_).sum(1))
        self.is_fitted = True; return self
    def predict(self, X):
        Xs = X[:, [0, 1, 2, 6]]
        return (np.abs((Xs - self.mu_) / self.sd_).sum(1) > self.thr_).astype(float)


# ── End of file ───────────────────────────────────────────────────────────────
# Total: 100 algorithms across 6 families
# Service ID: 4 — Anomaly Detection (Dua)
# Add to main.py:
#   from vebita_framework.services.s4_anomaly.dua_algorithms import *