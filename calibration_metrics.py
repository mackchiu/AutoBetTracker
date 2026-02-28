"""
Calibration metrics for sports betting models.

Implements classwise Expected Calibration Error (classwise-ECE) following
Walsh & Joshi (2024) methodology: 20-bin ECE optimized for binary classification
tasks like win/loss and over/under prediction.

Key insight: calibration >> accuracy for profitable sports betting.
A well-calibrated model with 55% accuracy beats a poorly-calibrated one at 65%.

Usage:
    from calibration_metrics import calculate_ece, calibration_report

    ece = calculate_ece(y_true, y_prob, n_bins=20)
    report = calibration_report(y_true, y_prob, n_bins=20)
"""

import numpy as np
from typing import Optional


def calculate_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 20,
) -> float:
    """
    Calculate Expected Calibration Error (ECE).

    ECE measures how well predicted probabilities match observed frequencies.
    Predictions are binned by confidence; within each bin, the gap between
    mean predicted probability and actual positive rate is computed, then
    weighted by bin population.

    ECE = sum_b (|B_b| / N) * |acc(B_b) - conf(B_b)|

    Args:
        y_true: Binary ground truth labels (0 or 1). Shape (n_samples,).
        y_prob: Predicted probabilities for the positive class. Shape (n_samples,).
        n_bins: Number of equal-width bins in [0, 1]. Default 20 per Walsh & Joshi.

    Returns:
        ECE score in [0, 1]. 0 = perfectly calibrated.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    if y_true.shape != y_prob.shape:
        raise ValueError(f"Shape mismatch: y_true {y_true.shape} vs y_prob {y_prob.shape}")
    if len(y_true) == 0:
        return 0.0

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        if i < n_bins - 1:
            mask = (y_prob >= lo) & (y_prob < hi)
        else:
            mask = (y_prob >= lo) & (y_prob <= hi)  # include 1.0 in last bin

        bin_size = mask.sum()
        if bin_size == 0:
            continue

        bin_acc = y_true[mask].mean()   # observed positive rate
        bin_conf = y_prob[mask].mean()  # mean predicted probability
        ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return float(ece)


def calculate_classwise_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 20,
) -> float:
    """
    Calculate classwise ECE as used in Walsh & Joshi (2024).

    Computes ECE independently for each class (positive and negative),
    then averages. This catches miscalibration that standard ECE can miss
    in imbalanced datasets (common in sports — home teams win ~58% in NBA).

    classwise-ECE = (ECE_positive + ECE_negative) / 2

    Args:
        y_true: Binary ground truth labels (0 or 1).
        y_prob: Predicted probability for positive class.
        n_bins: Number of bins (default 20).

    Returns:
        Classwise ECE score in [0, 1].
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    # ECE for positive class (P(y=1))
    ece_pos = calculate_ece(y_true, y_prob, n_bins)

    # ECE for negative class (P(y=0))
    ece_neg = calculate_ece(1 - y_true, 1 - y_prob, n_bins)

    return (ece_pos + ece_neg) / 2


def calibration_report(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 20,
    label: str = "Model",
) -> dict:
    """
    Generate a full calibration report with per-bin breakdown.

    Args:
        y_true: Binary ground truth labels.
        y_prob: Predicted probabilities.
        n_bins: Number of bins.
        label: Name for this model/evaluation.

    Returns:
        Dict with keys: label, ece, classwise_ece, n_samples, bins (list of
        dicts with lo, hi, count, mean_predicted, mean_actual, gap).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins = []

    for i in range(n_bins):
        lo, hi = float(bin_edges[i]), float(bin_edges[i + 1])
        if i < n_bins - 1:
            mask = (y_prob >= lo) & (y_prob < hi)
        else:
            mask = (y_prob >= lo) & (y_prob <= hi)

        count = int(mask.sum())
        if count == 0:
            bins.append(dict(lo=lo, hi=hi, count=0, mean_predicted=None, mean_actual=None, gap=None))
        else:
            mp = float(y_prob[mask].mean())
            ma = float(y_true[mask].mean())
            bins.append(dict(lo=lo, hi=hi, count=count, mean_predicted=round(mp, 4), mean_actual=round(ma, 4), gap=round(abs(mp - ma), 4)))

    return dict(
        label=label,
        ece=round(calculate_ece(y_true, y_prob, n_bins), 6),
        classwise_ece=round(calculate_classwise_ece(y_true, y_prob, n_bins), 6),
        n_samples=len(y_true),
        bins=bins,
    )


def print_calibration_report(report: dict) -> None:
    """Pretty-print a calibration report."""
    print(f"\n{'='*60}")
    print(f"  Calibration Report: {report['label']}")
    print(f"  Samples: {report['n_samples']}")
    print(f"  ECE:          {report['ece']:.4f}")
    print(f"  Classwise ECE: {report['classwise_ece']:.4f}")
    print(f"{'='*60}")
    print(f"  {'Bin':>10}  {'Count':>6}  {'Predicted':>10}  {'Actual':>8}  {'Gap':>6}")
    print(f"  {'-'*48}")
    for b in report['bins']:
        rng = f"[{b['lo']:.2f},{b['hi']:.2f})"
        if b['count'] == 0:
            print(f"  {rng:>10}  {0:>6}  {'—':>10}  {'—':>8}  {'—':>6}")
        else:
            print(f"  {rng:>10}  {b['count']:>6}  {b['mean_predicted']:>10.4f}  {b['mean_actual']:>8.4f}  {b['gap']:>6.4f}")
    print()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(42)

    # --- Test 1: perfectly calibrated model ---
    n = 10000
    y_prob_perfect = np.random.uniform(0, 1, n)
    y_true_perfect = (np.random.uniform(0, 1, n) < y_prob_perfect).astype(float)
    ece_perfect = calculate_ece(y_true_perfect, y_prob_perfect)
    print(f"[TEST] Perfect calibration ECE: {ece_perfect:.4f}  (expect ~0.00)")
    assert ece_perfect < 0.02, f"Perfect model ECE too high: {ece_perfect}"

    # --- Test 2: completely miscalibrated (always predicts 0.9, 50% true rate) ---
    y_prob_bad = np.full(1000, 0.9)
    y_true_bad = np.random.binomial(1, 0.5, 1000).astype(float)
    ece_bad = calculate_ece(y_true_bad, y_prob_bad)
    print(f"[TEST] Bad calibration ECE:     {ece_bad:.4f}  (expect ~0.40)")
    assert ece_bad > 0.3, f"Bad model ECE too low: {ece_bad}"

    # --- Test 3: classwise ECE ---
    cw_ece = calculate_classwise_ece(y_true_perfect, y_prob_perfect)
    print(f"[TEST] Classwise ECE (perfect): {cw_ece:.4f}  (expect ~0.00)")
    assert cw_ece < 0.02

    # --- Test 4: sports betting scenario ---
    # Simulate a model predicting NBA game outcomes
    n_games = 500
    # True home-win rate ~58%
    true_probs = np.clip(np.random.normal(0.58, 0.12, n_games), 0.05, 0.95)
    outcomes = (np.random.uniform(0, 1, n_games) < true_probs).astype(float)
    # Model predictions: slightly noisy version of truth (decent model)
    pred_probs = np.clip(true_probs + np.random.normal(0, 0.05, n_games), 0.01, 0.99)

    report = calibration_report(outcomes, pred_probs, label="NBA Home Win Model")
    print_calibration_report(report)

    print("[TEST] All tests passed ✓")
