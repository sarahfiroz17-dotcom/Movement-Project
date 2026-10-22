"""
services/s3_environment/sarah_algorithms.py
============================================
VEBITA — Service 3: Environmental Factors (Sarah)

25 algorithms across 7 categories studying how environmental variables
(temperature, NDVI, terrain, weather, land cover, etc.) relate to and
influence animal movement from Movebank data.

Feature matrix X shape: (n_points, 8)
    speed_ms, altitude_m, turning_angle, straightness,
    speed_roll_mean, speed_roll_std, step_length_m, alt_roll_mean

Service ID: 3
"""

import numpy as np
from sklearn.linear_model import (
    Ridge, BayesianRidge, HuberRegressor,
    ElasticNet, SGDRegressor,
)
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.decomposition import PCA, FastICA, NMF
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    BaggingRegressor,
    VotingRegressor,
    StackingRegressor,
)
from sklearn.neural_network import MLPRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from sklearn.inspection import permutation_importance
from sklearn.linear_model import QuantileRegressor
from scipy import stats

try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

try:
    from lightgbm import LGBMRegressor
    _HAS_LGB = True
except ImportError:
    _HAS_LGB = False

try:
    from catboost import CatBoostRegressor
    _HAS_CAT = True
except ImportError:
    _HAS_CAT = False

from core.base import BaseAlgorithm
from core.registry import registry


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: synthetic environmental features derived from movement data
# In real Movebank use, these would come from raster layers (GEE, ERA5, SRTM).
# ═══════════════════════════════════════════════════════════════════════════════

def _subsample_env(X, y=None, max_n=2000, seed=42):
    if len(X) <= max_n:
        return X, y
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(X), max_n, replace=False)
    return X[idx], (y[idx] if y is not None else None)


def _env_score(X: np.ndarray) -> np.ndarray:
    """
    Composite environmental intensity score built from raw movement features.
    Uses unscaled magnitudes so the target has real variance even on standardised X.
    Score = weighted sum of terrain ruggedness, speed variability, and altitude signal.
    This gives the regression algorithms a meaningful, varying target to learn from.
    """
    E = _env_features(X)
    # terrain_ruggedness (col 0), wind_proxy/spd_std (col 4), energy (col 11)
    terrain  = E[:, 0]
    wind     = E[:, 4]
    energy   = E[:, 11]
    ndvi     = E[:, 2]
    resource = E[:, 8]
    raw = 0.3 * terrain + 0.2 * wind + 0.2 * energy + 0.15 * ndvi + 0.15 * resource
    # Normalise to 0-1 range using training-set statistics stored on first call
    rng = raw.max() - raw.min()
    if rng < 1e-9:
        return np.zeros(len(raw))
    return ((raw - raw.min()) / rng).astype(float)


def _env_features(X: np.ndarray) -> np.ndarray:
    """
    Derive 12 synthetic environmental proxy features from movement features.
    Columns: terrain_ruggedness, slope, ndvi_proxy, land_cover,
             wind_proxy, temperature_proxy, proximity_water, solar_radiation,
             resource_score, elevation_gradient, habitat_boundary, energy_expenditure
    """
    speed    = X[:, 0]
    alt      = X[:, 1]
    turn     = X[:, 2]
    straight = X[:, 3]
    spd_mean = X[:, 4]
    spd_std  = X[:, 5]
    step     = X[:, 6]
    alt_mean = X[:, 7]

    terrain_rug  = np.abs(np.gradient(alt))
    slope        = np.gradient(alt_mean)
    ndvi_proxy   = speed * (1 / (turn + 1))
    land_cover   = np.round(alt_mean / (alt_mean.max() + 1e-6) * 4).astype(float)
    wind_proxy   = spd_std
    temp_proxy   = -alt / (alt.max() + 1e-6)
    prox_water   = ((speed < np.percentile(speed, 25)) & (alt < np.percentile(alt, 25))).astype(float)
    solar        = straight * spd_mean
    resource     = 1 / (turn + 1)
    elev_grad    = np.gradient(alt)
    hab_boundary = (turn > np.percentile(turn, 90)).astype(float)
    energy       = speed ** 2

    return np.column_stack([
        terrain_rug, slope, ndvi_proxy, land_cover,
        wind_proxy, temp_proxy, prox_water, solar,
        resource, elev_grad, hab_boundary, energy,
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 1 — STATISTICAL & REGRESSION  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvBayesianRidge(BaseAlgorithm):
    """Bayesian Ridge regression with automatic regularisation."""
    name        = "Env Bayesian Ridge"
    service_id  = 3
    category    = "statistical"
    library     = "sklearn"
    animals     = ["all"]
    description = "Bayesian regression with uncertainty on environmental effects"

    def __init__(self):
        super().__init__()
        self.model = BayesianRidge()

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=2000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvPLSRegression(BaseAlgorithm):
    """Partial Least Squares: links environmental & movement latent factors."""
    name        = "Env PLS Regression"
    service_id  = 3
    category    = "statistical"
    library     = "sklearn"
    animals     = ["all"]
    description = "PLS finds latent dimensions shared between environment and movement"

    def __init__(self, n_components: int = 3):
        super().__init__(n_components=n_components)
        self.model = PLSRegression(n_components=n_components)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=2000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).ravel().astype(float)


@registry.register
class EnvQuantileRegression(BaseAlgorithm):
    """Quantile regression — models median environmental response robustly."""
    name        = "Env Quantile Regression"
    service_id  = 3
    category    = "statistical"
    library     = "sklearn"
    animals     = ["all"]
    description = "Quantile (median) regression of movement on environment"

    def __init__(self, quantile: float = 0.5):
        super().__init__(quantile=quantile)
        self.model = QuantileRegressor(quantile=quantile, alpha=0.1, solver="highs")

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=2000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 2 — TIME SERIES & TEMPORAL  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvKalmanFilter(BaseAlgorithm):
    """Kalman filter — optimal state estimation of environmental trajectory."""
    name        = "Env Kalman Filter"
    service_id  = 3
    category    = "time_series"
    library     = "numpy"
    animals     = ["all"]
    description = "1D Kalman filter smoothing altitude/temperature state"

    def __init__(self, process_noise: float = 1e-3, obs_noise: float = 0.1):
        super().__init__(process_noise=process_noise, obs_noise=obs_noise)
        self.Q = process_noise
        self.R = obs_noise

    def fit(self, X, y=None):
        self.is_fitted = True
        return self

    def predict(self, X):
        z = _env_score(X)
        n = len(z)
        max_len = 20000
        step = max(1, int(np.ceil(n / max_len))) if n > max_len else 1
        zs = z[::step]
        m = len(zs)
        x_est = np.zeros(m)
        P = 1.0
        x_est[0] = zs[0]
        for i in range(1, m):
            x_pred = x_est[i - 1]
            P_pred = P + self.Q
            K = P_pred / (P_pred + self.R)
            x_est[i] = x_pred + K * (zs[i] - x_pred)
            P = (1 - K) * P_pred
        if step > 1:
            x_est = np.repeat(x_est, step, axis=0)[:n]
        return x_est.astype(float)


@registry.register
class EnvFourierTransform(BaseAlgorithm):
    """Fourier transform: frequency content of environmental influence."""
    name        = "Env Fourier Transform"
    service_id  = 3
    category    = "time_series"
    library     = "numpy"
    animals     = ["all"]
    description = "FFT extracts dominant frequencies in altitude-speed coupling"

    def __init__(self, n_harmonics: int = 5):
        super().__init__(n_harmonics=n_harmonics)
        self.n_harmonics = n_harmonics
        self.filtered_   = None

    def fit(self, X, y=None):
        s = _env_score(X)
        fft = np.fft.rfft(s)
        amps = np.abs(fft)
        top_idx = np.argsort(amps)[-self.n_harmonics:]
        mask = np.zeros_like(fft)
        mask[top_idx] = fft[top_idx]
        self.filtered_ = np.fft.irfft(mask, n=len(s))
        self.is_fitted = True
        return self

    def predict(self, X):
        if self.filtered_ is not None and len(X) == len(self.filtered_):
            return self.filtered_.astype(float)
        s = _env_score(X)
        fft = np.fft.rfft(s)
        amps = np.abs(fft)
        top_idx = np.argsort(amps)[-self.n_harmonics:]
        mask = np.zeros_like(fft)
        mask[top_idx] = fft[top_idx]
        return np.fft.irfft(mask, n=len(s)).astype(float)


@registry.register
class EnvSeasonalDecomposition(BaseAlgorithm):
    """Seasonal decomposition: extract daily/periodic environmental signal."""
    name        = "Env Seasonal Decomposition"
    service_id  = 3
    category    = "time_series"
    library     = "numpy"
    animals     = ["all"]
    description = "Decomposes movement speed into trend + seasonal + residual"

    def __init__(self, period: int = 48):
        super().__init__(period=period)
        self.period    = period
        self.seasonal_ = None

    def fit(self, X, y=None):
        s = _env_score(X)
        trend = np.convolve(s, np.ones(self.period) / self.period, mode="same")
        detrended = s - trend
        self.seasonal_ = np.array([
            np.mean(detrended[i::self.period]) for i in range(self.period)
        ])
        self.is_fitted = True
        return self

    def predict(self, X):
        n = len(X)
        seasonal = self.seasonal_[np.arange(n) % self.period]
        return seasonal.astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 3 — ML SUPERVISED  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvRandomForestRegressor(BaseAlgorithm):
    """Random Forest regression: nonlinear env-movement relationship."""
    name        = "Env Random Forest Regressor"
    service_id  = 3
    category    = "ml_supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "RF regression: environmental features predict movement speed"

    def __init__(self, n_estimators: int = 100):
        super().__init__(n_estimators=n_estimators)
        self.model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, n_jobs=-1)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvGradientBoostingRegressor(BaseAlgorithm):
    """GBM regression for complex environmental response surfaces."""
    name        = "Env Gradient Boosting Regressor"
    service_id  = 3
    category    = "ml_supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "Sequential boosting captures complex env-speed interactions"

    def __init__(self, n_estimators: int = 100, max_depth: int = 3):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth)
        self.model = GradientBoostingRegressor(n_estimators=n_estimators, max_depth=max_depth)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvXGBoostRegressor(BaseAlgorithm):
    """XGBoost for high-accuracy environmental factor modelling."""
    name        = "Env XGBoost Regressor"
    service_id  = 3
    category    = "ml_supervised"
    library     = "xgboost"
    animals     = ["all"]
    description = "XGBoost gradient boosting on environmental features"

    def __init__(self, n_estimators: int = 100, max_depth: int = 4):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth)
        self.n_estimators = n_estimators
        self.max_depth    = max_depth

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        if _HAS_XGB:
            self.model = XGBRegressor(
                n_estimators=self.n_estimators, max_depth=self.max_depth,
                verbosity=0, random_state=42,
            )
        else:
            self.model = GradientBoostingRegressor(n_estimators=self.n_estimators)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 4 — DEEP LEARNING  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvMLPRegressor(BaseAlgorithm):
    """Multi-layer perceptron regression on environmental features."""
    name        = "Env MLP Regressor"
    service_id  = 3
    category    = "deep_learning"
    library     = "sklearn"
    animals     = ["all"]
    description = "Neural network regression: env features → movement speed"

    def __init__(self, hidden_layer_sizes: tuple = (64, 32), max_iter: int = 200):
        super().__init__(hidden_layer_sizes=hidden_layer_sizes, max_iter=max_iter)
        self.model = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            max_iter=max_iter,
            random_state=42,
            early_stopping=True,
        )

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=10000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvGaussianProcessRegressor(BaseAlgorithm):
    """Gaussian Process Regression — probabilistic environmental surface."""
    name        = "Env Gaussian Process Regressor"
    service_id  = 3
    category    = "deep_learning"
    library     = "sklearn"
    animals     = ["all"]
    description = "GPR with Matern kernel: smooth probabilistic env-speed surface"

    def __init__(self, length_scale: float = 1.0, nu: float = 1.5):
        super().__init__(length_scale=length_scale, nu=nu)
        self.model = GaussianProcessRegressor(
            kernel=Matern(length_scale=length_scale, nu=nu),
            random_state=42,
            normalize_y=True,
        )

    def fit(self, X, y=None):
        # GPR training cost is O(n^3); keep sample small
        Xs, _ = _subsample_env(X, None, max_n=500)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvAutoencoderScore(BaseAlgorithm):
    """Autoencoder proxy: PCA reconstruction error as environmental stress."""
    name        = "Env Autoencoder Score"
    service_id  = 3
    category    = "deep_learning"
    library     = "sklearn"
    animals     = ["all"]
    description = "Reconstruction error from PCA bottleneck as env anomaly score"

    def __init__(self, n_components: int = 3):
        super().__init__(n_components=n_components)
        self.pca = PCA(n_components=n_components)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        E = _env_features(Xs)
        self.pca.fit(E)
        self.is_fitted = True
        return self

    def predict(self, X):
        E = _env_features(X)
        E_reduced    = self.pca.transform(E)
        E_reconstructed = self.pca.inverse_transform(E_reduced)
        error = np.mean((E - E_reconstructed) ** 2, axis=1)
        return error.astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 7 — ENVIRONMENTAL FEATURE ENGINEERING  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvPCAScore(BaseAlgorithm):
    """PCA environmental gradient: first principal component score."""
    name        = "Env PCA Score"
    service_id  = 3
    category    = "feature_engineering"
    library     = "sklearn"
    animals     = ["all"]
    description = "Projects env features onto first PC — single environmental gradient"

    def __init__(self):
        super().__init__()
        self.pca = PCA(n_components=1)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.pca.fit(_env_features(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.pca.transform(_env_features(X)).ravel().astype(float)


@registry.register
class EnvICAHabitatComponents(BaseAlgorithm):
    """ICA habitat components: independent environmental signals."""
    name        = "Env ICA Habitat Components"
    service_id  = 3
    category    = "feature_engineering"
    library     = "sklearn"
    animals     = ["all"]
    description = "FastICA extracts statistically independent habitat signals — scores habitat novelty"

    def __init__(self, n_components: int = 3):
        super().__init__(n_components=n_components)
        self.ica = FastICA(n_components=n_components, random_state=42, max_iter=500)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        E = _env_features(Xs)
        self.ica.fit(E)
        # Find the component least correlated with speed (col 0) — the "habitat novelty" axis
        components_train = self.ica.transform(E)
        speed_col = Xs[:, 0]
        corrs = np.abs([np.corrcoef(components_train[:, i], speed_col)[0, 1]
                        for i in range(components_train.shape[1])])
        self.novelty_idx_ = int(np.argmin(corrs))
        self.is_fitted = True
        return self

    def predict(self, X):
        # Score = magnitude of the speed-independent ICA component (habitat novelty)
        components = self.ica.transform(_env_features(X))
        return np.abs(components[:, self.novelty_idx_]).astype(float)


@registry.register
class EnvNMFHabitatParts(BaseAlgorithm):
    """NMF habitat parts: additive terrain/vegetation/energy decomposition."""
    name        = "Env NMF Habitat Parts"
    service_id  = 3
    category    = "feature_engineering"
    library     = "sklearn"
    animals     = ["all"]
    description = "NMF decomposes env features into additive parts — scores terrain/elevation component"

    def __init__(self, n_components: int = 3):
        super().__init__(n_components=n_components)
        self.nmf = NMF(n_components=n_components, random_state=42, max_iter=500)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        E = _env_features(Xs)
        E_pos = E - E.min(axis=0) + 1e-6
        self.E_min_ = E.min(axis=0)
        self.nmf.fit(E_pos)
        # Find the NMF component most correlated with altitude (col 1) — terrain part
        parts_train = self.nmf.transform(E_pos)
        alt_col = Xs[:, 1]
        corrs = np.abs([np.corrcoef(parts_train[:, i], alt_col)[0, 1]
                        for i in range(parts_train.shape[1])])
        self.terrain_idx_ = int(np.argmax(corrs))
        self.is_fitted = True
        return self

    def predict(self, X):
        E = _env_features(X)
        E_pos = E - self.E_min_ + 1e-6
        E_pos = np.clip(E_pos, 0, None)
        parts = self.nmf.transform(E_pos)
        # Score = terrain/elevation-driven habitat part only
        return parts[:, self.terrain_idx_].astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 8 — ENSEMBLE / HYBRID  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvVotingRegressor(BaseAlgorithm):
    """Voting Regressor: averages RF, GBM, and Ridge predictions."""
    name        = "Env Voting Regressor"
    service_id  = 3
    category    = "ensemble"
    library     = "sklearn"
    animals     = ["all"]
    description = "Averages RF + GBM + Ridge for robust env-speed prediction"

    def __init__(self):
        super().__init__()
        self.model = VotingRegressor(estimators=[
            ("rf",    RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)),
            ("gbm",   GradientBoostingRegressor(n_estimators=50, max_depth=3)),
            ("ridge", Ridge(alpha=1.0)),
        ])

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=10000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvBaggingRegressor(BaseAlgorithm):
    """Bagging Regressor: bootstrap aggregation over decision trees."""
    name        = "Env Bagging Regressor"
    service_id  = 3
    category    = "ensemble"
    library     = "sklearn"
    animals     = ["all"]
    description = "Bootstrap aggregation reduces variance in env-speed predictions"

    def __init__(self, n_estimators: int = 50):
        super().__init__(n_estimators=n_estimators)
        self.model = BaggingRegressor(n_estimators=n_estimators, random_state=42, n_jobs=-1)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvLightGBMRegressor(BaseAlgorithm):
    """LightGBM: fastest histogram-based gradient boosting."""
    name        = "Env LightGBM Regressor"
    service_id  = 3
    category    = "ensemble"
    library     = "lightgbm"
    animals     = ["all"]
    description = "LightGBM histogram boosting on environmental proxy features"

    def __init__(self, n_estimators: int = 100, max_depth: int = 4):
        super().__init__(n_estimators=n_estimators, max_depth=max_depth)
        self.n_estimators = n_estimators
        self.max_depth    = max_depth

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        if _HAS_LGB:
            self.model = LGBMRegressor(
                n_estimators=self.n_estimators, max_depth=self.max_depth,
                random_state=42, verbosity=-1,
            )
        else:
            self.model = GradientBoostingRegressor(n_estimators=self.n_estimators)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 9 — CAUSAL / EXPLAINABLE  (3 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvHuberRegressor(BaseAlgorithm):
    """Huber regression: robust to GPS position outliers."""
    name        = "Env Huber Regressor"
    service_id  = 3
    category    = "causal_explainable"
    library     = "sklearn"
    animals     = ["all"]
    description = "Robust regression downweights GPS outlier fixes"

    def __init__(self, epsilon: float = 1.35, alpha: float = 0.0001):
        super().__init__(epsilon=epsilon, alpha=alpha)
        self.model = HuberRegressor(epsilon=epsilon, alpha=alpha, max_iter=200)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=2000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvPermutationImportanceScore(BaseAlgorithm):
    """Permutation importance: which env feature drives speed the most."""
    name        = "Env Permutation Importance Score"
    service_id  = 3
    category    = "causal_explainable"
    library     = "sklearn"
    animals     = ["all"]
    description = "Score = projection onto most important env feature by permutation"

    def __init__(self):
        super().__init__()
        self._base  = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
        self._top_feature = 0

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=5000)
        E = _env_features(Xs)
        self._base.fit(E, _env_score(Xs))
        result = permutation_importance(self._base, E, _env_score(Xs), n_repeats=5, random_state=42)
        self._top_feature = int(np.argmax(result.importances_mean))
        self.is_fitted = True
        return self

    def predict(self, X):
        E = _env_features(X)
        return E[:, self._top_feature].astype(float)


@registry.register
class EnvGrangerCausalScore(BaseAlgorithm):
    """Granger causal proxy: lagged cross-correlation altitude → speed."""
    name        = "Env Granger Causal Score"
    service_id  = 3
    category    = "causal_explainable"
    library     = "numpy"
    animals     = ["all"]
    description = "Cross-correlation lag score: does altitude Granger-cause speed?"

    def __init__(self, max_lag: int = 10):
        super().__init__(max_lag=max_lag)
        self.max_lag   = max_lag
        self._best_lag = 1

    def fit(self, X, y=None):
        score = _env_score(X)
        alt   = X[:, 1]
        # Find lag that maximises cross-correlation
        correlations = [
            abs(np.corrcoef(alt[:-lag], score[lag:])[0, 1])
            for lag in range(1, self.max_lag + 1)
        ]
        self._best_lag = int(np.argmax(correlations)) + 1
        self.is_fitted = True
        return self

    def predict(self, X):
        score = _env_score(X)
        n     = len(score)
        out   = np.zeros(n, dtype=float)
        lag   = self._best_lag
        # Score at each point = env score `lag` steps ago (lagged influence)
        out[lag:] = score[:n - lag]
        out[:lag] = score[0]
        return out.astype(float)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 10 — ADVANCED SUPERVISED  (4 algorithms)
# ═══════════════════════════════════════════════════════════════════════════════

@registry.register
class EnvSGDRegressor(BaseAlgorithm):
    """SGD Regressor: online learning, scales to any dataset size."""
    name        = "Env SGD Regressor"
    service_id  = 3
    category    = "ml_supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "Stochastic gradient descent regression on environmental features"

    def __init__(self, loss: str = "huber", alpha: float = 0.0001):
        super().__init__(loss=loss, alpha=alpha)
        self.model = SGDRegressor(loss=loss, alpha=alpha, max_iter=1000, random_state=42)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvElasticNet(BaseAlgorithm):
    """Elastic Net: combined L1+L2 regularisation for correlated env features."""
    name        = "Env Elastic Net"
    service_id  = 3
    category    = "ml_supervised"
    library     = "sklearn"
    animals     = ["all"]
    description = "L1+L2 combined regularisation handles correlated env proxies"

    def __init__(self, alpha: float = 0.1, l1_ratio: float = 0.5):
        super().__init__(alpha=alpha, l1_ratio=l1_ratio)
        self.model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=1000)

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvStackingRegressor(BaseAlgorithm):
    """Stacking Regressor: meta-learner on top of RF, GBM, and Ridge."""
    name        = "Env Stacking Regressor"
    service_id  = 3
    category    = "ensemble"
    library     = "sklearn"
    animals     = ["all"]
    description = "Meta-learner combines RF + GBM + Ridge for highest accuracy"

    def __init__(self):
        super().__init__()
        self.model = StackingRegressor(
            estimators=[
                ("rf",  RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)),
                ("gbm", GradientBoostingRegressor(n_estimators=50, max_depth=3)),
                ("ridge", Ridge(alpha=1.0)),
            ],
            final_estimator=Ridge(alpha=1.0),
            cv=3,
        )

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=5000)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


@registry.register
class EnvCatBoostRegressor(BaseAlgorithm):
    """CatBoost: gradient boosting optimised for categorical env features."""
    name        = "Env CatBoost Regressor"
    service_id  = 3
    category    = "ensemble"
    library     = "catboost"
    animals     = ["all"]
    description = "CatBoost handles land-cover categorical feature natively"

    def __init__(self, iterations: int = 100, depth: int = 4):
        super().__init__(iterations=iterations, depth=depth)
        self.iterations = iterations
        self.depth      = depth

    def fit(self, X, y=None):
        Xs, _ = _subsample_env(X, None, max_n=20000)
        if _HAS_CAT:
            self.model = CatBoostRegressor(
                iterations=self.iterations, depth=self.depth,
                random_seed=42, verbose=0,
            )
        else:
            self.model = GradientBoostingRegressor(n_estimators=self.iterations)
        self.model.fit(_env_features(Xs), _env_score(Xs))
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(_env_features(X)).astype(float)


# ── End of file ──────────────────────────────────────────────────────────────
# Total algorithms: 25 across 7 categories
# Service ID: 3 — Environmental Factors (Sarah)
