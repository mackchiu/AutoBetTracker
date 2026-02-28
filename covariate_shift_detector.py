"""
Covariate Shift Detection System

Detects when feature distributions shift over time using the two-sample
Kolmogorov-Smirnov test, per Walsh & Joshi (2024) Section 5.

Sports data exhibits covariate shift from rule changes, roster turnover,
and meta-game evolution. Detecting shift is critical for model robustness.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class FeatureDriftResult:
    """Result of a KS test on a single feature."""
    feature: str
    ks_statistic: float
    p_value: float
    shifted: bool
    train_mean: float
    train_std: float
    test_mean: float
    test_std: float

    @property
    def mean_delta(self) -> float:
        return self.test_mean - self.train_mean

    @property
    def effect_size(self) -> float:
        """Cohen's d between the two distributions."""
        pooled_std = np.sqrt((self.train_std**2 + self.test_std**2) / 2)
        if pooled_std == 0:
            return 0.0
        return abs(self.mean_delta) / pooled_std


@dataclass
class DriftReport:
    """Aggregated drift report across all features."""
    results: List[FeatureDriftResult] = field(default_factory=list)
    alpha: float = 0.01

    @property
    def shifted_features(self) -> List[str]:
        return [r.feature for r in self.results if r.shifted]

    @property
    def stable_features(self) -> List[str]:
        return [r.feature for r in self.results if not r.shifted]

    @property
    def shift_ratio(self) -> float:
        if not self.results:
            return 0.0
        return len(self.shifted_features) / len(self.results)

    def summary(self) -> str:
        lines = [
            f"Drift Report (alpha={self.alpha})",
            f"  Features tested: {len(self.results)}",
            f"  Shifted: {len(self.shifted_features)} ({self.shift_ratio:.1%})",
            f"  Stable:  {len(self.stable_features)}",
        ]
        if self.shifted_features:
            lines.append("  Shifted features:")
            for r in self.results:
                if r.shifted:
                    lines.append(
                        f"    - {r.feature}: KS={r.ks_statistic:.4f}, "
                        f"p={r.p_value:.2e}, effect_size={r.effect_size:.3f}"
                    )
        return "\n".join(lines)

    def recommendation(self) -> str:
        if not self.shifted_features:
            return "No significant drift detected. Model is likely still valid."
        severe = [r for r in self.results if r.shifted and r.effect_size > 0.5]
        moderate = [r for r in self.results if r.shifted and r.effect_size <= 0.5]
        lines = []
        if severe:
            lines.append(
                f"DROP or re-engineer ({len(severe)} features with large effect): "
                + ", ".join(r.feature for r in severe)
            )
        if moderate:
            lines.append(
                f"MONITOR ({len(moderate)} features with moderate drift): "
                + ", ".join(r.feature for r in moderate)
            )
        if self.shift_ratio > 0.3:
            lines.append("RETRAIN recommended — >30% of features have shifted.")
        return "\n".join(lines)


def detect_shift(
    train_data: Union[pd.DataFrame, np.ndarray],
    test_data: Union[pd.DataFrame, np.ndarray],
    features: List[str],
    alpha: float = 0.01,
) -> DriftReport:
    """
    Compare distribution of each feature between train and test sets
    using the two-sample Kolmogorov-Smirnov test.

    Args:
        train_data: Training set (DataFrame or ndarray with columns matching features).
        test_data: Test/recent set.
        features: List of feature names to test.
        alpha: Significance level (default 0.01 per Walsh & Joshi 2024).

    Returns:
        DriftReport with per-feature KS results.
    """
    if isinstance(train_data, np.ndarray):
        train_data = pd.DataFrame(train_data, columns=features)
    if isinstance(test_data, np.ndarray):
        test_data = pd.DataFrame(test_data, columns=features)

    report = DriftReport(alpha=alpha)

    for feat in features:
        train_vals = train_data[feat].dropna().values
        test_vals = test_data[feat].dropna().values

        if len(train_vals) < 2 or len(test_vals) < 2:
            continue

        ks_stat, p_value = stats.ks_2samp(train_vals, test_vals)

        report.results.append(FeatureDriftResult(
            feature=feat,
            ks_statistic=ks_stat,
            p_value=p_value,
            shifted=p_value < alpha,
            train_mean=float(np.mean(train_vals)),
            train_std=float(np.std(train_vals, ddof=1)),
            test_mean=float(np.mean(test_vals)),
            test_std=float(np.std(test_vals, ddof=1)),
        ))

    return report


def check_feature_drift(
    historical_csv: str,
    recent_csv: str,
    features: List[str],
    alpha: float = 0.01,
) -> DriftReport:
    """
    Load two CSV files and run KS drift detection on specified features.

    Args:
        historical_csv: Path to historical/training data CSV.
        recent_csv: Path to recent/incoming data CSV.
        features: Feature column names to test.
        alpha: Significance level.

    Returns:
        DriftReport with recommendations.
    """
    hist_df = pd.read_csv(historical_csv)
    recent_df = pd.read_csv(recent_csv)

    missing_hist = [f for f in features if f not in hist_df.columns]
    missing_recent = [f for f in features if f not in recent_df.columns]
    if missing_hist:
        raise ValueError(f"Features missing from historical CSV: {missing_hist}")
    if missing_recent:
        raise ValueError(f"Features missing from recent CSV: {missing_recent}")

    return detect_shift(hist_df, recent_df, features, alpha=alpha)


def should_retrain_model(drift_report: DriftReport, threshold: float = 0.1) -> bool:
    """
    Returns True if more than `threshold` fraction of features have shifted.

    Args:
        drift_report: Output from detect_shift or check_feature_drift.
        threshold: Fraction of shifted features that triggers retrain (default 10%).
    """
    return drift_report.shift_ratio > threshold


# ---------------------------------------------------------------------------
# CLI / demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys, os

    def demo():
        """Run a quick demo with synthetic sports data."""
        np.random.seed(42)
        n_train, n_test = 500, 100
        features = [
            "avg_point_diff", "win_pct_last10", "pace", "three_pt_rate",
            "opp_strength", "rest_days", "home_court_adv",
        ]

        # Simulate training data (e.g. 2022-23 season)
        train = pd.DataFrame({
            "avg_point_diff": np.random.normal(0, 5, n_train),
            "win_pct_last10": np.random.beta(5, 5, n_train),
            "pace":           np.random.normal(98, 3, n_train),
            "three_pt_rate":  np.random.normal(0.36, 0.04, n_train),
            "opp_strength":   np.random.normal(0, 1, n_train),
            "rest_days":      np.random.poisson(1.5, n_train).astype(float),
            "home_court_adv": np.random.normal(3.0, 1.0, n_train),
        })

        # Simulate recent data with drift in pace and three_pt_rate
        # (rule change increased pace; league-wide 3pt shift)
        test = pd.DataFrame({
            "avg_point_diff": np.random.normal(0, 5, n_test),          # stable
            "win_pct_last10": np.random.beta(5, 5, n_test),            # stable
            "pace":           np.random.normal(102, 3, n_test),        # SHIFTED +4
            "three_pt_rate":  np.random.normal(0.40, 0.04, n_test),   # SHIFTED +0.04
            "opp_strength":   np.random.normal(0, 1, n_test),          # stable
            "rest_days":      np.random.poisson(1.5, n_test).astype(float),  # stable
            "home_court_adv": np.random.normal(3.0, 1.0, n_test),     # stable
        })

        report = detect_shift(train, test, features, alpha=0.01)
        print(report.summary())
        print()
        print("Recommendation:")
        print(report.recommendation())
        print()
        print(f"Should retrain (>10% drift)? {should_retrain_model(report)}")
        return report

    parser = argparse.ArgumentParser(description="Covariate shift detection")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("demo", help="Run synthetic demo")

    csv_p = sub.add_parser("check", help="Check drift between two CSVs")
    csv_p.add_argument("historical", help="Path to historical CSV")
    csv_p.add_argument("recent", help="Path to recent CSV")
    csv_p.add_argument("--features", nargs="+", required=True)
    csv_p.add_argument("--alpha", type=float, default=0.01)

    args = parser.parse_args()

    if args.cmd == "demo":
        demo()
    elif args.cmd == "check":
        report = check_feature_drift(
            args.historical, args.recent, args.features, alpha=args.alpha
        )
        print(report.summary())
        print()
        print("Recommendation:")
        print(report.recommendation())
        print(f"\nShould retrain? {should_retrain_model(report)}")
    else:
        parser.print_help()
