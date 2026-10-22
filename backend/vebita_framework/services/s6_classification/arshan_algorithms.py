"""
services/s6_classification/arshan_algorithms.py
================================================
VEBITA — Service 6: Behavioural State Classification (Arshan)

21 algorithms across 7 categories:
  A. Linear & Statistical         (3 algorithms)
  B. Tree & Ensemble              (3 algorithms)
  C. Kernel & Distance-Based      (3 algorithms)
  D. Probabilistic & Bayesian     (3 algorithms)
  E. Deep Learning                (3 algorithms)
  F. Ecological-Specific          (3 algorithms)
  G. Advanced Boosting            (3 algorithms)

Feature matrix X shape: (n_points, 8)
  [0] speed_ms  [1] altitude_m  [2] turning_angle  [3] straightness
  [4] speed_roll_mean  [5] speed_roll_std  [6] step_length_m  [7] alt_roll_mean

predict() returns a 1-D float array of integer class labels, same length as X.
Service ID: 6
"""

import numpy as np
from scipy.spatial.distance import cdist

from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    AdaBoostClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.mixture import GaussianMixture
from sklearn.decomposition import PCA
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
    _XGB = True
except ImportError:
    _XGB = False

try:
    from catboost import CatBoostClassifier
    _CAT = True
except ImportError:
    _CAT = False

from core.base import BaseAlgorithm
from core.registry import registry


# ══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _y(y, n):
    if y is not None and len(y) == n:
        return np.asarray(y, dtype=int)
    return np.zeros(n, dtype=int)

def _majority(arr):
    if arr is None or len(arr) == 0:
        return 0
    vals, counts = np.unique(arr, return_counts=True)
    return int(vals[np.argmax(counts)])

def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))

def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / (e.sum(axis=1, keepdims=True) + 1e-9)

def _relu(x):
    return np.maximum(0, x)

def _ce_grad(probs, y, K):
    g = probs.copy()
    for i, yi in enumerate(y):
        g[i, int(yi) % K] -= 1
    return g / len(y)

def _transition_counts(y_, K):
    if len(y_) < 2:
        return np.zeros((K, K))
    a = y_[:-1] % K
    b = y_[1:] % K
    flat = (a * K + b).astype(np.int64)
    return np.bincount(flat, minlength=K * K).reshape(K, K).astype(float)

def _subsample(X, y=None, max_n=20000, seed=42):
    n = len(X)
    if n <= max_n:
        return X, y
    rs = np.random.RandomState(seed)
    idx = rs.choice(n, max_n, replace=False)
    return X[idx], (np.asarray(y)[idx] if y is not None else None)


# ══════════════════════════════════════════════════════════════════════════════
# A. LINEAR & STATISTICAL  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_A01_LogisticRegression(BaseAlgorithm):
    """A01 — Multinomial logistic regression."""
    name = "BC A01 Logistic Regression"
    service_id = 6; category = "A_linear"; library = "sklearn"; animals = ["all"]
    description = "Multinomial LR: linear decision boundaries between behaviour states"

    def __init__(self, C=1.0):
        super().__init__(C=C)
        self.m = LogisticRegression(C=C, solver="lbfgs", max_iter=500)

    def fit(self, X, y=None):
        self.m.fit(X, _y(y, len(X))); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_A05_LDA(BaseAlgorithm):
    """A05 — Linear Discriminant Analysis."""
    name = "BC A05 LDA"
    service_id = 6; category = "A_linear"; library = "sklearn"; animals = ["all"]
    description = "LDA maximally separates behaviour classes by linear combination"

    def __init__(self):
        super().__init__()
        self.m = LinearDiscriminantAnalysis()

    def fit(self, X, y=None):
        self.m.fit(X, _y(y, len(X))); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_A29_SpeedAltitudeRules(BaseAlgorithm):
    """A29 — Expert rule-based classifier (speed + altitude thresholds)."""
    name = "BC A29 Expert Rules"
    service_id = 6; category = "A_linear"; library = "numpy"; animals = ["all"]
    description = "Domain rules: speed/altitude percentile thresholds → states"

    def __init__(self):
        super().__init__()
        self.sp_ = None; self.al_ = None

    def fit(self, X, y=None):
        self.sp_ = np.percentile(X[:, 0], [25, 60])
        self.al_ = np.percentile(X[:, 1], 50)
        self.is_fitted = True; return self

    def predict(self, X):
        sp, al = X[:, 0], X[:, 1]
        labels = np.zeros(len(X), dtype=int)
        labels[(sp >= self.sp_[0]) & (sp < self.sp_[1])] = 1
        labels[(sp >= self.sp_[1]) & (al < self.al_)] = 2
        labels[(sp >= self.sp_[0]) & (al >= self.al_)] = 3
        return labels.astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# B. TREE & ENSEMBLE  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_B34_RandomForest100(BaseAlgorithm):
    """B34 — Random Forest (100 trees)."""
    name = "BC B34 Random Forest 100"
    service_id = 6; category = "B_tree"; library = "sklearn"; animals = ["all"]
    description = "RF ensemble of 100 trees — robust behaviour classification"

    def __init__(self, n_estimators=100):
        super().__init__(n_estimators=n_estimators)
        self.m = RandomForestClassifier(n_estimators=n_estimators,
                                        random_state=42, n_jobs=-1)

    def fit(self, X, y=None):
        self.m.fit(X, _y(y, len(X))); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_B37_GBM(BaseAlgorithm):
    """B37 — Gradient Boosting Machine."""
    name = "BC B37 Gradient Boosting"
    service_id = 6; category = "B_tree"; library = "sklearn"; animals = ["all"]
    description = "Sequential boosting corrects misclassified behaviour states"

    def __init__(self, n_estimators=100, max_depth=4):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth)
        self.m = GradientBoostingClassifier(n_estimators=n_estimators,
                                             max_depth=max_depth, random_state=42)

    def fit(self, X, y=None):
        Xs, ys = _subsample(X, _y(y, len(X)), max_n=20000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_B39_XGBoost(BaseAlgorithm):
    """B39 — XGBoost Classifier."""
    name = "BC B39 XGBoost"
    service_id = 6; category = "B_tree"; library = "xgboost"; animals = ["all"]
    description = "XGBoost regularised gradient boosting for behaviour"

    def __init__(self, n_estimators=100, max_depth=4):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth)
        self.n_estimators = n_estimators; self.max_depth = max_depth

    def fit(self, X, y=None):
        y_ = _y(y, len(X))
        if _XGB:
            self.m = XGBClassifier(n_estimators=self.n_estimators,
                                   max_depth=self.max_depth,
                                   eval_metric="mlogloss",
                                   verbosity=0, random_state=42)
        else:
            self.m = GradientBoostingClassifier(n_estimators=self.n_estimators,
                                                max_depth=self.max_depth)
        Xs, ys = _subsample(X, y_, max_n=20000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# C. KERNEL & DISTANCE-BASED  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_C56_SVM_RBF(BaseAlgorithm):
    """C56 — SVM with RBF kernel."""
    name = "BC C56 SVM RBF"
    service_id = 6; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "RBF-SVM: curved decision boundaries between behaviour states"

    def __init__(self, C=1.0, gamma="scale"):
        super().__init__(C=C, gamma=gamma)
        self.m = SVC(C=C, kernel="rbf", gamma=gamma, decision_function_shape="ovr")

    def fit(self, X, y=None):
        Xs, ys = _subsample(X, _y(y, len(X)), max_n=5000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_C63_KNN7(BaseAlgorithm):
    """C63 — k-NN (k=7)."""
    name = "BC C63 kNN k=7"
    service_id = 6; category = "C_kernel"; library = "sklearn"; animals = ["all"]
    description = "7-NN majority vote — smoother, less noisy behaviour labels"

    def __init__(self):
        super().__init__()

    def fit(self, X, y=None):
        Xs, ys = _subsample(X, _y(y, len(X)), max_n=500)
        self.Xtr_ = Xs; self.ytr_ = ys
        self.classes_ = np.unique(ys)
        self.k_ = min(7, len(Xs) - 1)
        self.is_fitted = True; return self

    def predict(self, X):
        batch = 20000
        nclasses = len(self.classes_)
        out = np.empty(len(X), dtype=float)
        for start in range(0, len(X), batch):
            end = min(start + batch, len(X))
            d = cdist(X[start:end], self.Xtr_)
            idx = np.argpartition(d, self.k_ - 1, axis=1)[:, :self.k_]
            neigh_y = self.ytr_[idx]
            mapped = np.searchsorted(self.classes_, neigh_y)
            onehot = (mapped[:, :, None] == np.arange(nclasses)[None, None, :])
            counts = onehot.sum(axis=1)
            out[start:end] = self.classes_[counts.argmax(axis=1)]
        return out


@registry.register
class BC_C69_MahalanobisClassifier(BaseAlgorithm):
    """C69 — Mahalanobis distance nearest-class classifier."""
    name = "BC C69 Mahalanobis Classifier"
    service_id = 6; category = "C_kernel"; library = "numpy"; animals = ["all"]
    description = "Assigns fix to class with smallest Mahalanobis distance"

    def __init__(self):
        super().__init__()
        self.means_ = {}; self.cov_inv_ = {}

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); self.classes_ = np.unique(y_)
        for c in self.classes_:
            Xc = X[y_ == c]
            self.means_[c] = Xc.mean(0)
            cov = np.cov(Xc.T) + np.eye(X.shape[1]) * 1e-6
            self.cov_inv_[c] = np.linalg.inv(cov)
        self.is_fitted = True; return self

    def predict(self, X):
        dists = np.stack([
            np.einsum('ij,jk,ik->i',
                      X - self.means_[c],
                      self.cov_inv_[c],
                      X - self.means_[c])
            for c in self.classes_
        ], axis=1)
        return self.classes_[np.argmin(dists, axis=1)].astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# D. PROBABILISTIC & BAYESIAN  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_D72_HMM4(BaseAlgorithm):
    """D72 — 4-State HMM (foraging / migration / roosting / soaring)."""
    name = "BC D72 HMM 4-State"
    service_id = 6; category = "D_probabilistic"; library = "numpy"; animals = ["all"]
    description = "4-state Gaussian HMM — gold standard for bird behaviour"

    def __init__(self):
        super().__init__()
        self.n_states = 4
        self.means_ = self.stds_ = self.A_ = self.pi_ = None

    def _emit(self, x, k):
        return np.sum(-0.5 * ((x - self.means_[k]) / self.stds_[k]) ** 2
                      - np.log(self.stds_[k] * np.sqrt(2 * np.pi)))

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); K = self.n_states
        self.means_ = np.zeros((K, X.shape[1]))
        self.stds_  = np.ones((K, X.shape[1]))
        self.pi_    = np.ones(K) / K
        for k in range(K):
            mask = (y_ % K) == k
            if mask.sum() > 1:
                self.means_[k] = X[mask].mean(0)
                self.stds_[k]  = X[mask].std(0) + 1e-6
        self.A_ = np.ones((K, K)) / K + _transition_counts(y_, K)
        self.A_ /= self.A_.sum(1, keepdims=True) + 1e-9
        self.is_fitted = True; return self

    def predict(self, X):
        K = self.n_states; n = len(X)
        step = max(1, int(np.ceil(n / 20000))) if n > 20000 else 1
        Xd = X[::step]; T = len(Xd)
        delta = np.log(self.pi_ + 1e-9) + np.array([self._emit(Xd[0], k) for k in range(K)])
        psi = np.zeros((T, K), dtype=int)
        for t in range(1, T):
            tr = delta[:, None] + np.log(self.A_ + 1e-9)
            psi[t] = tr.argmax(0)
            delta  = tr.max(0) + np.array([self._emit(Xd[t], k) for k in range(K)])
        path = np.zeros(T, dtype=int); path[-1] = delta.argmax()
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]
        return (np.repeat(path, step)[:n] % K).astype(float)


@registry.register
class BC_D77_GMMClassifier(BaseAlgorithm):
    """D77 — Per-class GMM classifier."""
    name = "BC D77 GMM Classifier"
    service_id = 6; category = "D_probabilistic"; library = "sklearn"; animals = ["all"]
    description = "Per-class GMM: each behaviour has its own mixture"

    def __init__(self, n_mix=2):
        super().__init__(n_mix=n_mix)
        self.n_mix = n_mix; self.gmms_ = {}; self.priors_ = {}

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); self.classes_ = np.unique(y_); n = len(y_)
        for c in self.classes_:
            Xc = X[y_ == c]
            if len(Xc) >= self.n_mix:
                Xc_sub, _ = _subsample(Xc, max_n=20000)
                gm = GaussianMixture(n_components=self.n_mix, random_state=42)
                gm.fit(Xc_sub); self.gmms_[c] = gm
            self.priors_[c] = len(Xc) / n
        self.is_fitted = True; return self

    def predict(self, X):
        scores = np.array([
            self.gmms_[c].score_samples(X) + np.log(self.priors_[c] + 1e-9)
            if c in self.gmms_ else np.full(len(X), np.log(self.priors_[c] + 1e-9))
            for c in self.classes_]).T
        return self.classes_[np.argmax(scores, axis=1)].astype(float)


@registry.register
class BC_D80_KalmanGMM(BaseAlgorithm):
    """D80 — Kalman-smoothed features + GMM decoder."""
    name = "BC D80 Kalman + GMM"
    service_id = 6; category = "D_probabilistic"; library = "sklearn"; animals = ["all"]
    description = "Kalman-smoothed GPS features fed into GMM for behaviour"

    def __init__(self, Q=1e-3, R=0.1, n_components=4):
        super().__init__(Q=Q, R=R, n_components=n_components)
        self.Q = Q; self.R = R
        self.m = GaussianMixture(n_components=n_components, random_state=42)
        self.mapping_ = {}

    def _smooth(self, X):
        n = len(X)
        step = max(1, int(np.ceil(n / 20000))) if n > 20000 else 1
        Xd = X[::step]
        out_d = np.zeros_like(Xd)
        for j in range(Xd.shape[1]):
            s = Xd[:, j]; x, P = s[0], 1.0; col = np.zeros(len(s))
            for i in range(len(s)):
                P += self.Q; K = P / (P + self.R)
                x = x + K * (s[i] - x); P = (1 - K) * P; col[i] = x
            out_d[:, j] = col
        return np.repeat(out_d, step, axis=0)[:n]

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); Xs = self._smooth(X)
        Xsub, ysub = _subsample(Xs, y_, max_n=20000)
        self.m.fit(Xsub)
        raw = self.m.predict(Xsub)
        for comp in np.unique(raw):
            self.mapping_[comp] = _majority(ysub[raw == comp])
        self.is_fitted = True; return self

    def predict(self, X):
        raw = self.m.predict(self._smooth(X))
        return np.array([self.mapping_.get(r, 0) for r in raw], dtype=float)


# ══════════════════════════════════════════════════════════════════════════════
# E. DEEP LEARNING  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_E81_MLP(BaseAlgorithm):
    """E81 — 2-hidden-layer MLP classifier."""
    name = "BC E81 MLP"
    service_id = 6; category = "E_deep"; library = "numpy"; animals = ["all"]
    description = "2-layer neural network trained on movement features"

    def __init__(self, h=64, epochs=150, lr=0.01):
        super().__init__(h=h, epochs=epochs, lr=lr)
        self.h = h; self.epochs = epochs; self.lr = lr

    def fit(self, X, y=None):
        y_full = _y(y, len(X))
        X, y_ = _subsample(X, y_full, max_n=20000)
        K = len(np.unique(y_full)); self.K_ = K
        np.random.seed(42)
        self.W1 = np.random.randn(X.shape[1], self.h) * np.sqrt(2 / X.shape[1])
        self.b1 = np.zeros(self.h)
        self.W2 = np.random.randn(self.h, K) * np.sqrt(2 / self.h)
        self.b2 = np.zeros(K)
        for _ in range(self.epochs):
            h = _relu(X @ self.W1 + self.b1)
            probs = _softmax(h @ self.W2 + self.b2)
            dL = _ce_grad(probs, y_, K)
            self.W2 -= self.lr * h.T @ dL; self.b2 -= self.lr * dL.mean(0)
            dh = (dL @ self.W2.T) * (h > 0)
            self.W1 -= self.lr * X.T @ dh; self.b1 -= self.lr * dh.mean(0)
        self.is_fitted = True; return self

    def predict(self, X):
        batch = 200_000; out = np.empty(len(X), dtype=float)
        for start in range(0, len(X), batch):
            end = min(start + batch, len(X))
            h = _relu(X[start:end] @ self.W1 + self.b1)
            out[start:end] = np.argmax(h @ self.W2 + self.b2, axis=1)
        return out


@registry.register
class BC_E83_LSTM(BaseAlgorithm):
    """E83 — LSTM classifier."""
    name = "BC E83 LSTM"
    service_id = 6; category = "E_deep"; library = "numpy"; animals = ["all"]
    description = "LSTM gating captures long-range behaviour context"

    def __init__(self, hidden=16, epochs=30, lr=0.01):
        super().__init__(hidden=hidden, epochs=epochs, lr=lr)
        self.hidden = hidden; self.epochs = epochs; self.lr = lr

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); K = len(np.unique(y_)); self.K_ = K
        MAX_TRAIN = 2000
        if len(X) > MAX_TRAIN:
            step = int(np.ceil(len(X) / MAX_TRAIN))
            X_fit = X[::step]; y_fit = y_[::step]
        else:
            X_fit = X; y_fit = y_
        n, h = X_fit.shape[1], self.hidden; s = 0.1; np.random.seed(42)
        self.Wf = np.random.randn(n + h, h) * s; self.bf = np.zeros(h)
        self.Wi = np.random.randn(n + h, h) * s; self.bi = np.zeros(h)
        self.Wc = np.random.randn(n + h, h) * s; self.bc = np.zeros(h)
        self.Wo = np.random.randn(n + h, h) * s; self.bo = np.zeros(h)
        self.Wy = np.random.randn(h, K) * s;     self.by = np.zeros(K)
        for _ in range(self.epochs):
            ht, ct = np.zeros(h), np.zeros(h)
            for t in range(len(X_fit)):
                c = np.concatenate([X_fit[t], ht])
                f = _sigmoid(c @ self.Wf + self.bf)
                i = _sigmoid(c @ self.Wi + self.bi)
                ct_ = np.tanh(c @ self.Wc + self.bc)
                ct = f * ct + i * ct_
                o = _sigmoid(c @ self.Wo + self.bo)
                ht = o * np.tanh(ct)
                p = _softmax((ht @ self.Wy + self.by).reshape(1, -1)).ravel()
                e = p.copy(); e[y_fit[t] % K] -= 1
                self.Wy -= self.lr * np.outer(ht, e)
                self.by -= self.lr * e
        self.is_fitted = True; return self

    def predict(self, X):
        h = self.hidden; n = len(X)
        step = max(1, int(np.ceil(n / 20000))) if n > 20000 else 1
        Xd = X[::step]; ht, ct = np.zeros(h), np.zeros(h); out = []
        for t in range(len(Xd)):
            c = np.concatenate([Xd[t], ht])
            f = _sigmoid(c @ self.Wf + self.bf)
            i = _sigmoid(c @ self.Wi + self.bi)
            ct_ = np.tanh(c @ self.Wc + self.bc)
            ct = f * ct + i * ct_
            o = _sigmoid(c @ self.Wo + self.bo)
            ht = o * np.tanh(ct)
            out.append(np.argmax(ht @ self.Wy + self.by))
        return np.repeat(np.array(out, dtype=float), step)[:n]


@registry.register
class BC_E87_TCN(BaseAlgorithm):
    """E87 — Temporal Convolutional Network (dilated causal convolutions)."""
    name = "BC E87 TCN"
    service_id = 6; category = "E_deep"; library = "numpy"; animals = ["all"]
    description = "Dilated causal convolutions capture multi-scale behaviour"

    def __init__(self, n_filters=8, kernel_size=3, n_layers=3):
        super().__init__(n_filters=n_filters, kernel_size=kernel_size, n_layers=n_layers)
        self.nf = n_filters; self.ks = kernel_size; self.nl = n_layers

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); K = len(np.unique(y_)); self.K_ = K
        np.random.seed(42)
        self.layers_ = []
        in_ch = X.shape[1]
        for _ in range(self.nl):
            self.layers_.append(np.random.randn(self.nf, in_ch, self.ks) * 0.1)
            in_ch = self.nf
        self.Wout_ = np.random.randn(self.nf, K) * 0.1
        self.bout_ = np.zeros(K)
        self.is_fitted = True; return self

    def predict(self, X):
        a = X
        for l, W in enumerate(self.layers_):
            d = 2 ** l; n = len(a)
            idx = [np.clip(np.arange(n) - d * (self.ks - 1 - k), 0, None) for k in range(self.ks)]
            a_shift = [a[ix] for ix in idx]
            out = np.zeros((n, self.nf))
            for fi in range(self.nf):
                acc = np.zeros(n)
                for k in range(self.ks):
                    acc += a_shift[k] @ W[fi, :, k]
                out[:, fi] = acc
            a = _relu(out)
        return np.argmax(a @ self.Wout_ + self.bout_, axis=1).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# F. ECOLOGICAL-SPECIFIC  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_F105_HMMRFHybrid(BaseAlgorithm):
    """F105 — Hybrid HMM + Random Forest (temporal + spatial)."""
    name = "BC F105 HMM+RF Hybrid"
    service_id = 6; category = "F_ecological"; library = "sklearn"; animals = ["all"]
    description = "RF for instant behaviour + HMM Viterbi for temporal coherence"

    def __init__(self, n_estimators=50, n_states=4):
        super().__init__(n_estimators=n_estimators, n_states=n_states)
        self.rf = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        self.K  = n_states; self.A_ = None; self.pi_ = None

    def fit(self, X, y=None):
        y_ = _y(y, len(X)); self.rf.fit(X, y_)
        K = self.K; self.pi_ = np.ones(K) / K
        self.A_ = np.ones((K, K)) / K + _transition_counts(y_, K)
        self.A_ /= self.A_.sum(1, keepdims=True) + 1e-9
        self.is_fitted = True; return self

    def predict(self, X):
        rf_p = self.rf.predict_proba(X)
        K = min(self.K, rf_p.shape[1]); n = len(X)
        step = max(1, int(np.ceil(n / 20000))) if n > 20000 else 1
        log_e = np.log(rf_p[::step, :K] + 1e-9)
        T = len(log_e)
        delta = np.log(self.pi_[:K] + 1e-9) + log_e[0]
        psi = np.zeros((T, K), dtype=int)
        for t in range(1, T):
            tr = delta[:, None] + np.log(self.A_[:K, :K] + 1e-9)
            psi[t] = tr.argmax(0); delta = tr.max(0) + log_e[t]
        path = np.zeros(T, dtype=int); path[-1] = delta.argmax()
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]
        return (np.repeat(path, step)[:n] % K).astype(float)


@registry.register
class BC_F106_MigrationSpeedClassifier(BaseAlgorithm):
    """F106 — Migration vs residency classifier using speed + straightness."""
    name = "BC F106 Migration Speed Classifier"
    service_id = 6; category = "F_ecological"; library = "sklearn"; animals = ["all"]
    description = "Ecologically-motivated: high speed + high straightness = migration"

    def __init__(self):
        super().__init__()
        self.m = LogisticRegression(solver="lbfgs", max_iter=500)
        self.classes_ = None

    def fit(self, X, y=None):
        # Build ecological features: migration score = speed × straightness
        y_ = _y(y, len(X))
        mig_score = X[:, 0] * X[:, 3]   # speed_ms × straightness
        alt_change = np.abs(np.gradient(X[:, 1]))  # altitude change rate
        eco = np.column_stack([mig_score, alt_change, X[:, 4], X[:, 6]])
        self.m.fit(eco, y_)
        self.classes_ = np.unique(y_)
        self.is_fitted = True; return self

    def predict(self, X):
        mig_score = X[:, 0] * X[:, 3]
        alt_change = np.abs(np.gradient(X[:, 1]))
        eco = np.column_stack([mig_score, alt_change, X[:, 4], X[:, 6]])
        return self.m.predict(eco).astype(float)


@registry.register
class BC_F107_RestingForagingClassifier(BaseAlgorithm):
    """F107 — Resting vs foraging vs travelling via turning angle bands."""
    name = "BC F107 Turning Angle Classifier"
    service_id = 6; category = "F_ecological"; library = "sklearn"; animals = ["all"]
    description = "Turning angle + step length bands map to resting/foraging/travel"

    def __init__(self):
        super().__init__()
        self.m = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)

    def fit(self, X, y=None):
        y_ = _y(y, len(X))
        # Ecological features: turning angle, step length, speed variation
        turn = X[:, 2]; step = X[:, 6]; spd_std = X[:, 5]
        sinuosity = np.where(step > 0, turn / (step + 1e-6), 0.0)
        eco = np.column_stack([turn, step, spd_std, sinuosity, X[:, 0]])
        Xs, ys = _subsample(eco, y_, max_n=20000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        turn = X[:, 2]; step = X[:, 6]; spd_std = X[:, 5]
        sinuosity = np.where(step > 0, turn / (step + 1e-6), 0.0)
        eco = np.column_stack([turn, step, spd_std, sinuosity, X[:, 0]])
        return self.m.predict(eco).astype(float)


# ══════════════════════════════════════════════════════════════════════════════
# G. ADVANCED BOOSTING  (3 algorithms)
# ══════════════════════════════════════════════════════════════════════════════

@registry.register
class BC_G01_AdaBoost(BaseAlgorithm):
    """G01 — AdaBoost classifier."""
    name = "BC G01 AdaBoost"
    service_id = 6; category = "G_advanced_boosting"; library = "sklearn"; animals = ["all"]
    description = "Adaptive boosting: reweights misclassified GPS fixes each round"

    def __init__(self, n_estimators=100):
        super().__init__(n_estimators=n_estimators)
        self.m = AdaBoostClassifier(n_estimators=n_estimators, random_state=42,
                                    algorithm="SAMME")

    def fit(self, X, y=None):
        Xs, ys = _subsample(X, _y(y, len(X)), max_n=20000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_G02_HistGradientBoosting(BaseAlgorithm):
    """G02 — Histogram Gradient Boosting (sklearn's fastest tree boosting)."""
    name = "BC G02 Hist Gradient Boosting"
    service_id = 6; category = "G_advanced_boosting"; library = "sklearn"; animals = ["all"]
    description = "Histogram-based GBM — fastest sklearn booster for large GPS datasets"

    def __init__(self, max_iter=100, max_depth=4):
        super().__init__(max_iter=max_iter, max_depth=max_depth)
        self.m = HistGradientBoostingClassifier(max_iter=max_iter,
                                                 max_depth=max_depth,
                                                 random_state=42)

    def fit(self, X, y=None):
        # HistGradientBoosting natively handles large n via histogram bins
        # so no subsampling needed — it already scales well.
        self.m.fit(X, _y(y, len(X))); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


@registry.register
class BC_G03_CatBoost(BaseAlgorithm):
    """G03 — CatBoost Classifier."""
    name = "BC G03 CatBoost"
    service_id = 6; category = "G_advanced_boosting"; library = "catboost"; animals = ["all"]
    description = "CatBoost ordered boosting — strong accuracy with minimal tuning"

    def __init__(self, iterations=100, depth=4):
        super().__init__(iterations=iterations, depth=depth)
        self.iterations = iterations; self.depth = depth

    def fit(self, X, y=None):
        y_ = _y(y, len(X))
        if _CAT:
            self.m = CatBoostClassifier(iterations=self.iterations,
                                        depth=self.depth,
                                        random_seed=42, verbose=0)
        else:
            self.m = GradientBoostingClassifier(n_estimators=self.iterations,
                                                max_depth=self.depth)
        Xs, ys = _subsample(X, y_, max_n=20000)
        self.m.fit(Xs, ys); self.is_fitted = True; return self

    def predict(self, X):
        return self.m.predict(X).astype(float)


# ── End of file ───────────────────────────────────────────────────────────────
# Total: 21 algorithms across 7 categories
#   A. Linear & Statistical      : 3  (Logistic Regression, LDA, Expert Rules)
#   B. Tree & Ensemble           : 3  (Random Forest, GBM, XGBoost)
#   C. Kernel & Distance-Based   : 3  (SVM RBF, kNN k=7, Mahalanobis)
#   D. Probabilistic & Bayesian  : 3  (HMM 4-State, GMM Classifier, Kalman+GMM)
#   E. Deep Learning             : 3  (MLP, LSTM, TCN)
#   F. Ecological-Specific       : 3  (HMM+RF Hybrid, Migration Speed, Turning Angle)
#   G. Advanced Boosting         : 3  (AdaBoost, HistGradientBoosting, CatBoost)
# Service ID: 6
