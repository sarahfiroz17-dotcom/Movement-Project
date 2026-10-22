"""
core/evaluator.py
=================
VEBITA Shared Evaluator

Computes the right metrics for each service type automatically.
The benchmark runner calls this — team members don't need to worry about it.

Service metrics:
    S1 Time Series       → MAE, RMSE, R²
    S2 Pattern Recog.    → Silhouette score, ARI, NMI
    S3 Environmental     → Pearson r, Spearman r, R²
    S4 Anomaly Detection → AUC-ROC, Precision, Recall, F1
    S5 Segmentation      → Accuracy, F1-macro, Jaccard
    S6 Classification    → Accuracy, F1-macro, F1-weighted
"""

import numpy as np
from typing import Optional, Dict


class Evaluator:

    @staticmethod
    def compute_metrics(
        y_true:     np.ndarray,
        y_pred:     np.ndarray,
        service_id: int,
        scores:     Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        Compute appropriate metrics for a given service.
        Returns a flat dict of metric_name → float.
        """
        try:
            if service_id == 1:
                return Evaluator._regression_metrics(y_true, y_pred)
            elif service_id == 2:
                return Evaluator._clustering_metrics(y_true, y_pred)
            elif service_id == 3:
                return Evaluator._correlation_metrics(y_true, y_pred)
            elif service_id == 4:
                return Evaluator._anomaly_metrics(y_true, y_pred, scores)
            elif service_id == 5:
                return Evaluator._segmentation_metrics(y_true, y_pred)
            elif service_id == 6:
                return Evaluator._classification_metrics(y_true, y_pred)
            else:
                return Evaluator._classification_metrics(y_true, y_pred)
        except Exception as e:
            return {"metric_error": str(e)}

    # ── S1: Time series (regression / forecasting) ────────────────────────
    @staticmethod
    def _regression_metrics(y_true, y_pred) -> dict:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        y_t = np.array(y_true, dtype=float)
        y_p = np.array(y_pred, dtype=float)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]
        return {
            "mae":      round(float(mean_absolute_error(y_t, y_p)), 4),
            "rmse":     round(float(np.sqrt(mean_squared_error(y_t, y_p))), 4),
            "r2":       round(float(r2_score(y_t, y_p)), 4),
        }

    # ── S2: Pattern recognition / clustering ─────────────────────────────
    @staticmethod
    def _clustering_metrics(y_true, y_pred) -> dict:
        from sklearn.metrics import (
            adjusted_rand_score, normalized_mutual_info_score,
            silhouette_score
        )
        y_t = np.array(y_true)
        y_p = np.array(y_pred)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]
        metrics = {
            "ari": round(float(adjusted_rand_score(y_t, y_p)), 4),
            "nmi": round(float(normalized_mutual_info_score(y_t, y_p)), 4),
        }
        return metrics

    # ── S3: Environmental factors (correlation) ───────────────────────────
    @staticmethod
    def _correlation_metrics(y_true, y_pred) -> dict:
        from scipy.stats import pearsonr, spearmanr
        from sklearn.metrics import r2_score
        y_t = np.array(y_true, dtype=float)
        y_p = np.array(y_pred, dtype=float)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]
        pearson_r,  _ = pearsonr(y_t, y_p)
        spearman_r, _ = spearmanr(y_t, y_p)
        return {
            "pearson_r":  round(float(pearson_r), 4),
            "spearman_r": round(float(spearman_r), 4),
            "r2":         round(float(r2_score(y_t, y_p)), 4),
        }

    # ── S4: Anomaly detection ─────────────────────────────────────────────
    @staticmethod
    def _anomaly_metrics(y_true, y_pred, scores=None) -> dict:
        from sklearn.metrics import (
            precision_score, recall_score, f1_score,
            roc_auc_score, average_precision_score
        )
        y_t = np.array(y_true)
        y_p = np.array(y_pred)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]

        # Convert to binary if needed
        y_t_bin = (y_t > 0).astype(int)
        y_p_bin = (y_p > 0).astype(int)

        metrics = {
            "precision": round(float(precision_score(y_t_bin, y_p_bin, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_t_bin, y_p_bin, zero_division=0)), 4),
            "f1":        round(float(f1_score(y_t_bin, y_p_bin, zero_division=0)), 4),
        }
        if scores is not None and len(np.unique(y_t_bin)) > 1:
            sc = np.array(scores[:min_len])
            try:
                metrics["auc_roc"] = round(float(roc_auc_score(y_t_bin, sc)), 4)
            except Exception:
                pass
        return metrics

    # ── S5: Trajectory segmentation ───────────────────────────────────────
    @staticmethod
    def _segmentation_metrics(y_true, y_pred) -> dict:
        from sklearn.metrics import (
            accuracy_score, f1_score,
            adjusted_rand_score, jaccard_score
        )
        y_t = np.array(y_true)
        y_p = np.array(y_pred)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]

        # Re-map predicted labels to best matching true labels
        y_p_mapped = Evaluator._remap_labels(y_t, y_p)

        metrics = {
            "accuracy":  round(float(accuracy_score(y_t, y_p_mapped)), 4),
            "f1_macro":  round(float(f1_score(y_t, y_p_mapped,
                                              average="macro", zero_division=0)), 4),
            "ari":       round(float(adjusted_rand_score(y_t, y_p)), 4),
        }
        return metrics

    # ── S6: Behavioural classification ────────────────────────────────────
    @staticmethod
    def _classification_metrics(y_true, y_pred) -> dict:
        from sklearn.metrics import (
            accuracy_score, f1_score, precision_score, recall_score
        )
        y_t = np.array(y_true)
        y_p = np.array(y_pred)
        min_len = min(len(y_t), len(y_p))
        y_t, y_p = y_t[:min_len], y_p[:min_len]
        return {
            "accuracy":    round(float(accuracy_score(y_t, y_p)), 4),
            "f1_macro":    round(float(f1_score(y_t, y_p, average="macro", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(y_t, y_p, average="weighted", zero_division=0)), 4),
            "precision":   round(float(precision_score(y_t, y_p, average="macro", zero_division=0)), 4),
            "recall":      round(float(recall_score(y_t, y_p, average="macro", zero_division=0)), 4),
        }

    # ── Utility: remap cluster labels to best matching true labels ────────
    @staticmethod
    def _remap_labels(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
        """
        HMM / clustering algorithms return arbitrary integer labels.
        This maps each predicted label to the true label it overlaps most with.
        """
        from scipy.stats import mode
        y_out = np.zeros_like(y_pred)
        for label in np.unique(y_pred):
            mask = y_pred == label
            if mask.sum() == 0:
                continue
            most_common = mode(y_true[mask], keepdims=True).mode[0]
            y_out[mask] = most_common
        return y_out
