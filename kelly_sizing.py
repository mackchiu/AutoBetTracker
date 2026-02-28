#!/usr/bin/env python3
"""
Fractional Kelly Bet Sizing

Based on Walsh & Joshi (2024) findings:
- Full Kelly maximizes growth but has high variance/risk of ruin
- 1/5 Kelly achieved 98% ROI with much lower drawdown
- We default to 1/10 Kelly for conservative bankroll management

Kelly formula: f* = (p*b - q) / b
Where: p = probability of winning, b = decimal odds - 1, q = 1 - p
"""

from typing import Optional, Tuple


def kelly_fraction(model_prob: float, odds: float, fraction: float = 0.1) -> float:
    """
    Calculate fractional Kelly criterion bet size as % of bankroll.

    Args:
        model_prob: Model's estimated win probability (0 to 1)
        odds: Decimal odds (e.g., 1.91 for -110)
        fraction: Kelly fraction (0.1 = 1/10 Kelly, 0.2 = 1/5 Kelly)

    Returns:
        Fraction of bankroll to bet (0 to 1). Returns 0 if no edge.
    """
    if model_prob <= 0 or model_prob >= 1 or odds <= 1:
        return 0.0

    b = odds - 1  # net odds (profit per $1 wagered)
    q = 1 - model_prob
    kelly = (model_prob * b - q) / b

    if kelly <= 0:
        return 0.0  # No edge — don't bet

    return min(fraction * kelly, 1.0)


def kelly_units(
    model_prob: float,
    odds: float,
    bankroll: float,
    unit_size: float = 100.0,
    max_bet: float = 0.05,
    fraction: float = 0.1,
) -> float:
    """
    Calculate bet size in units based on Kelly criterion.

    Args:
        model_prob: Model's estimated win probability (0 to 1)
        odds: Decimal odds (e.g., 1.91)
        bankroll: Current bankroll in dollars
        unit_size: Dollar value of 1 unit (default $100)
        max_bet: Maximum bet as fraction of bankroll (default 5%)
        fraction: Kelly fraction (default 1/10)

    Returns:
        Number of units to bet (e.g., 0.5, 1.0, 2.3). Returns 0 if no edge.
    """
    if bankroll <= 0 or unit_size <= 0:
        return 0.0

    kelly_pct = kelly_fraction(model_prob, odds, fraction)
    bet_pct = min(kelly_pct, max_bet)
    bet_dollars = bet_pct * bankroll
    units = round(bet_dollars / unit_size, 2)

    return max(units, 0.0)


def grade_adjusted_units(
    grade: str,
    model_prob: float,
    odds: float,
    bankroll: float,
    unit_size: float = 100.0,
    max_bet: float = 0.05,
    fraction: float = 0.1,
) -> float:
    """
    Kelly units adjusted by pick grade.

    A-grade: full Kelly calculation
    B-grade: Kelly * 0.5
    C-grade: 0 units (paper only)

    Returns:
        Units to bet.
    """
    if grade.upper() == 'C':
        return 0.0

    units = kelly_units(model_prob, odds, bankroll, unit_size, max_bet, fraction)

    if grade.upper() == 'B':
        units = round(units * 0.5, 2)

    return units


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds."""
    if american > 0:
        return 1 + american / 100
    else:
        return 1 + 100 / abs(american)


def implied_probability(odds: float) -> float:
    """Implied probability from decimal odds (no vig removal)."""
    if odds <= 1:
        return 1.0
    return 1.0 / odds


def edge_pct(model_prob: float, odds: float) -> float:
    """Calculate edge as percentage over implied probability."""
    implied = implied_probability(odds)
    return round((model_prob - implied) * 100, 2)


# --- Usage examples ---
if __name__ == '__main__':
    print("=== Fractional Kelly Sizing Examples ===\n")

    bankroll = 5000
    unit = 100

    examples = [
        ("Strong edge", 0.60, 1.91),   # -110 line, model says 60%
        ("Moderate edge", 0.55, 1.91),  # -110 line, model says 55%
        ("Slight edge", 0.53, 1.91),    # -110 line, model says 53%
        ("No edge", 0.50, 1.91),        # No edge
        ("Plus odds edge", 0.45, 2.50), # +150, model says 45%
    ]

    for label, prob, odds in examples:
        implied = implied_probability(odds)
        full_kelly = kelly_fraction(prob, odds, fraction=1.0)
        tenth_kelly = kelly_fraction(prob, odds, fraction=0.1)
        units_a = grade_adjusted_units('A', prob, odds, bankroll, unit)
        units_b = grade_adjusted_units('B', prob, odds, bankroll, unit)

        print(f"{label}: p={prob:.0%}, odds={odds}, implied={implied:.1%}")
        print(f"  Full Kelly: {full_kelly:.3%} | 1/10 Kelly: {tenth_kelly:.3%}")
        print(f"  A-grade: {units_a}u | B-grade: {units_b}u | C-grade: 0u")
        print(f"  Edge: {edge_pct(prob, odds)}%\n")
