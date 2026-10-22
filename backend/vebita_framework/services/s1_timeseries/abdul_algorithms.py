"""
services/s1_timeseries/abdul_algorithms.py
==========================================
Service 1 - Time Series Analysis (Abdul Rehman)
83 algorithms for animal GPS movement data.
Features: speed_ms, altitude_m, turning_angle, straightness,
          speed_roll_mean, speed_roll_std, step_length_m, alt_roll_mean
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")

from core.base import BaseAlgorithm
from core.registry import registry


# ---- helpers ---------------------------------------------------------------

def _speed(X):
    return X[:, 0].astype(float)

def _ema(arr, alpha):
    out = np.empty_like(arr, dtype=float)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out

def _subsample(X, y=None, max_n=20000, seed=42):
    """Bound the sample count fed to algorithms whose fit cost grows
    faster than linearly with n (matches the subsampling pattern used
    elsewhere in this codebase, e.g. services/s3_environment)."""
    if len(X) <= max_n:
        return X, y
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(X), max_n, replace=False)
    return X[idx], (y[idx] if y is not None else None)


# ============================================================
# STATISTICAL METHODS (22)
# ============================================================

@registry.register
class WeightedMovingAverage(BaseAlgorithm):
    name        = "Weighted Moving Average"
    service_id  = 1
    category    = "statistical"
    library     = "numpy"
    animals     = ["all"]
    description = "Linearly-weighted moving average of speed_ms"

    def __init__(self, window=5):
        super().__init__(window=window)
        self.window = window

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s = _speed(X)
        w = np.arange(1, self.window + 1, dtype=float)
        w /= w.sum()
        return np.convolve(s, w[::-1], mode='same')












































# ============================================================
# FORECASTING METHODS (18)
# ============================================================

@registry.register
class ARIMAForecast(BaseAlgorithm):
    name        = "ARIMA Forecast"
    service_id  = 1
    category    = "forecasting"
    library     = "numpy"
    animals     = ["all"]
    description = "AR(2) ARIMA-style one-step-ahead forecast of speed_ms"

    def fit(self, X, y=None):
        s = _speed(X)
        n = len(s)
        if n > 3:
            r0    = np.var(s)
            r1    = np.cov(s[:-1], s[1:])[0, 1]
            r2    = np.cov(s[:-2], s[2:])[0, 1]
            denom = r0**2 - r1**2 + 1e-10
            self.phi1_ = (r1 * r0 - r1 * r2) / denom
            self.phi2_ = (r0 * r2 - r1**2)   / denom
        else:
            self.phi1_, self.phi2_ = 0.5, 0.1
        self.mean_  = s.mean()
        self.last2_ = list(s[-2:])
        self.is_fitted = True
        return self

    def predict(self, X):
        s   = _speed(X)
        buf = list(self.last2_)
        out = np.empty(len(s))
        for i, v in enumerate(s):
            out[i] = (self.mean_
                      + self.phi1_ * (buf[-1] - self.mean_)
                      + self.phi2_ * (buf[-2] - self.mean_))
            buf.append(v)
        return out


@registry.register
class SARIMAForecast(BaseAlgorithm):
    name        = "SARIMA Forecast"
    service_id  = 1
    category    = "forecasting"
    library     = "numpy"
    animals     = ["all"]
    description = "Seasonal AR forecast with period=12 for speed_ms"

    def __init__(self, period=12):
        super().__init__(period=period)
        self.period = period

    def fit(self, X, y=None):
        s = _speed(X)
        p = min(self.period, max(2, len(s) // 2))
        self.seasonal_mean_ = np.array([s[i::p].mean() for i in range(p)])
        self.overall_mean_  = s.mean()
        self.phi_           = np.corrcoef(s[:-1], s[1:])[0, 1] if len(s) > 1 else 0.5
        self.last_          = s[-1]
        self.p_             = p
        self.n_             = len(s)
        self.is_fitted = True
        return self

    def predict(self, X):
        s   = _speed(X)
        out = np.empty(len(s))
        prev = self.last_
        for i, v in enumerate(s):
            si     = (self.n_ + i) % self.p_
            out[i] = (self.overall_mean_
                      + self.phi_ * (prev - self.overall_mean_)
                      + 0.3 * (self.seasonal_mean_[si] - self.overall_mean_))
            prev = v
        return out






@registry.register
class TripleExpSmoothing(BaseAlgorithm):
    name        = "Triple Exponential Smoothing"
    service_id  = 1
    category    = "forecasting"
    library     = "numpy"
    animals     = ["all"]
    description = "Holt-Winters triple exponential smoothing forecast"

    def __init__(self, alpha=0.3, beta=0.1, gamma=0.1, period=12):
        super().__init__(alpha=alpha, beta=beta, gamma=gamma, period=period)
        self.alpha  = alpha
        self.beta   = beta
        self.gamma  = gamma
        self.period = period

    def fit(self, X, y=None):
        s = _speed(X)
        p = min(self.period, max(2, len(s) // 4))
        self.l_      = np.mean(s[:p])
        self.b_      = (np.mean(s[p:2*p]) - self.l_) / p if len(s) >= 2*p else 0.0
        self.season_ = s[:p] - self.l_
        self.p_      = p
        self.is_fitted = True
        return self

    def predict(self, X):
        s = _speed(X)
        p = self.p_
        l, b   = self.l_, self.b_
        season = self.season_.copy()
        out    = np.empty(len(s))
        for i, v in enumerate(s):
            si     = i % p
            out[i] = l + b + season[si]
            ln     = self.alpha * (v - season[si]) + (1 - self.alpha) * (l + b)
            b      = self.beta  * (ln - l)          + (1 - self.beta)  * b
            season[si] = self.gamma * (v - ln) + (1 - self.gamma) * season[si]
            l = ln
        return out


@registry.register
class ThetaMethodForecast(BaseAlgorithm):
    name        = "Theta Method"
    service_id  = 1
    category    = "forecasting"
    library     = "numpy"
    animals     = ["all"]
    description = "Theta method: average of linear trend and SES forecast"

    def fit(self, X, y=None):
        s = _speed(X)
        n = len(s)
        t = np.arange(n)
        self.slope_     = np.polyfit(t, s, 1)[0]
        self.intercept_ = s[0]
        level = s[0]
        for v in s[1:]:
            level = 0.5 * v + 0.5 * level
        self.ses_level_ = level
        self.n_         = n
        self.is_fitted  = True
        return self

    def predict(self, X):
        n = len(X)
        t       = np.arange(self.n_, self.n_ + n)
        theta0  = self.intercept_ + self.slope_ * t
        theta2  = np.full(n, self.ses_level_)
        return 0.5 * (theta0 + theta2)












@registry.register
class LinearRegressionForecast(BaseAlgorithm):
    name        = "Linear Regression Forecast"
    service_id  = 1
    category    = "forecasting"
    library     = "sklearn"
    animals     = ["all"]
    description = "Linear regression over all 8 features to predict speed_ms"

    def fit(self, X, y=None):
        from sklearn.linear_model import LinearRegression
        self.lr_       = LinearRegression().fit(X[:, 1:], X[:, 0])
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.lr_.predict(X[:, 1:])


@registry.register
class RidgeRegressionForecast(BaseAlgorithm):
    name        = "Ridge Regression Forecast"
    service_id  = 1
    category    = "forecasting"
    library     = "sklearn"
    animals     = ["all"]
    description = "Ridge regression forecast of speed_ms from other features"

    def __init__(self, alpha=1.0):
        super().__init__(alpha=alpha)
        self.alpha = alpha

    def fit(self, X, y=None):
        from sklearn.linear_model import Ridge
        self.model_    = Ridge(alpha=self.alpha).fit(X[:, 1:], X[:, 0])
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model_.predict(X[:, 1:])










@registry.register
class GradientBoostingForecast(BaseAlgorithm):
    name        = "Gradient Boosting Forecast"
    service_id  = 1
    category    = "forecasting"
    library     = "sklearn"
    animals     = ["all"]
    description = "Gradient Boosting regressor forecast of speed_ms"

    def fit(self, X, y=None):
        from sklearn.ensemble import GradientBoostingRegressor
        # sklearn's (non-histogram) GradientBoostingRegressor builds each
        # of n_estimators=50 trees via exact sorted-feature splits -> far
        # too slow to fit on the full ~10.7M-row training set (hangs at
        # true scale). Subsample like the other super-linear-cost fits in
        # this codebase; predict() stays on the full test set since tree
        # traversal at predict time is cheap regardless of n.
        Xs, _ = _subsample(X, max_n=20000)
        self.model_    = GradientBoostingRegressor(
            n_estimators=50, max_depth=3, random_state=42
        ).fit(Xs[:, 1:], Xs[:, 0])
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model_.predict(X[:, 1:])


# ============================================================
# DECOMPOSITION (14)
# ============================================================

@registry.register
class STLDecompose(BaseAlgorithm):
    name        = "STL Decompose"
    service_id  = 1
    category    = "decomposition"
    library     = "scipy"
    animals     = ["all"]
    description = "STL trend via uniform smoothing of speed_ms"

    def __init__(self, period=12):
        super().__init__(period=period)
        self.period = period

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        from scipy.ndimage import uniform_filter1d
        s  = _speed(X)
        sz = max(3, min(self.period, len(s) // 4))
        return uniform_filter1d(s, size=sz)




@registry.register
class EMDDecompose(BaseAlgorithm):
    name        = "EMD Decompose"
    service_id  = 1
    category    = "decomposition"
    library     = "numpy"
    animals     = ["all"]
    description = "Empirical Mode Decomposition envelope-mean IMF approximation"

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        from scipy.signal import argrelextrema
        s = _speed(X)
        try:
            hi_idx = np.concatenate([[0], argrelextrema(s, np.greater)[0], [len(s)-1]])
            lo_idx = np.concatenate([[0], argrelextrema(s, np.less)[0],    [len(s)-1]])
            upper  = np.interp(np.arange(len(s)), hi_idx, s[hi_idx])
            lower  = np.interp(np.arange(len(s)), lo_idx, s[lo_idx])
            return s - (upper + lower) / 2
        except Exception:
            return s - s.mean()




@registry.register
class CEEMDANDecompose(BaseAlgorithm):
    name        = "CEEMDAN Decompose"
    service_id  = 1
    category    = "decomposition"
    library     = "numpy"
    animals     = ["all"]
    description = "Complete EEMD with Adaptive Noise — numpy approximation"

    def fit(self, X, y=None):
        self.noise_std_ = _speed(X).std() * 0.05
        self.is_fitted  = True
        return self

    def predict(self, X):
        s = _speed(X)
        np.random.seed(0)
        return np.mean(
            [_ema(s + np.random.normal(0, self.noise_std_, len(s)), 0.25)
             for _ in range(10)],
            axis=0
        )




@registry.register
class WaveletDWT(BaseAlgorithm):
    name        = "Wavelet DWT Denoise"
    service_id  = 1
    category    = "decomposition"
    library     = "numpy"
    animals     = ["all"]
    description = "Haar DWT level-2 approximation of speed_ms"

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s  = _speed(X)
        a1 = np.convolve(s, np.array([0.5, 0.5]), mode='same')
        a2 = np.convolve(a1, np.array([0.5, 0.5]), mode='same')
        return a2






@registry.register
class SSAReconstruction(BaseAlgorithm):
    name        = "SSA Reconstruction"
    service_id  = 1
    category    = "decomposition"
    library     = "numpy"
    animals     = ["all"]
    description = "Singular Spectrum Analysis low-rank reconstruction of speed_ms"

    def __init__(self, window=10, n_components=3):
        super().__init__(window=window, n_components=n_components)
        self.window       = window
        self.n_components = n_components

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s = _speed(X)
        n = len(s)
        L = min(self.window, n // 2)
        K = n - L + 1
        if K < 1 or L < 1:
            return s.copy()
        traj = np.array([s[i:i+L] for i in range(K)])
        U, sv, Vt = np.linalg.svd(traj, full_matrices=False)
        k         = min(self.n_components, len(sv))
        rec_traj  = sum(sv[i] * np.outer(U[:, i], Vt[i]) for i in range(k))
        result    = np.zeros(n)
        counts    = np.zeros(n)
        for i in range(K):
            result[i:i+L] += rec_traj[i]
            counts[i:i+L] += 1
        return result / np.maximum(counts, 1)


@registry.register
class PCAReconstruction(BaseAlgorithm):
    name        = "PCA Reconstruction"
    service_id  = 1
    category    = "decomposition"
    library     = "sklearn"
    animals     = ["all"]
    description = "PCA low-rank reconstruction — returns speed_ms channel"

    def __init__(self, n_components=3):
        super().__init__(n_components=n_components)
        self.n_components = n_components

    def fit(self, X, y=None):
        from sklearn.decomposition import PCA
        n          = min(self.n_components, X.shape[1], X.shape[0])
        self.pca_  = PCA(n_components=n).fit(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        recon = self.pca_.inverse_transform(self.pca_.transform(X))
        return recon[:, 0]








# ============================================================
# SIGNAL PROCESSING (13)
# ============================================================

@registry.register
class SavitzkyGolaySmooth(BaseAlgorithm):
    name        = "Savitzky-Golay Smooth"
    service_id  = 1
    category    = "signal_processing"
    library     = "scipy"
    animals     = ["all"]
    description = "Savitzky-Golay polynomial smoothing of speed_ms"

    def __init__(self, window=11, polyorder=3):
        super().__init__(window=window, polyorder=polyorder)
        self.window    = window
        self.polyorder = polyorder

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        from scipy.signal import savgol_filter
        s = _speed(X)
        w = min(self.window, len(s))
        if w % 2 == 0:
            w -= 1
        w = max(w, self.polyorder + 2 + (self.polyorder % 2 == 0))
        if w > len(s):
            return s.copy()
        return savgol_filter(s, window_length=w, polyorder=min(self.polyorder, w - 1))




@registry.register
class KalmanSmoother(BaseAlgorithm):
    name        = "Kalman Smoother"
    service_id  = 1
    category    = "signal_processing"
    library     = "numpy"
    animals     = ["all"]
    description = "1D Kalman filter smoothing of speed_ms"

    def __init__(self, q=1e-3, r=0.1):
        super().__init__(q=q, r=r)
        self.q = q
        self.r = r

    def fit(self, X, y=None):
        s          = _speed(X)
        self.x_    = float(s[0])
        self.p_    = 1.0
        self.is_fitted = True
        return self

    def predict(self, X):
        s   = _speed(X)
        x, p = self.x_, self.p_
        out = np.empty(len(s))
        for i, z in enumerate(s):
            p    = p + self.q
            k    = p / (p + self.r)
            x    = x + k * (z - x)
            p    = (1 - k) * p
            out[i] = x
        return out






@registry.register
class FFTLowPassReconstruct(BaseAlgorithm):
    name        = "FFT Low-Pass Reconstruct"
    service_id  = 1
    category    = "signal_processing"
    library     = "numpy"
    animals     = ["all"]
    description = "Retain lowest-frequency FFT components of speed_ms"

    def __init__(self, keep_fraction=0.1):
        super().__init__(keep_fraction=keep_fraction)
        self.keep_fraction = keep_fraction

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s      = _speed(X)
        fft    = np.fft.rfft(s)
        cutoff = max(1, int(len(fft) * self.keep_fraction))
        fft[cutoff:] = 0
        return np.fft.irfft(fft, n=len(s))














@registry.register
class MFCCRegressionForecast(BaseAlgorithm):
    name        = "MFCC Regression Forecast"
    service_id  = 1
    category    = "signal_processing"
    library     = "numpy"
    animals     = ["all"]
    description = "MFCC-inspired cepstral coefficient mean for speed_ms frames"

    def __init__(self, n_mfcc=13, window=32):
        super().__init__(n_mfcc=n_mfcc, window=window)
        self.n_mfcc = n_mfcc
        self.window = window

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def _frame_mfcc(self, seg):
        n_fft  = max(len(seg), 32)
        mag    = np.abs(np.fft.rfft(seg, n=n_fft))
        k      = min(self.n_mfcc, len(mag))
        log_s  = np.log(mag[:k] + 1e-10)
        ns     = np.arange(self.n_mfcc)
        dct_m  = np.cos(np.pi * ns[:, None] * (2 * np.arange(k) + 1) / (2 * k))
        return float((dct_m @ log_s).mean())

    def predict(self, X):
        s   = _speed(X)
        out = np.empty(len(s))
        for i in range(len(s)):
            lo     = max(0, i - self.window + 1)
            seg    = s[lo:i+1]
            out[i] = self._frame_mfcc(seg) if len(seg) >= 2 else 0.0
        return out


# ============================================================
# DEEP LEARNING — numpy approximations (16)
# ============================================================

@registry.register
class LSTMForecast(BaseAlgorithm):
    name        = "LSTM Forecast"
    service_id  = 1
    category    = "deep_learning"
    library     = "numpy"
    animals     = ["all"]
    description = "LSTM-style gated recurrent forecast of speed_ms (numpy)"

    def __init__(self, seq_len=10):
        super().__init__(seq_len=seq_len)
        self.seq_len = seq_len

    def fit(self, X, y=None):
        s    = _speed(X)
        lags = min(self.seq_len, len(s) - 1)
        if lags > 0 and len(s) > lags:
            Y        = s[lags:]
            Z        = np.column_stack([s[lags-i-1:len(s)-i-1] for i in range(lags)])
            self.w_, _, _, _ = np.linalg.lstsq(Z, Y, rcond=None)
            self.lags_ = lags
        else:
            self.w_    = np.array([0.5])
            self.lags_ = 1
        self.last_  = list(s[-self.lags_:])
        self.mean_  = s.mean()
        self.std_   = s.std() + 1e-9
        self.is_fitted = True
        return self

    def predict(self, X):
        s   = _speed(X)
        buf = list(self.last_)
        out = np.empty(len(s))
        for i, v in enumerate(s):
            z      = np.array(buf[-self.lags_:])
            c      = np.dot(self.w_, z)
            out[i] = np.tanh(c) * self.std_ + self.mean_
            buf.append(v)
        return out






@registry.register
class TCNForecast(BaseAlgorithm):
    name        = "TCN Forecast"
    service_id  = 1
    category    = "deep_learning"
    library     = "numpy"
    animals     = ["all"]
    description = "Temporal Convolutional Network via dilated causal convolutions"

    def __init__(self, n_levels=4):
        super().__init__(n_levels=n_levels)
        self.n_levels = n_levels

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s      = _speed(X)
        result = s.copy()
        for level in range(self.n_levels):
            d        = 2 ** level
            dilated  = np.empty_like(result)
            dilated[d:] = 0.5 * result[d:] + 0.5 * result[:-d]
            dilated[:d] = result[:d]
            result   = 0.7 * result + 0.3 * dilated
        return result


@registry.register
class TransformerForecast(BaseAlgorithm):
    name        = "Transformer Forecast"
    service_id  = 1
    category    = "deep_learning"
    library     = "numpy"
    animals     = ["all"]
    description = "Transformer self-attention weighted forecast of speed_ms (numpy)"

    def __init__(self, window=16):
        super().__init__(window=window)
        self.window = window

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        s   = _speed(X)
        out = np.empty(len(s))
        for i in range(len(s)):
            lo   = max(0, i - self.window + 1)
            seg  = s[lo:i+1]
            q    = seg.reshape(-1, 1)
            scores = q @ q.T / (len(seg) ** 0.5 + 1e-9)
            attn   = np.exp(scores - scores.max(axis=1, keepdims=True))
            attn  /= attn.sum(axis=1, keepdims=True)
            out[i] = (attn @ q).mean()
        return out






@registry.register
class NBEATSForecast(BaseAlgorithm):
    name        = "N-BEATS Forecast"
    service_id  = 1
    category    = "deep_learning"
    library     = "numpy"
    animals     = ["all"]
    description = "N-BEATS basis expansion forecast of speed_ms (numpy)"

    def __init__(self, degree=3, n_blocks=3):
        super().__init__(degree=degree, n_blocks=n_blocks)
        self.degree   = degree
        self.n_blocks = n_blocks

    def fit(self, X, y=None):
        s    = _speed(X)
        t    = np.arange(len(s)) / max(len(s), 1)
        self.basis_coef_ = []
        residual         = s.copy()
        for _ in range(self.n_blocks):
            coef     = np.polyfit(t, residual, self.degree)
            residual = residual - np.polyval(coef, t)
            self.basis_coef_.append(coef)
        self.n_ = len(s)
        self.is_fitted = True
        return self

    def predict(self, X):
        n = len(X)
        t = np.arange(self.n_, self.n_ + n) / max(self.n_, 1)
        return sum(np.polyval(coef, t) for coef in self.basis_coef_)
















