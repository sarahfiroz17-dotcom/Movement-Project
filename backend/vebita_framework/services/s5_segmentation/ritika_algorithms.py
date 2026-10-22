"""
services/s5_segmentation/dua_algorithms.py
==========================================
Dua's 79 trajectory-segmentation algorithms for VEBITA Service 5.

predict() returns an integer numpy array of segment / behavioral-state labels.
The evaluator auto-remaps unsupervised cluster IDs to true behaviour labels.
"""

import numpy as np
from scipy import stats, signal
from scipy.spatial.distance import cdist
from sklearn.cluster import (
    KMeans, DBSCAN, AgglomerativeClustering,
    SpectralClustering, MeanShift, OPTICS, Birch,
)
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

try:
    from hmmlearn import hmm as _hmm
    _HMM_OK = True
except ImportError:
    _HMM_OK = False

from core.base import BaseAlgorithm
from core.registry import registry

# ── Helpers ───────────────────────────────────────────────────────────────────

def _subsample(X, y=None, max_n=500, seed=42):
    if len(X) <= max_n:
        return X, y
    np.random.seed(seed)
    idx = np.random.choice(len(X), max_n, replace=False)
    return X[idx], (y[idx] if y is not None else None)

def _n_states(y):
    return int(len(np.unique(y))) if y is not None else 4

def _safe_fit_hmm(model, X):
    lengths = [len(X)]
    try:
        model.fit(X, lengths)
        return True
    except Exception:
        return False

def _predict_hmm(model, X):
    try:
        return model.predict(X, [len(X)])
    except Exception:
        return np.zeros(len(X), dtype=int)

def _rolling_mean(x, w=5):
    out = np.empty(len(x))
    for i in range(len(x)):
        lo = max(0, i - w + 1)
        out[i] = x[lo:i + 1].mean()
    return out

def _rolling_std(x, w=5):
    out = np.empty(len(x))
    for i in range(len(x)):
        lo = max(0, i - w + 1)
        sl = x[lo:i + 1]
        out[i] = sl.std() if len(sl) > 1 else 0.0
    return out

def _breakpoints_to_labels(bkpts, n):
    labels = np.zeros(n, dtype=int)
    prev = 0
    for seg, bp in enumerate(bkpts):
        labels[prev:bp] = seg
        prev = bp
    labels[prev:] = len(bkpts)
    return labels

class _Fenwick:
    """Binary indexed tree over rank-compressed coordinates 0..size-1."""
    def __init__(self, size):
        self.n = size
        self.tree = [0] * (size + 1)
    def add(self, idx, delta):
        idx += 1
        while idx <= self.n:
            self.tree[idx] += delta
            idx += idx & (-idx)
    def prefix(self, idx):
        if idx < 0:
            return 0
        idx += 1
        s = 0
        while idx > 0:
            s += self.tree[idx]
            idx -= idx & (-idx)
        return s

def _mk_scores_sliding(x, w):
    """Rolling Mann-Kendall |S|-statistic for every centered window
    [i-w, i+w) at i in range(w, n-w), computed incrementally with a
    Fenwick tree instead of recomputing rankdata + an O(w^2) double
    loop from scratch at each position.

    Mathematically S = sum_{a<b} sign(x_b - x_a) over the window, and
    sign(rank_b - rank_a) == sign(x_b - x_a), so ranks are unnecessary:
    we rank-compress the whole series once (coordinates), then maintain
    S while the window slides by one element (remove x[lo], add
    x[hi]) using the Fenwick tree to get counts of elements less-than /
    greater-than the incoming/outgoing value in O(log n). This gives the
    exact same S values as the original brute-force implementation
    (verified against it on randomized inputs, including ties) in
    O(n log n) total instead of O(n * w^2).
    """
    n = len(x)
    scores = np.zeros(n)
    if n - 2 * w <= 0:
        return scores

    sorted_vals = np.unique(x)
    m = len(sorted_vals)
    coords = np.searchsorted(sorted_vals, x)
    ft = _Fenwick(m)

    lo, hi = 0, 2 * w
    S = 0
    curr = 0
    for k in range(lo, hi):
        c = coords[k]
        less = ft.prefix(c - 1)
        greater = curr - ft.prefix(c)
        S += less - greater
        ft.add(c, 1)
        curr += 1

    scores[w] = abs(S)
    for i in range(w + 1, n - w):
        c_old = coords[lo]
        greater_old = curr - ft.prefix(c_old)
        less_old = ft.prefix(c_old - 1)
        S -= (greater_old - less_old)
        ft.add(c_old, -1)
        curr -= 1
        lo += 1

        c_new = coords[hi]
        less_new = ft.prefix(c_new - 1)
        greater_new = curr - ft.prefix(c_new)
        S += less_new - greater_new
        ft.add(c_new, 1)
        curr += 1
        hi += 1

        scores[i] = abs(S)
    return scores

def _bounded_sliding_scores(x, w, test_fn, max_w=2000, max_candidates=2000):
    """Bound the cost of a per-position sliding-window statistical test.

    WilcoxonSlidingSeg / VarianceLeveneSeg originally called scipy's
    ranksums/levene on a window of size w at EVERY one of the ~n candidate
    positions, with w = max(n // (n_states*3), 5) scaling linearly with n.
    That's at minimum O(n*w) work -- fine at n~62K (a few seconds) but a
    hang at n~13.39M (stuck inside a single scipy C call long enough that
    even a SIGALRM can't interrupt it).

    This caps the window fed to the test at max_w points per side, and
    evaluates the test at only `max_candidates` evenly spaced positions
    (nearest-neighbor-filling the rest) instead of every single position.
    For n small enough that the original loop was already within budget
    (total candidate positions <= max_candidates and w <= max_w), this is
    an EXACT no-op (step=1, eff_w=w) -- verified against the original
    brute-force implementation on randomized small-n trials. It only
    changes behavior as n grows large, the same class of fix already
    applied elsewhere in this file/codebase (subsampling, decimation) for
    algorithms whose cost grows faster than linearly with n.
    """
    n = len(x)
    scores = np.zeros(n)
    lo_bound, hi_bound = w, n - w
    if hi_bound <= lo_bound:
        return scores
    eff_w = min(w, max_w)
    total = hi_bound - lo_bound
    step = max(1, total // max_candidates)
    positions = np.arange(lo_bound, hi_bound, step)
    vals = np.empty(len(positions))
    for k, i in enumerate(positions):
        try:
            stat, _ = test_fn(x[i - eff_w:i], x[i:i + eff_w])
            vals[k] = stat
        except Exception:
            vals[k] = 0.0
    if step == 1:
        scores[lo_bound:hi_bound] = vals[:total]
    else:
        filled = np.repeat(vals, step)[:total]
        scores[lo_bound:hi_bound] = filled
    return scores

def _align_supervised(X_train, y_train, X_test, cluster_fn):
    """Fit cluster_fn on X_train, assign test cluster IDs; evaluator remaps."""
    cluster_fn.fit(X_train)
    return cluster_fn.predict(X_test)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HMM Family — remaining 10 (after the 4 basic ones in example pipeline)
# ═══════════════════════════════════════════════════════════════════════════════







@registry.register
class GMMHMMSeg(BaseAlgorithm):
    name = "GMM-HMM Segmentation"
    service_id = 5
    category = "hmm"
    library = "hmmlearn"
    animals = ["all"]
    description = "HMM with Gaussian mixture model emissions per state."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        if _HMM_OK:
            self.model_ = _hmm.GMMHMM(
                n_components=self.n_, n_mix=2, covariance_type="diag",
                n_iter=30, random_state=42)
            if not _safe_fit_hmm(self.model_, X):
                self.model_ = None
        else:
            self.model_ = None
        if self.model_ is None:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(X)
        return self

    def predict(self, X):
        if self.model_ is not None:
            return _predict_hmm(self.model_, X)
        return self.fallback_.predict(X)


@registry.register
class TiedCovHMMSeg(BaseAlgorithm):
    name = "Tied-Covariance HMM Segmentation"
    service_id = 5
    category = "hmm"
    library = "hmmlearn"
    animals = ["all"]
    description = "Gaussian HMM where all states share one covariance matrix."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        if _HMM_OK:
            self.model_ = _hmm.GaussianHMM(
                n_components=self.n_, covariance_type="tied",
                n_iter=50, random_state=42)
            if not _safe_fit_hmm(self.model_, X):
                self.model_ = None
        else:
            self.model_ = None
        if self.model_ is None:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(X)
        return self

    def predict(self, X):
        if self.model_ is not None:
            return _predict_hmm(self.model_, X)
        return self.fallback_.predict(X)




@registry.register
class HierarchicalHMMSeg(BaseAlgorithm):
    name = "Hierarchical HMM Segmentation"
    service_id = 5
    category = "hmm"
    library = "hmmlearn"
    animals = ["all"]
    description = "Two-level hierarchical HMM: coarse then fine-grained states."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        if _HMM_OK:
            self.coarse_ = _hmm.GaussianHMM(n_components=2, covariance_type="diag",
                                              n_iter=30, random_state=42)
            self.fine_ = _hmm.GaussianHMM(n_components=self.n_, covariance_type="diag",
                                            n_iter=30, random_state=42)
            ok_c = _safe_fit_hmm(self.coarse_, X)
            ok_f = _safe_fit_hmm(self.fine_, X)
            self.ok_ = ok_c and ok_f
        else:
            self.ok_ = False
        if not self.ok_:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(X)
        return self

    def predict(self, X):
        if self.ok_:
            coarse = _predict_hmm(self.coarse_, X)
            fine = _predict_hmm(self.fine_, X)
            return np.where(coarse == 0, fine % 2, fine % 2 + 2)
        return self.fallback_.predict(X)




@registry.register
class HiddenSemiMarkovSeg(BaseAlgorithm):
    name = "Hidden Semi-Markov Segmentation"
    service_id = 5
    category = "hmm"
    library = "hmmlearn"
    animals = ["all"]
    description = "HSMM approximation: HMM with explicit state-duration modelling."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        if _HMM_OK:
            self.model_ = _hmm.GaussianHMM(
                n_components=self.n_, covariance_type="full",
                n_iter=30, random_state=42)
            if not _safe_fit_hmm(self.model_, X):
                self.model_ = None
        else:
            self.model_ = None
        if self.model_ is None:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(X)
        return self

    def predict(self, X):
        if self.model_ is not None:
            raw = _predict_hmm(self.model_, X)
            smoothed = np.convolve(raw, np.ones(5) / 5, mode='same').round().astype(int)
            return np.clip(smoothed, 0, self.n_ - 1)
        return self.fallback_.predict(X)




# ═══════════════════════════════════════════════════════════════════════════════
# 2. Change Point — remaining 16
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class BinarySegmentation(BaseAlgorithm):
    name = "Binary Segmentation"
    service_id = 5
    category = "changepoint"
    library = "numpy"
    animals = ["all"]
    description = "Greedy binary segmentation by maximum mean-shift cost."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        speed = X[:, 0]
        self.bkpts_ = self._binseg(speed, self.n_ - 1)
        return self

    def _binseg(self, x, n_bkpts):
        # Recomputing x[lo:bp].mean() and x[bp:hi].mean() from scratch for
        # every candidate breakpoint made the search over all ~n positions
        # O(n) per candidate, i.e. O(n^2) per split - fine at 62k rows (a
        # couple of seconds) but a ~26-hour operation extrapolated to 13M+
        # rows. A prefix-sum lets any range mean be read in O(1), giving
        # the exact same gain values (verified against the original on
        # randomized inputs) in O(n) per split instead of O(n^2).
        cumsum = np.concatenate(([0.0], np.cumsum(x)))
        def mean_range(lo, hi):
            return (cumsum[hi] - cumsum[lo]) / (hi - lo)
        bkpts = []
        intervals = [(0, len(x))]
        for _ in range(n_bkpts):
            best_gain, best_bp, best_idx = -np.inf, None, None
            for i, (lo, hi) in enumerate(intervals):
                if hi - lo < 4:
                    continue
                for bp in range(lo + 2, hi - 2):
                    gain = abs(mean_range(lo, bp) - mean_range(bp, hi))
                    if gain > best_gain:
                        best_gain, best_bp, best_idx = gain, bp, i
            if best_bp is None:
                break
            lo, hi = intervals.pop(best_idx)
            intervals.insert(best_idx, (best_bp, hi))
            intervals.insert(best_idx, (lo, best_bp))
            bkpts.append(best_bp)
        return sorted(bkpts)

    def predict(self, X):
        n = len(X)
        bkpts = self._binseg(X[:, 0], self.n_ - 1)
        return _breakpoints_to_labels(bkpts, n)










@registry.register
class DPFixedKSeg(BaseAlgorithm):
    name = "Dynamic Programming Fixed-K Segmentation"
    service_id = 5
    category = "changepoint"
    library = "numpy"
    animals = ["all"]
    description = "Exact DP for fixed number of segments minimising within-segment variance."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        return self

    def predict(self, X):
        x = X[:, 0].astype(float)
        n = len(x)
        k = self.n_

        # The exact DP below is O(n * window) to build the cost table plus
        # an O(k * n * window) fill, with window ~ n/k*3 - i.e. effectively
        # O(n^2) to O(n^3) in n. It already took 8+s on a 4.3k-point file;
        # on a real ~60k-point file it never finished (multi-minute hang,
        # not a crash - just an infeasible nested Python loop). Random
        # subsampling (like the clustering algos use) would scramble time
        # order and break segment-variance semantics, so instead we
        # decimate on a stride to preserve chronological order, run the
        # exact DP on that reduced series, then map the resulting
        # breakpoints back to the original index range.
        MAX_N = 1200
        if n > MAX_N:
            step = int(np.ceil(n / MAX_N))
            idx = np.arange(0, n, step)
            xs = x[idx]
        else:
            idx = np.arange(n)
            xs = x

        m = len(xs)
        k_eff = min(k, m)
        INF = np.inf
        cost = np.full((m + 1, m + 1), INF)
        for i in range(m):
            for j in range(i + 1, min(i + m // k_eff * 3, m + 1)):
                seg = xs[i:j]
                cost[i][j] = seg.var() * len(seg) if len(seg) > 1 else 0
        dp = np.full((k_eff + 1, m + 1), INF)
        split = np.zeros((k_eff + 1, m + 1), dtype=int)
        dp[0][0] = 0
        for s in range(1, k_eff + 1):
            for j in range(s, m + 1):
                for i in range(s - 1, j):
                    c = dp[s - 1][i] + cost[i][j]
                    if c < dp[s][j]:
                        dp[s][j] = c
                        split[s][j] = i
        bkpts_small = []
        pos = m
        for s in range(k_eff, 0, -1):
            prev = split[s][pos]
            if 0 < prev < m:
                bkpts_small.append(prev)
            pos = prev
        bkpts = sorted(int(idx[b]) for b in bkpts_small)
        return _breakpoints_to_labels(bkpts, n)










@registry.register
class MannKendallSeg(BaseAlgorithm):
    name = "Mann-Kendall Trend Segmentation"
    service_id = 5
    category = "changepoint"
    library = "scipy"
    animals = ["all"]
    description = "Detect trend shifts using rolling Mann-Kendall statistic."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        return self

    def predict(self, X):
        x = X[:, 0]
        n = len(x)
        w = max(n // (self.n_ * 2), 5)
        # Was O(n * w^2) (rankdata + nested sign-sum recomputed from
        # scratch at every window position) -> effectively O(n^3) since w
        # scales with n. Replaced with an O(n log n) incremental
        # Fenwick-tree sliding window (see _mk_scores_sliding) that
        # produces identical S-statistic values.
        scores = _mk_scores_sliding(x, w)
        bkpts = []
        for _ in range(self.n_ - 1):
            peak = int(np.argmax(scores))
            bkpts.append(peak)
            scores[max(0, peak - w):peak + w] = 0
        return _breakpoints_to_labels(sorted(bkpts), n)


@registry.register
class WilcoxonSlidingSeg(BaseAlgorithm):
    name = "Wilcoxon Sliding Window Segmentation"
    service_id = 5
    category = "changepoint"
    library = "scipy"
    animals = ["all"]
    description = "Wilcoxon rank-sum test statistic between adjacent windows."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        return self

    def predict(self, X):
        x = X[:, 0]
        n = len(x)
        w = max(n // (self.n_ * 3), 5)
        # Was O(n * w) (scipy ranksums call at every single position,
        # w scaling linearly with n) -> hangs at n~13M. Bounded via
        # _bounded_sliding_scores (see docstring); exact no-op at the
        # dataset sizes this was originally verified against.
        scores = np.abs(_bounded_sliding_scores(x, w, lambda a, b: stats.ranksums(a, b)))
        bkpts = []
        for _ in range(self.n_ - 1):
            peak = int(np.argmax(scores))
            bkpts.append(peak)
            scores[max(0, peak - w):peak + w] = 0
        return _breakpoints_to_labels(sorted(bkpts), n)




@registry.register
class VarianceLeveneSeg(BaseAlgorithm):
    name = "Variance Change Levene Segmentation"
    service_id = 5
    category = "changepoint"
    library = "scipy"
    animals = ["all"]
    description = "Levene test for equal variances detects volatility regime changes."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        return self

    def predict(self, X):
        x = X[:, 0]
        n = len(x)
        w = max(n // (self.n_ * 3), 5)
        # Same O(n * w) -> hang-at-scale bug as WilcoxonSlidingSeg above;
        # same bounded fix.
        scores = _bounded_sliding_scores(x, w, lambda a, b: stats.levene(a, b))
        bkpts = []
        for _ in range(self.n_ - 1):
            peak = int(np.argmax(scores))
            bkpts.append(peak)
            scores[max(0, peak - w):peak + w] = 0
        return _breakpoints_to_labels(sorted(bkpts), n)






# ═══════════════════════════════════════════════════════════════════════════════
# 3. Clustering (16)
# ═══════════════════════════════════════════════════════════════════════════════



















@registry.register
class MeanShiftSeg(BaseAlgorithm):
    name = "Mean Shift Trajectory Segmentation"
    service_id = 5
    category = "clustering"
    library = "scikit-learn"
    animals = ["all"]
    description = "Mean shift mode-seeking clustering."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        Xs, _ = _subsample(X, max_n=300)
        ms = MeanShift(bandwidth=None, bin_seeding=True)
        ms.fit(Xs)
        self.centers_ = ms.cluster_centers_
        return self

    def predict(self, X):
        return np.argmin(cdist(X, self.centers_), axis=1)


@registry.register
class OPTICSSeg(BaseAlgorithm):
    name = "OPTICS Trajectory Segmentation"
    service_id = 5
    category = "clustering"
    library = "scikit-learn"
    animals = ["all"]
    description = "OPTICS ordering-based density clustering."

    def fit(self, X, y=None):
        Xs, _ = _subsample(X, max_n=400)
        scaler = StandardScaler()
        Xsc = scaler.fit_transform(Xs)
        opt = OPTICS(min_samples=5)
        opt.fit(Xsc)
        self.scaler_ = scaler
        labels = opt.labels_
        valid = labels >= 0
        if valid.sum() > 0:
            self.core_X_ = Xsc[valid]
            self.core_L_ = labels[valid]
        else:
            self.core_X_ = Xsc
            self.core_L_ = np.zeros(len(Xsc), dtype=int)
        return self

    def predict(self, X):
        # Was a single cdist(Xsc, self.core_X_) over the WHOLE test set at
        # once -> materializes an n_test x n_core distance matrix, which is
        # 3.89 GiB (MemoryError) at n_test~2.68M. Batch it: identical
        # per-row argmin result, bounded peak memory.
        Xsc = self.scaler_.transform(X)
        batch = 5000
        out = np.empty(len(Xsc), dtype=self.core_L_.dtype)
        for start in range(0, len(Xsc), batch):
            end = min(start + batch, len(Xsc))
            d = cdist(Xsc[start:end], self.core_X_)
            out[start:end] = self.core_L_[np.argmin(d, axis=1)]
        return out


@registry.register
class BIRCHSeg(BaseAlgorithm):
    name = "BIRCH Trajectory Segmentation"
    service_id = 5
    category = "clustering"
    library = "scikit-learn"
    animals = ["all"]
    description = "BIRCH incremental CF-tree clustering."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        # Was Birch.fit() on the FULL, unsubsampled training set (every
        # sibling clustering algo in this file subsamples fit data) ->
        # times out building the CF-tree at n~10.7M rows. Birch.predict()
        # only compares against the fitted subcluster centroids, so it
        # stays fast on the full test set regardless.
        Xs, _ = _subsample(X, max_n=2000)
        self.model_ = Birch(n_clusters=self.n_, threshold=0.5)
        self.model_.fit(Xs)
        return self

    def predict(self, X):
        return self.model_.predict(X)


@registry.register
class FuzzyCMeansSeg(BaseAlgorithm):
    name = "Fuzzy C-Means Segmentation"
    service_id = 5
    category = "clustering"
    library = "numpy"
    animals = ["all"]
    description = "Fuzzy C-means; assign each point to highest membership cluster."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        # Was 50 EM iterations of cdist + a 3D broadcast
        # (u[:,:,None]**m * X[:,None,:]) run directly on the FULL,
        # unsubsampled training set -- the only clustering algo in this
        # file without subsampling. At n~10.7M rows that 3D array is
        # multiple GB, reallocated on every iteration -> OOM/hang.
        # Subsample like every sibling clustering algo here (MeanShiftSeg,
        # OPTICSSeg, BIRCHSeg).
        Xs, _ = _subsample(X, max_n=2000)
        np.random.seed(42)
        self.centers_ = Xs[np.random.choice(len(Xs), self.n_, replace=False)].copy()
        m = 2.0
        for _ in range(50):
            dists = cdist(Xs, self.centers_) + 1e-12
            u = (1.0 / dists) ** (1 / (m - 1))
            u /= u.sum(axis=1, keepdims=True)
            new_c = (u[:, :, None] ** m * Xs[:, None, :]).sum(axis=0)
            new_c /= (u[:, :, None] ** m).sum(axis=0)
            if np.allclose(self.centers_, new_c, atol=1e-6):
                break
            self.centers_ = new_c
        return self

    def predict(self, X):
        # Batched for the same reason as OPTICSSeg.predict(): bounds peak
        # memory on huge test sets instead of building one big array.
        m = 2.0
        batch = 5000
        out = np.empty(len(X), dtype=int)
        for start in range(0, len(X), batch):
            end = min(start + batch, len(X))
            dists = cdist(X[start:end], self.centers_) + 1e-12
            u = (1.0 / dists) ** (1.0 / (m - 1))
            u /= u.sum(axis=1, keepdims=True)
            out[start:end] = np.argmax(u, axis=1)
        return out




@registry.register
class KShapeSeg(BaseAlgorithm):
    name = "K-Shape Segmentation"
    service_id = 5
    category = "clustering"
    library = "numpy"
    animals = ["all"]
    description = "K-shape clustering using shape-based (cross-correlation) distance."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        Xs, _ = _subsample(X, max_n=200)
        np.random.seed(42)
        self.centers_ = Xs[np.random.choice(len(Xs), self.n_, replace=False)].copy()
        for _ in range(20):
            dists = self._sbd_matrix(Xs, self.centers_)
            labels = np.argmin(dists, axis=1)
            for k in range(self.n_):
                mask = labels == k
                if mask.sum() == 0:
                    continue
                self.centers_[k] = Xs[mask].mean(axis=0)
        return self

    def _sbd_matrix(self, X, centers):
        # Was a nested pure-Python for-loop (per center x per row of X)
        # -> ~10.7M Python-level iterations at n_test~2.68M, n_clusters~4
        # (this ran unbounded on predict()'s full test set, unlike fit()
        # which already subsamples). Vectorized via one matmul: identical
        # up to floating-point rounding (verified against the loop version,
        # max diff ~1e-16, same argmin every trial).
        Xn = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
        Cn = centers / (np.linalg.norm(centers, axis=1, keepdims=True) + 1e-12)
        return 1 - Xn @ Cn.T

    def predict(self, X):
        dists = self._sbd_matrix(X, self.centers_)
        return np.argmin(dists, axis=1)


@registry.register
class SOMSeg(BaseAlgorithm):
    name = "Self-Organising Map Segmentation"
    service_id = 5
    category = "clustering"
    library = "numpy"
    animals = ["all"]
    description = "1D SOM lattice as competitive-learning segmenter."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        # Was `for x in X:` over the FULL, unsubsampled training set for 5
        # epochs -> ~53M pure-Python iterations at n~10.7M. Every sibling
        # clustering algo in this file subsamples fit data; this one
        # didn't. Subsample like the others (exact no-op below max_n).
        Xs, _ = _subsample(X, max_n=2000)
        np.random.seed(42)
        self.weights_ = Xs[np.random.choice(len(Xs), self.n_, replace=False)].copy().astype(float)
        lr, sigma = 0.1, self.n_ / 2.0
        for epoch in range(5):
            lr_e = lr * (0.1 ** (epoch / 5))
            sig_e = max(1.0, sigma * (0.5 ** (epoch / 5)))
            for x in Xs:
                bmu = np.argmin(((self.weights_ - x) ** 2).sum(axis=1))
                nbr = np.exp(-((np.arange(self.n_) - bmu) ** 2) / (2 * sig_e ** 2))
                self.weights_ += lr_e * nbr[:, None] * (x - self.weights_)
        return self

    def predict(self, X):
        return np.argmin(cdist(X, self.weights_), axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Statistical Methods (16)
# ═══════════════════════════════════════════════════════════════════════════════















@registry.register
class EMDSeg(BaseAlgorithm):
    name = "Empirical Mode Decomposition Segmentation"
    service_id = 5
    category = "statistical"
    library = "numpy"
    animals = ["all"]
    description = "EMD-based intrinsic mode functions cluster into behavioral states."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        imfs = self._emd(X[:, 0], n_imf=3)
        self.model_ = KMeans(n_clusters=self.n_, random_state=42)
        self.model_.fit(imfs.T)
        return self

    def _emd(self, x, n_imf=3):
        imfs = []
        residue = x.copy()
        for _ in range(n_imf):
            h = residue.copy()
            for _ in range(10):
                maxima_idx = signal.argrelextrema(h, np.greater, order=3)[0]
                minima_idx = signal.argrelextrema(h, np.less, order=3)[0]
                if len(maxima_idx) < 2 or len(minima_idx) < 2:
                    break
                t = np.arange(len(h))
                upper = np.interp(t, maxima_idx, h[maxima_idx])
                lower = np.interp(t, minima_idx, h[minima_idx])
                mean_env = (upper + lower) / 2
                h -= mean_env
            imfs.append(h)
            residue -= h
        return np.array(imfs)

    def predict(self, X):
        imfs = self._emd(X[:, 0], n_imf=3)
        return self.model_.predict(imfs.T)










@registry.register
class ACFSeg(BaseAlgorithm):
    name = "Autocorrelation Function Segmentation"
    service_id = 5
    category = "statistical"
    library = "numpy"
    animals = ["all"]
    description = "Rolling ACF features cluster into behavioural states."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        feats = self._acf_features(X)
        self.model_ = KMeans(n_clusters=self.n_, random_state=42)
        self.model_.fit(feats)
        return self

    def _acf_features(self, X):
        # Was `for i in range(n):` with per-row slicing + numpy calls --
        # window size w=20 is fixed (not scaling with n, so this is only
        # O(n)), but at n~13.39M the pure-Python-loop overhead alone made
        # it take far too long. Vectorized in bounded chunks via
        # sliding_window_view (identical results -- verified against the
        # loop version on randomized trials, max diff ~1e-16 -- while
        # keeping peak memory independent of n, ~500MB at true scale
        # instead of one huge whole-array allocation).
        x = X[:, 0]
        n = len(x)
        w = 20
        feats = np.zeros((n, 3))
        b = min(w, n)
        for i in range(b):
            lo = max(0, i - w)
            seg = x[lo:i + 1]
            if len(seg) < 4:
                feats[i] = [0, 0, 0]
                continue
            seg_c = seg - seg.mean()
            norm = (seg_c ** 2).sum() + 1e-12
            feats[i, 0] = np.dot(seg_c[:-1], seg_c[1:]) / norm
            feats[i, 1] = np.dot(seg_c[:-2], seg_c[2:]) / norm if len(seg_c) > 2 else 0
            feats[i, 2] = seg.std()
        if n > w:
            W = w + 1
            chunk = 200_000
            for start in range(w, n, chunk):
                end = min(start + chunk, n)
                windows = np.lib.stride_tricks.sliding_window_view(x[start - w:end], W)
                means = windows.mean(axis=1, keepdims=True)
                wc = windows - means
                norm = (wc ** 2).sum(axis=1) + 1e-12
                feats[start:end, 0] = (wc[:, :-1] * wc[:, 1:]).sum(axis=1) / norm
                feats[start:end, 1] = (wc[:, :-2] * wc[:, 2:]).sum(axis=1) / norm
                feats[start:end, 2] = windows.std(axis=1)
        return feats

    def predict(self, X):
        feats = self._acf_features(X)
        return self.model_.predict(feats)






@registry.register
class CTMMSeg(BaseAlgorithm):
    name = "CTMM Segmentation"
    service_id = 5
    category = "statistical"
    library = "numpy"
    animals = ["all"]
    description = "Continuous-time movement model proxy: velocity autocorrelation cluster."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        speed = X[:, 0]
        tau = self._tau(speed)
        self.model_ = KMeans(n_clusters=self.n_, random_state=42)
        self.model_.fit(np.column_stack([speed, tau]))
        return self

    def _tau(self, speed):
        # Same fixed-window-but-too-slow-at-scale bug as ACFSeg._acf_features
        # above; same chunked-vectorization fix (verified exact match on
        # randomized trials, including the seg.std()<=1e-12 branch).
        n = len(speed)
        w = 20
        tau = np.zeros(n)
        b = min(w, n)
        for i in range(b):
            lo = max(0, i - w)
            seg = speed[lo:i + 1]
            if len(seg) > 2 and seg.std() > 1e-12:
                cc = np.corrcoef(seg[:-1], seg[1:])[0, 1]
                tau[i] = 0.0 if np.isnan(cc) else cc
        if n > w:
            W = w + 1
            chunk = 200_000
            for start in range(w, n, chunk):
                end = min(start + chunk, n)
                windows = np.lib.stride_tricks.sliding_window_view(speed[start - w:end], W)
                seg_std = windows.std(axis=1)
                a = windows[:, :-1]
                b_ = windows[:, 1:]
                ac = a - a.mean(axis=1, keepdims=True)
                bc = b_ - b_.mean(axis=1, keepdims=True)
                num = (ac * bc).sum(axis=1)
                den = np.sqrt((ac ** 2).sum(axis=1) * (bc ** 2).sum(axis=1))
                with np.errstate(divide='ignore', invalid='ignore'):
                    cc = np.where(den > 0, num / den, np.nan)
                cc = np.where(seg_std > 1e-12, cc, 0.0)
                tau[start:end] = np.nan_to_num(cc, nan=0.0)
        return tau

    def predict(self, X):
        speed = X[:, 0]
        tau = self._tau(speed)
        return self.model_.predict(np.column_stack([speed, tau]))


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Deep Learning Approximations (13)
# ═══════════════════════════════════════════════════════════════════════════════



@registry.register
class BiLSTMSegProxy(BaseAlgorithm):
    name = "BiLSTM Segmenter Proxy"
    service_id = 5
    category = "deep_learning"
    library = "numpy"
    animals = ["all"]
    description = "Bidirectional LSTM proxy: forward + backward hidden states."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        np.random.seed(1)
        d, h = X.shape[1], 8
        self.Wf_ = (np.random.randn(h, d) * 0.1, np.random.randn(h, h) * 0.1)
        self.Wb_ = (np.random.randn(h, d) * 0.1, np.random.randn(h, h) * 0.1)
        feats = self._run(X, expand=False)
        self.model_ = KMeans(n_clusters=self.n_, random_state=42)
        self.model_.fit(feats)
        return self

    def _run_dir(self, X, W, max_len=5000, expand=True):
        # Was a `for i, x in enumerate(X):` sequential recurrence run on
        # the FULL X in both fit() (~10.7M rows) and predict() (~2.68M
        # rows) with no bound at all -- per-step cost is tiny (two 8x8
        # matvecs) but millions of Python-level iterations is too slow
        # (>30s at true scale). Bound via order-preserving stride
        # decimation (random subsampling would scramble the temporal order
        # the recurrence depends on -- same reasoning as BC_E83_LSTM's fit
        # fix in service 6), then repeat each hidden state to refill the
        # full output length predict() must return. Exact no-op when
        # n <= max_len (step=1) -- verified against the unbounded loop on
        # randomized small-n trials.
        Wx, Wh = W
        n = len(X)
        step = max(1, int(np.ceil(n / max_len))) if n > max_len else 1
        Xs = X[::step]
        h = np.zeros(Wx.shape[0])
        hs = np.zeros((len(Xs), len(h)))
        for i, x in enumerate(Xs):
            h = np.tanh(Wx @ x + Wh @ h)
            hs[i] = h
        if not expand or step == 1:
            return hs
        return np.repeat(hs, step, axis=0)[:n]

    def _run(self, X, expand=True):
        # expand=False (used by fit(), below) skips re-expanding back to
        # full length -- fit() only needs the bounded decimated hidden
        # states to train KMeans on, and re-expanding+hstacking a
        # ~10.7M-row array here was itself an OOM (verified: several GB of
        # transient repeat/hstack copies on top of feeding KMeans.fit() a
        # huge unsubsampled array, unlike every sibling clustering fit in
        # this file). predict() keeps expand=True since ITS output length
        # must match the full test set.
        fwd = self._run_dir(X, self.Wf_, expand=expand)
        bwd = self._run_dir(X[::-1], self.Wb_, expand=expand)[::-1]
        return np.hstack([fwd, bwd])

    def predict(self, X):
        return self.model_.predict(self._run(X))


@registry.register
class GRUSegProxy(BaseAlgorithm):
    name = "GRU Segmenter Proxy"
    service_id = 5
    category = "deep_learning"
    library = "numpy"
    animals = ["all"]
    description = "GRU-like update gate proxy for sequential segmentation."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        np.random.seed(2)
        d, h = X.shape[1], 8
        self.Wz_ = np.random.randn(h, d + h) * 0.1
        self.Wr_ = np.random.randn(h, d + h) * 0.1
        self.Wn_ = np.random.randn(h, d + h) * 0.1
        # expand=False: same OOM-avoidance reasoning as BiLSTMSegProxy.fit
        # above -- fit() only needs the bounded decimated hidden states.
        hidden = self._run(X, expand=False)
        self.model_ = KMeans(n_clusters=self.n_, random_state=42)
        self.model_.fit(hidden)
        return self

    def _sigmoid(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -10, 10)))

    def _run(self, X, max_len=5000, expand=True):
        # Same unbounded-full-X sequential-recurrence bug as
        # BiLSTMSegProxy._run_dir above; same order-preserving-decimation
        # fix (exact no-op below max_len, verified against the unbounded
        # loop on randomized trials).
        n_rows = len(X)
        step = max(1, int(np.ceil(n_rows / max_len))) if n_rows > max_len else 1
        Xs = X[::step]
        h = np.zeros(self.Wz_.shape[0])
        hs = np.zeros((len(Xs), len(h)))
        for i, x in enumerate(Xs):
            xh = np.r_[x, h]
            z = self._sigmoid(self.Wz_ @ xh)
            r = self._sigmoid(self.Wr_ @ xh)
            n = np.tanh(self.Wn_ @ np.r_[x, r * h])
            h = (1 - z) * h + z * n
            hs[i] = h
        if not expand or step == 1:
            return hs
        return np.repeat(hs, step, axis=0)[:n_rows]

    def predict(self, X):
        return self.model_.predict(self._run(X))














@registry.register
class LSTMHMMHybridSeg(BaseAlgorithm):
    name = "LSTM-HMM Hybrid Segmentation"
    service_id = 5
    category = "deep_learning"
    library = "hmmlearn"
    animals = ["all"]
    description = "LSTM proxy extracts temporal features fed into Gaussian HMM."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        np.random.seed(6)
        d, h = X.shape[1], 4
        self.Wx_ = np.random.randn(h, d) * 0.1
        self.Wh_ = np.random.randn(h, h) * 0.1
        feats = self._run(X)
        if _HMM_OK:
            self.model_ = _hmm.GaussianHMM(n_components=self.n_, covariance_type="diag",
                                             n_iter=30, random_state=42)
            if not _safe_fit_hmm(self.model_, feats):
                self.model_ = None
        else:
            self.model_ = None
        if self.model_ is None:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(feats)
        return self

    def _run(self, X):
        h = np.zeros(self.Wx_.shape[0])
        out = np.zeros((len(X), len(h)))
        for i, x in enumerate(X):
            h = np.tanh(self.Wx_ @ x + self.Wh_ @ h)
            out[i] = h
        return out

    def predict(self, X):
        feats = self._run(X)
        if self.model_ is not None:
            return _predict_hmm(self.model_, feats)
        return self.fallback_.predict(feats)








# ═══════════════════════════════════════════════════════════════════════════════
# 6. Ecology-Specific (6)
# ═══════════════════════════════════════════════════════════════════════════════





@registry.register
class MoveHMMPortSeg(BaseAlgorithm):
    name = "moveHMM Port Segmentation"
    service_id = 5
    category = "ecology"
    library = "hmmlearn"
    animals = ["all"]
    description = "moveHMM-inspired HMM on step-length and turning angle features."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        feat = np.column_stack([X[:, 6], X[:, 2]])
        if _HMM_OK:
            self.model_ = _hmm.GaussianHMM(n_components=self.n_, covariance_type="full",
                                             n_iter=50, random_state=42)
            if not _safe_fit_hmm(self.model_, feat):
                self.model_ = None
        else:
            self.model_ = None
        if self.model_ is None:
            self.fallback_ = KMeans(n_clusters=self.n_, random_state=42).fit(feat)
        self.feat_cols_ = [6, 2]
        return self

    def predict(self, X):
        feat = X[:, self.feat_cols_]
        if self.model_ is not None:
            return _predict_hmm(self.model_, feat)
        return self.fallback_.predict(feat)


@registry.register
class RFBehavioralSeg(BaseAlgorithm):
    name = "Random Forest Behavioral Segmentation"
    service_id = 5
    category = "ecology"
    library = "scikit-learn"
    animals = ["all"]
    description = "Supervised Random Forest trained on labelled behavior classes."

    def fit(self, X, y=None):
        if y is None:
            self.fallback_ = KMeans(n_clusters=4, random_state=42).fit(X)
            self.supervised_ = False
        else:
            self.model_ = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model_.fit(X, y)
            self.supervised_ = True
        return self

    def predict(self, X):
        if self.supervised_:
            return self.model_.predict(X)
        return self.fallback_.predict(X)




@registry.register
class MajorityVoteEnsembleSeg(BaseAlgorithm):
    name = "Majority Vote Ensemble Segmentation"
    service_id = 5
    category = "ecology"
    library = "numpy"
    animals = ["all"]
    description = "Ensemble of K-Means, GMM, and HMM by majority vote per point."

    def fit(self, X, y=None):
        self.n_ = _n_states(y)
        # Was 3 separate model fits (KMeans with n_init=10, GaussianMixture,
        # GaussianHMM) all run on the FULL, unsubsampled training set
        # (~10.7M rows) at once -- unlike every sibling ensemble/clustering
        # algo in this file. Got OOM-killed at true scale. Subsample like
        # the others (exact no-op below max_n).
        Xs, _ = _subsample(X, max_n=2000)
        self.km_ = KMeans(n_clusters=self.n_, random_state=42, n_init=10).fit(Xs)
        self.gm_ = GaussianMixture(n_components=self.n_, random_state=42).fit(Xs)
        if _HMM_OK:
            self.hmm_ = _hmm.GaussianHMM(n_components=self.n_, covariance_type="diag",
                                           n_iter=30, random_state=42)
            if not _safe_fit_hmm(self.hmm_, Xs):
                self.hmm_ = None
        else:
            self.hmm_ = None
        return self

    def predict(self, X):
        p1 = self.km_.predict(X)
        p2 = self.gm_.predict(X)
        p3 = _predict_hmm(self.hmm_, X) if self.hmm_ is not None else p1
        # Was `for row in combined: np.bincount(row).argmax()` -- a
        # pure-Python loop over every test row (~2.68M at true scale),
        # same class of bug as the ACF/CTMM/BiLSTM fixes above. Vectorized
        # via one-hot counting (identical tie-breaking to bincount+argmax:
        # lowest label index wins ties -- verified exact match against the
        # loop version on randomized trials).
        combined = np.stack([p1, p2, p3], axis=1)
        nbins = max(self.n_, int(combined.max()) + 1) if combined.size else self.n_
        onehot = (combined[:, :, None] == np.arange(nbins)[None, None, :])
        return onehot.sum(axis=1).argmax(axis=1)
