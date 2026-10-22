"""
services/s2_patterns/ritikha_algorithms.py
==========================================
Service 2 - Pattern Recognition and Trajectory Clustering (Ritikha)
87 algorithms for animal GPS movement data.
Features: speed_ms, altitude_m, turning_angle, straightness,
          speed_roll_mean, speed_roll_std, step_length_m, alt_roll_mean
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from core.base import BaseAlgorithm
from core.registry import registry


# ---- helpers ---------------------------------------------------------------

_K = 4  # default number of clusters


def _nc(y=None):
    if y is not None and len(np.unique(y)) >= 2:
        return int(len(np.unique(y)))
    return _K


def _nearest(centers, X, batch=5000):
    """Assign each row of X to nearest center; return integer labels.

    Was a single 3D broadcast (X[:,None,:] - centers[None,:,:], shape
    (n, k, d)) over the WHOLE input at once. Fine for the small, fixed k
    most callers here use (K-Means/DBSCAN/HDBSCAN), but OPTICSClustering's
    fit_predict can produce many more clusters (dozens of small density
    clusters), and at n~2.68M rows (true scale) x k~dozens that array is
    multiple GB -> OOM (verified: 10+GB for k=60 at true scale). Batched
    via cdist (argmin of euclidean distance == argmin of squared euclidean
    distance, so results are byte-identical -- verified on randomized
    trials), bounding peak memory regardless of n or k for every caller.
    """
    from scipy.spatial.distance import cdist
    out = np.empty(len(X), dtype=int)
    for start in range(0, len(X), batch):
        end = min(start + batch, len(X))
        d = cdist(X[start:end], centers)
        out[start:end] = np.argmin(d, axis=1)
    return out


def _discretize(X, col=0, n_bins=4):
    """Quantile-bin one feature column into 0..n_bins-1."""
    s    = X[:, col].astype(float)
    cuts = np.percentile(s, np.linspace(0, 100, n_bins + 1)[1:-1])
    return np.digitize(s, cuts)


def _cluster_centers(X, labels, k):
    """Compute per-cluster means; fallback to global mean for empty clusters."""
    mu = X.mean(axis=0)
    return np.array([
        X[labels == j].mean(axis=0) if (labels == j).any() else mu
        for j in range(k)
    ])


def _subsample(X, y, max_n=300, seed=42):
    """Return a random subsample of at most max_n rows (keeps y aligned)."""
    if len(X) <= max_n:
        return X, y
    np.random.seed(seed)
    idx = np.random.choice(len(X), max_n, replace=False)
    return X[idx], (y[idx] if y is not None else None)


def _safe_kmeans(X, k, seed=42):
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    return km.fit(X)


# ============================================================
# CLUSTERING (24)
# ============================================================

@registry.register
class KMeansMovementClustering(BaseAlgorithm):
    name        = "K-Means Movement Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "K-Means clustering of all 8 movement features"

    def __init__(self, k=_K):
        super().__init__(k=k)
        self.k = k

    def fit(self, X, y=None):
        k = _nc(y) if y is not None else self.k
        self.model_    = _safe_kmeans(X, k)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model_.predict(X)




@registry.register
class DBSCANMovementClustering(BaseAlgorithm):
    name        = "DBSCAN Movement Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "DBSCAN density clustering of normalised movement features"

    def __init__(self, eps=0.5, min_samples=5):
        super().__init__(eps=eps, min_samples=min_samples)
        self.eps         = eps
        self.min_samples = min_samples

    def fit(self, X, y=None):
        # DBSCAN's neighbor-graph can hold O(n^2) point-pairs when real GPS
        # data has dense clusters (e.g. long stationary/roosting periods),
        # even though sklearn uses a tree internally - this OOM-crashed on a
        # real ~62k-point movement file. Subsample like the other clustering
        # algos in this file to bound memory.
        Xf, yf         = _subsample(X, y, max_n=300)
        from sklearn.preprocessing import StandardScaler
        self.scaler_   = StandardScaler().fit(Xf)
        Xs             = self.scaler_.transform(Xf)
        from sklearn.cluster import DBSCAN
        labels         = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit_predict(Xs)
        self.k_        = max(2, len(np.unique(labels[labels >= 0])))
        # map noise to nearest valid cluster using centers
        valid = labels >= 0
        if valid.any():
            self.centers_ = _cluster_centers(Xf[valid], labels[valid], self.k_)
        else:
            self.centers_ = _safe_kmeans(Xf, _K).cluster_centers_
        self.is_fitted = True
        return self

    def predict(self, X):
        # predict() must stay a plain nearest-center lookup so it scales to
        # any size test set - re-running a full DBSCAN fit_predict here (as
        # before) reintroduces the same O(n^2)-memory risk on large data.
        return _nearest(self.centers_, X)


@registry.register
class HDBSCANClustering(BaseAlgorithm):
    name        = "HDBSCAN Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "HDBSCAN hierarchical density clustering of movement features"

    def __init__(self, min_cluster_size=10):
        super().__init__(min_cluster_size=min_cluster_size)
        self.min_cluster_size = min_cluster_size

    def fit(self, X, y=None):
        # Same bug as its sibling OPTICSClustering below (see that class's
        # comment): HDBSCAN's default algorithm builds an O(n^2) pairwise
        # distance structure over the FULL dataset -- OOM-kills at
        # true/large scale (~10.7M rows). This sibling was missed when
        # OPTICSClustering got the same fix; applying the identical
        # subsample-before-fit pattern here.
        Xs, _ = _subsample(X, y, max_n=300)
        try:
            from sklearn.cluster import HDBSCAN
            labels = HDBSCAN(min_cluster_size=self.min_cluster_size).fit_predict(Xs)
        except ImportError:
            from sklearn.cluster import DBSCAN
            labels = DBSCAN(eps=0.8, min_samples=self.min_cluster_size).fit_predict(Xs)
        k = max(2, len(np.unique(labels[labels >= 0])))
        valid = labels >= 0
        self.centers_ = _cluster_centers(Xs[valid] if valid.any() else Xs,
                                         labels[valid] if valid.any() else np.zeros(len(Xs), int), k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class OPTICSClustering(BaseAlgorithm):
    name        = "OPTICS Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "OPTICS density ordering clustering of movement features"

    def fit(self, X, y=None):
        from sklearn.cluster import OPTICS
        # Every sibling clustering algo here (Agglomerative/Spectral/MeanShift)
        # subsamples before fitting. This one didn't: sklearn's OPTICS builds
        # an O(n^2) pairwise distance structure over the FULL dataset, which
        # OOM-kills on medium/large movement-tracking files. Subsample like
        # its siblings to fix both the crash and the runtime.
        Xs, _          = _subsample(X, y, max_n=300)
        labels         = OPTICS(min_samples=5).fit_predict(Xs)
        k              = max(2, len(np.unique(labels[labels >= 0])))
        valid          = labels >= 0
        self.centers_  = _cluster_centers(Xs[valid] if valid.any() else Xs,
                                          labels[valid] if valid.any() else np.zeros(len(Xs), int), k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class AgglomerativeWardClustering(BaseAlgorithm):
    name        = "Agglomerative Ward Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Agglomerative clustering with Ward linkage"

    def fit(self, X, y=None):
        from sklearn.cluster import AgglomerativeClustering
        k              = _nc(y)
        Xs, _          = _subsample(X, y, max_n=300)
        labels         = AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(Xs)
        self.centers_  = _cluster_centers(Xs, labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)








@registry.register
class SpectralClusteringMovement(BaseAlgorithm):
    name        = "Spectral Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Spectral clustering on RBF affinity of movement features"

    def fit(self, X, y=None):
        from sklearn.cluster import SpectralClustering
        k              = _nc(y)
        Xs, _          = _subsample(X, y, max_n=250)
        labels         = SpectralClustering(n_clusters=k, random_state=42,
                                            n_init=5, assign_labels='kmeans').fit_predict(Xs)
        self.centers_  = _cluster_centers(Xs, labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class MeanShiftClustering(BaseAlgorithm):
    name        = "Mean Shift Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Mean shift mode-seeking clustering of movement features"

    def fit(self, X, y=None):
        from sklearn.cluster import MeanShift, estimate_bandwidth
        Xs, _          = _subsample(X, y, max_n=300)
        bw             = estimate_bandwidth(Xs, quantile=0.2, n_samples=min(300, len(Xs)))
        bw             = max(bw, 0.5)
        ms             = MeanShift(bandwidth=bw, n_jobs=1)
        labels         = ms.fit_predict(Xs)
        self.centers_  = ms.cluster_centers_
        self.k_        = len(self.centers_)
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)




@registry.register
class BIRCHClustering(BaseAlgorithm):
    name        = "BIRCH Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "BIRCH incremental clustering using CF-tree of movement features"

    def fit(self, X, y=None):
        from sklearn.cluster import Birch
        # Was Birch.fit() on the FULL, unsubsampled training set -- every
        # sibling clustering algo here subsamples (or uses a fast-enough
        # algorithm); Birch's CF-tree build times out at true scale
        # (~10.7M rows), same bug already fixed for its counterpart in
        # services/s5_segmentation. Birch.predict() only compares against
        # the fitted subcluster centroids, so it stays fast on the full
        # test set regardless.
        k              = _nc(y)
        Xs, _          = _subsample(X, y, max_n=2000)
        self.model_    = Birch(n_clusters=k).fit(Xs)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model_.predict(X)




@registry.register
class GaussianMixtureClustering(BaseAlgorithm):
    name        = "Gaussian Mixture Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "sklearn"
    animals     = ["all"]
    description = "GMM soft clustering of movement features"

    def fit(self, X, y=None):
        from sklearn.mixture import GaussianMixture
        # GaussianMixture's EM fit on the FULL, unsubsampled training set
        # (~10.7M rows) with max_iter=200 -> OOM/hangs at true scale.
        # Subsample like the other super-linear-cost fits in this file.
        k              = _nc(y)
        Xs, _          = _subsample(X, y, max_n=20000)
        self.model_    = GaussianMixture(n_components=k, random_state=42, max_iter=200).fit(Xs)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model_.predict(X)


@registry.register
class FuzzyCMeansClustering(BaseAlgorithm):
    name        = "Fuzzy C-Means"
    service_id  = 2
    category    = "clustering"
    library     = "numpy"
    animals     = ["all"]
    description = "Fuzzy C-Means soft partition of movement features"

    def __init__(self, k=_K, m=2.0, max_iter=100):
        super().__init__(k=k, m=m, max_iter=max_iter)
        self.k        = k
        self.m        = m
        self.max_iter = max_iter

    def fit(self, X, y=None):
        # Was `max_iter` EM iterations, each allocating an (n, k, d) and an
        # (n, k, k) array over the FULL, unsubsampled training set
        # (~10.7M rows) -- several GB per iteration, times up to 100
        # iterations -> OOM at true scale. Unlike its numpy siblings in
        # this file, this one never subsampled. Fix: subsample like the
        # others (exact no-op below max_n).
        k  = _nc(y) if y is not None else self.k
        Xs, _ = _subsample(X, y, max_n=2000)
        n  = len(Xs)
        np.random.seed(42)
        u  = np.random.dirichlet(np.ones(k), n)
        for _ in range(self.max_iter):
            um      = u ** self.m
            centers = (um.T @ Xs) / (um.sum(axis=0)[:, None] + 1e-10)
            dists   = np.sum((Xs[:, None, :] - centers[None, :, :]) ** 2, axis=2) + 1e-10
            exp     = 2.0 / (self.m - 1)
            ratio   = dists[:, :, None] / dists[:, None, :]    # (n, k, k)
            new_u   = 1.0 / ratio.sum(axis=2)
            if np.allclose(new_u, u, atol=1e-4):
                break
            u = new_u
        self.centers_  = centers
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        # Batched: the same (n, k, d)/(n, k, k) broadcast run once on the
        # FULL test set (~2.68M rows at true scale) was also multiple GB.
        # Bounding to fixed-size chunks keeps peak memory independent of n
        # (identical result -- it's the same computation, just chunked).
        batch = 5000
        exp   = 2.0 / (self.m - 1)
        out   = np.empty(len(X), dtype=int)
        for start in range(0, len(X), batch):
            end   = min(start + batch, len(X))
            chunk = X[start:end]
            dists = np.sum((chunk[:, None, :] - self.centers_[None, :, :]) ** 2, axis=2) + 1e-10
            ratio = dists[:, :, None] / dists[:, None, :]
            u     = 1.0 / ratio.sum(axis=2)
            out[start:end] = np.argmax(u, axis=1)
        return out


@registry.register
class KShapeClustering(BaseAlgorithm):
    name        = "K-Shape Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "numpy"
    animals     = ["all"]
    description = "K-Shape cross-correlation clustering of speed_ms subsequences"

    def __init__(self, k=_K, max_iter=30):
        super().__init__(k=k, max_iter=max_iter)
        self.k        = k
        self.max_iter = max_iter

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        # Use z-normalised speed as shape feature; cluster via L2 in feature space
        from sklearn.preprocessing import StandardScaler
        Xz = StandardScaler().fit_transform(X)
        km = _safe_kmeans(Xz, k)
        self.feat_centers_ = _cluster_centers(X, km.labels_, k)
        self.km_z_         = km
        self.scaler_       = StandardScaler().fit(X)
        self.k_            = k
        self.is_fitted     = True
        return self

    def predict(self, X):
        return self.km_z_.predict(self.scaler_.transform(X))


@registry.register
class DTWKMeansClustering(BaseAlgorithm):
    name        = "DTW K-Means Clustering"
    service_id  = 2
    category    = "clustering"
    library     = "numpy"
    animals     = ["all"]
    description = "K-Means with DTW-inspired distance for speed trajectories"

    def __init__(self, k=_K, max_iter=20):
        super().__init__(k=k, max_iter=max_iter)
        self.k        = k
        self.max_iter = max_iter

    def _dtw_dist(self, a, b):
        n, m = len(a), len(b)
        dp   = np.full((n + 1, m + 1), np.inf)
        dp[0, 0] = 0
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost    = (a[i-1] - b[j-1]) ** 2
                dp[i,j] = cost + min(dp[i-1,j], dp[i,j-1], dp[i-1,j-1])
        return dp[n, m]

    def fit(self, X, y=None):
        # Was a nested pure-Python double loop (for i in range(len(s)):
        # for j in range(k):) over the FULL, unsubsampled training set for
        # max_iter=20 iterations -> ~856M Python-level iterations at
        # n~10.7M. Subsample (matching sibling clustering algos here) and
        # vectorize the distance computation (identical formula, just via
        # numpy broadcasting instead of nested loops -- verified exact
        # match against the loop version on randomized small-n trials).
        k  = _nc(y) if y is not None else self.k
        Xs, _ = _subsample(X, y, max_n=300)
        s  = Xs[:, :2]                          # use speed + altitude
        np.random.seed(42)
        centers = s[np.random.choice(len(s), k, replace=False)].copy()
        labels  = np.zeros(len(s), int)
        for _ in range(self.max_iter):
            dists   = np.sum((s[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            labels  = np.argmin(dists, axis=1)
            for j in range(k):
                grp = s[labels == j]
                if len(grp):
                    centers[j] = grp.mean(axis=0)
        self.feat_centers_ = _cluster_centers(Xs, labels, k)
        self.k_            = k
        self.is_fitted     = True
        return self

    def predict(self, X):
        return _nearest(self.feat_centers_, X)














# ============================================================
# MOTIF DISCOVERY (15)
# ============================================================

@registry.register
class MatrixProfileSTAMP(BaseAlgorithm):
    name        = "Matrix Profile STAMP"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "STAMP matrix profile: cluster by subsequence distance profile"

    def __init__(self, window=20, k=_K):
        super().__init__(window=window, k=k)
        self.window = window
        self.k      = k

    def _mp_row(self, s, i, max_candidates=2000):
        # The outer anchor loop in fit() already bounds itself to ~50
        # positions, but each call here did an unbounded O(n) Python loop
        # over EVERY candidate subsequence -> ~50*n inner iterations at
        # true scale. Bound the candidate set per query too (exact
        # no-op below max_candidates -- verified against the unbounded
        # loop on randomized trials).
        w = self.window
        q = s[i:i+w]
        q = (q - q.mean()) / (q.std() + 1e-9)
        n_candidates = len(s) - w + 1
        if n_candidates > max_candidates:
            idx = np.linspace(0, n_candidates - 1, max_candidates).astype(int)
        else:
            idx = np.arange(n_candidates)
        dists = np.empty(len(idx))
        for k, j in enumerate(idx):
            sub = s[j:j+w]
            sub = (sub - sub.mean()) / (sub.std() + 1e-9)
            dists[k] = np.sum((q - sub) ** 2)
        self_pos = np.argmin(np.abs(idx - i))
        dists[self_pos] = np.inf
        return np.min(dists)

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        n  = len(s)
        w  = min(self.window, n // 4)
        mp = np.array([self._mp_row(s, i) for i in range(0, n - w + 1, max(1, (n-w)//50))])
        # Cluster based on profile values
        cuts = np.percentile(mp, np.linspace(0, 100, k + 1)[1:-1])
        self.cuts_ = cuts
        self.k_    = k
        # Store feature centers
        labels = np.digitize(s[:len(mp)], cuts)
        self.centers_ = _cluster_centers(X[:len(mp)], labels % k, k)
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class MatrixProfileSTOMP(BaseAlgorithm):
    name        = "Matrix Profile STOMP"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "STOMP matrix profile: sliding QT for subsequence clustering"

    def __init__(self, window=20, k=_K):
        super().__init__(window=window, k=k)
        self.window = window
        self.k      = k

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        w  = min(self.window, max(3, len(s) // 4))
        n  = len(s)
        # Was `for i in range(len(mp)):` over ALL ~n-w+1 positions (not
        # bounded at all, unlike STAMP's outer anchor loop) -- pure
        # fixed-window (w) rolling stat, so it's exactly vectorizable via
        # sliding_window_view in bounded chunks instead of a Python loop
        # (identical result -- verified exact match against the loop
        # version on randomized trials, and bounds peak memory the same
        # way as the ACF/CTMM fixes in services/s5_segmentation).
        mlen = max(1, n - w + 1)
        mp = np.empty(mlen)
        if n >= w:
            chunk = 200_000
            for start in range(0, mlen, chunk):
                end = min(start + chunk, mlen)
                windows = np.lib.stride_tricks.sliding_window_view(s[start:end + w - 1], w)
                wm  = windows.mean(axis=1, keepdims=True)
                wsd = windows.std(axis=1, keepdims=True) + 1e-9
                norm = (windows - wm) / wsd
                mp[start:end] = norm.std(axis=1)
        cuts = np.percentile(mp, np.linspace(0, 100, k + 1)[1:-1])
        labels = np.digitize(s[:len(mp)], cuts) % k
        self.centers_ = _cluster_centers(X[:len(mp)], labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class FLOSSSegmentation(BaseAlgorithm):
    name        = "FLOSS Segmentation"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "FLOSS arc-curve change-point detection for regime clustering"

    def __init__(self, window=20, k=_K):
        super().__init__(window=window, k=k)
        self.window = window
        self.k      = k

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        w  = min(self.window, max(3, len(s) // 4))
        # Arc curve: rolling local std as regime indicator. Was a Python
        # list comprehension over the WHOLE, unbounded series
        # (~13.39M at true scale) -- same class of bug as
        # ACFSeg/CTMMSeg fixed in services/s5_segmentation. Fixed-window
        # (w), so exactly vectorizable via sliding_window_view in bounded
        # chunks (no approximation -- verified exact match against the
        # loop version, max diff 0.0, on randomized trials).
        n = len(s)
        arc = np.empty(n)
        b = min(w, n)
        for i in range(b):
            arc[i] = s[max(0, i - w):i + 1].std()
        if n > w:
            W = w + 1
            chunk = 200_000
            for start in range(w, n, chunk):
                end = min(start + chunk, n)
                windows = np.lib.stride_tricks.sliding_window_view(s[start - w:end], W)
                arc[start:end] = windows.std(axis=1)
        arc = np.nan_to_num(arc)
        cuts   = np.percentile(arc, np.linspace(0, 100, k + 1)[1:-1])
        labels = np.digitize(arc, cuts) % k
        self.centers_  = _cluster_centers(X, labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class FLUSSSegmentation(BaseAlgorithm):
    name        = "FLUSS Segmentation"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "FLUSS regime change-point detection via arc curve"

    def __init__(self, k=_K, window=30):
        super().__init__(k=k, window=window)
        self.k      = k
        self.window = window

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        w  = min(self.window, max(4, len(s) // 4))
        # Corrected Arc Curve (CAC): proportion of arcs crossing each index.
        # Was a Python for-loop over ~n positions (not bounded at all) --
        # same class of bug as FLOSS above. Fixed window (2w), so exactly
        # vectorizable via sliding_window_view in bounded chunks (verified
        # exact match against the loop version, max diff 0.0).
        n_s = len(s)
        cac = np.zeros(n_s)
        lo, hi = w, n_s - w
        if hi > lo:
            W = 2 * w
            chunk = 200_000
            for start in range(lo, hi, chunk):
                end = min(start + chunk, hi)
                windows = np.lib.stride_tricks.sliding_window_view(s[start - w:end + w - 1], W)
                cac[start:end] = windows.std(axis=1)
        # Find k-1 change points as minima
        from scipy.signal import argrelextrema
        minima = argrelextrema(cac, np.less, order=w//2)[0]
        cp     = np.sort(np.argsort(cac[minima])[:k-1]) if len(minima) >= k-1 else np.linspace(0, len(s)-1, k+1)[1:-1].astype(int)
        cp_abs = minima[cp] if len(minima) >= k-1 else cp
        labels = np.zeros(len(s), int)
        for j, c in enumerate(np.sort(cp_abs)):
            labels[c:] = j + 1
        self.centers_  = _cluster_centers(X, labels % k, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)






@registry.register
class DiscordDetection(BaseAlgorithm):
    name        = "Discord Detection"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "Discord detection: cluster by anomaly score vs motif centres"

    def __init__(self, window=20, k=_K):
        super().__init__(window=window, k=k)
        self.window = window
        self.k      = k

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        n  = len(s)
        w  = min(self.window, max(3, n // 4))
        # Discord score: local deviation from rolling mean (efficient approximation)
        roll_mean = np.convolve(s, np.ones(w) / w, mode='same')
        score     = np.abs(s - roll_mean)
        cuts      = np.percentile(score, np.linspace(0, 100, k + 1)[1:-1])
        labels    = np.digitize(score, cuts) % k
        self.centers_  = _cluster_centers(X, labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)




@registry.register
class SAXMotifDiscovery(BaseAlgorithm):
    name        = "SAX Motif Discovery"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "SAX symbolic discretisation motif discovery on speed_ms"

    def __init__(self, alphabet=4, word_len=8, k=_K):
        super().__init__(alphabet=alphabet, word_len=word_len, k=k)
        self.alphabet  = alphabet
        self.word_len  = word_len
        self.k         = k

    def _sax(self, s, alpha):
        n   = len(s)
        s_z = (s - s.mean()) / (s.std() + 1e-9)
        breaks = np.percentile(s_z, np.linspace(0, 100, alpha + 1)[1:-1])
        return np.digitize(s_z, breaks)

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        s  = X[:, 0].astype(float)
        sym = self._sax(s, self.alphabet)
        # Group by dominant symbol pattern
        wl  = min(self.word_len, len(s) // 4)
        words = {}
        for i in range(len(s) - wl + 1):
            w = tuple(sym[i:i+wl])
            words[w] = words.get(w, [])
            words[w].append(i)
        top_words = sorted(words.items(), key=lambda x: -len(x[1]))[:k]
        centers   = []
        for word, indices in top_words:
            centers.append(X[indices].mean(axis=0))
        while len(centers) < k:
            centers.append(X.mean(axis=0))
        self.centers_  = np.array(centers[:k])
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)










@registry.register
class TurningPointDetectionClustering(BaseAlgorithm):
    name        = "Turning Point Detection"
    service_id  = 2
    category    = "motif_discovery"
    library     = "numpy"
    animals     = ["all"]
    description = "Cluster movement phases using turning-angle change points"

    def __init__(self, k=_K):
        super().__init__(k=k)
        self.k = k

    def fit(self, X, y=None):
        k  = _nc(y) if y is not None else self.k
        ta = X[:, 2].astype(float)          # turning_angle column
        n  = len(ta)
        # Label each point by cumulative turning regime
        cum = np.cumsum(np.abs(ta))
        cuts = np.percentile(cum, np.linspace(0, 100, k + 1)[1:-1])
        labels = np.digitize(cum, cuts) % k
        self.centers_  = _cluster_centers(X, labels, k)
        self.k_        = k
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)




# ============================================================
# DIMENSIONALITY REDUCTION (14)
# ============================================================

@registry.register
class PCATrajectoryCluster(BaseAlgorithm):
    name        = "PCA Trajectory Clustering"
    service_id  = 2
    category    = "dimensionality_reduction"
    library     = "sklearn"
    animals     = ["all"]
    description = "PCA projection followed by K-Means for movement clustering"

    def __init__(self, n_components=2, k=_K):
        super().__init__(n_components=n_components, k=k)
        self.n_components = n_components
        self.k            = k

    def fit(self, X, y=None):
        from sklearn.decomposition import PCA
        k          = _nc(y) if y is not None else self.k
        n          = min(self.n_components, X.shape[1])
        self.pca_  = PCA(n_components=n).fit(X)
        Xp         = self.pca_.transform(X)
        km         = _safe_kmeans(Xp, k)
        self.km_   = km
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.km_.predict(self.pca_.transform(X))


@registry.register
class KernelPCACluster(BaseAlgorithm):
    name        = "Kernel PCA Clustering"
    service_id  = 2
    category    = "dimensionality_reduction"
    library     = "sklearn"
    animals     = ["all"]
    description = "Kernel PCA (RBF) followed by K-Means clustering"

    def __init__(self, n_components=2, k=_K):
        super().__init__(n_components=n_components, k=k)
        self.n_components = n_components
        self.k            = k

    def fit(self, X, y=None):
        # KernelPCA computes a dense n x n kernel (Gram) matrix - at ~62k
        # rows that's a 28.7GB float64 array and MemoryErrors out. Subsample
        # like the other dimensionality-reduction/clustering algos here so
        # both fit and predict (which kernels new points against the fitted
        # training set) stay bounded on large real-world files.
        Xf, yf      = _subsample(X, y, max_n=300)
        from sklearn.decomposition import KernelPCA
        k           = _nc(yf) if yf is not None else self.k
        self.kpca_  = KernelPCA(n_components=self.n_components, kernel='rbf').fit(Xf)
        Xp          = self.kpca_.transform(Xf)
        self.km_    = _safe_kmeans(Xp, k)
        self.is_fitted = True
        return self

    def predict(self, X):
        # kpca_.transform computes a kernel between every query row and the
        # (subsampled, so already small) *training* support points - its
        # cost is fine per-row, but it still scales linearly with how many
        # rows we're predicting. On a large real test set (millions of
        # rows) materialising that whole kernel matrix in one call needs
        # several GB, so predict in bounded batches instead.
        batch = 50_000
        if len(X) <= batch:
            return self.km_.predict(self.kpca_.transform(X))
        out = np.empty(len(X), dtype=int)
        for start in range(0, len(X), batch):
            end = min(start + batch, len(X))
            out[start:end] = self.km_.predict(self.kpca_.transform(X[start:end]))
        return out


@registry.register
class IncrementalPCACluster(BaseAlgorithm):
    name        = "Incremental PCA Clustering"
    service_id  = 2
    category    = "dimensionality_reduction"
    library     = "sklearn"
    animals     = ["all"]
    description = "Incremental PCA for large-scale movement clustering"

    def __init__(self, n_components=2, k=_K):
        super().__init__(n_components=n_components, k=k)
        self.n_components = n_components
        self.k            = k

    def fit(self, X, y=None):
        from sklearn.decomposition import IncrementalPCA
        k           = _nc(y) if y is not None else self.k
        n           = min(self.n_components, X.shape[1])
        self.ipca_  = IncrementalPCA(n_components=n).fit(X)
        Xp          = self.ipca_.transform(X)
        self.km_    = _safe_kmeans(Xp, k)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.km_.predict(self.ipca_.transform(X))




@registry.register
class TruncatedSVDCluster(BaseAlgorithm):
    name        = "Truncated SVD Clustering"
    service_id  = 2
    category    = "dimensionality_reduction"
    library     = "sklearn"
    animals     = ["all"]
    description = "TruncatedSVD (LSA) projection followed by K-Means"

    def __init__(self, n_components=2, k=_K):
        super().__init__(n_components=n_components, k=k)
        self.n_components = n_components
        self.k            = k

    def fit(self, X, y=None):
        from sklearn.decomposition import TruncatedSVD
        k           = _nc(y) if y is not None else self.k
        n           = min(self.n_components, X.shape[1] - 1)
        self.svd_   = TruncatedSVD(n_components=n, random_state=42).fit(X)
        Xp          = self.svd_.transform(X)
        self.km_    = _safe_kmeans(Xp, k)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.km_.predict(self.svd_.transform(X))




















# ============================================================
# SEQUENTIAL PATTERN MINING (18)
# ============================================================

def _seq_fit(X, y, col=0, window=5):
    """Common helper: discretise + find k cluster centers per dominant window pattern."""
    k      = _nc(y)
    sym    = _discretize(X, col=col, n_bins=k)
    wl     = min(window, len(X) // 4)
    wl     = max(wl, 1)
    counts = {}
    for i in range(len(X) - wl + 1):
        pat = tuple(sym[i:i+wl])
        counts[pat] = counts.get(pat, [])
        counts[pat].append(i)
    top = sorted(counts.items(), key=lambda x: -len(x[1]))[:k]
    centers = []
    for _, indices in top:
        centers.append(X[indices].mean(axis=0))
    while len(centers) < k:
        centers.append(X.mean(axis=0))
    return np.array(centers[:k])


@registry.register
class GSPPatternMining(BaseAlgorithm):
    name        = "GSP Pattern Mining"
    service_id  = 2
    category    = "sequential_pattern"
    library     = "numpy"
    animals     = ["all"]
    description = "Generalised Sequential Patterns: cluster by frequent speed sequences"

    def fit(self, X, y=None):
        self.centers_  = _seq_fit(X, y, col=0, window=5)
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


@registry.register
class PrefixSpanMining(BaseAlgorithm):
    name        = "PrefixSpan Mining"
    service_id  = 2
    category    = "sequential_pattern"
    library     = "numpy"
    animals     = ["all"]
    description = "PrefixSpan projected DB mining on discretised movement"

    def fit(self, X, y=None):
        self.centers_  = _seq_fit(X, y, col=0, window=4)
        self.is_fitted = True
        return self

    def predict(self, X):
        return _nearest(self.centers_, X)


































# ============================================================
# DEEP LEARNING — numpy/sklearn approximations (16)
# ============================================================

def _encode(X, hidden=8, seed=42):
    """Simple 2-layer random projection as encoder approximation."""
    np.random.seed(seed)
    d   = X.shape[1]
    W1  = np.random.randn(d, hidden) * 0.1
    h   = np.tanh(X @ W1)
    W2  = np.random.randn(hidden, hidden // 2 + 1) * 0.1
    return np.tanh(h @ W2)
































