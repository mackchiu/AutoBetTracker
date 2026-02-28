#!/usr/bin/env python3
"""
Out-Performance Features for NBA Prediction

Based on Walsh & Joshi (2024): "average out-performance vs opponents"
is more predictive than raw stats and less prone to covariate shift.

Out-performance = team_stat - opponent_avg_allowed_stat
This normalizes for opponent strength and league-wide trends.
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple
import statistics

DB_PATH = os.environ.get('NBA_DB_PATH', '/data/.openclaw/workspace/data/nba.db')

# Key stats for out-performance features
# Maps friendly name -> actual column in team_game_stats
STAT_COLUMNS = {
    'ortg': 'ortg',
    'drtg': 'drtg',
    'efg_pct': 'efg_pct',
    'oreb_pct': 'oreb_pct',
    'ftr': 'ftr',
    'points_scored': 'points_scored',
    'possessions': 'possessions',
    'opp_efg_pct': 'opp_efg_pct',
}
STATS = list(STAT_COLUMNS.keys())


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def calculate_outperformance(
    team_id: str,
    stat: str,
    games_lookback: int = 10,
    db_conn=None
) -> Optional[float]:
    """
    Calculate a team's average out-performance for a given stat.

    For each of the last N games:
        op = team_stat_in_game - opponent_season_avg_allowed_for_that_stat

    Args:
        team_id: Team abbreviation (e.g., 'BOS', 'LAL')
        stat: Stat column name (e.g., 'offensive_rating', 'pace')
        games_lookback: Number of recent games to average over
        db_conn: Optional existing DB connection

    Returns:
        Average out-performance, or None if insufficient data.
    """
    conn = db_conn or get_db()
    close_conn = db_conn is None

    try:
        cursor = conn.cursor()

        col = STAT_COLUMNS.get(stat, stat)

        # Get last N games for this team with their opponent
        cursor.execute(f"""
            SELECT ts.game_id, ts.date, ts.{col} as team_stat, ts.opponent_id as opponent
            FROM team_game_stats ts
            WHERE ts.team_id = ?
            ORDER BY ts.date DESC
            LIMIT ?
        """, (team_id, games_lookback))

        games = cursor.fetchall()
        if not games:
            return None

        op_values = []
        for game_id, game_date, team_stat, opponent in games:
            if team_stat is None:
                continue

            # Get opponent's average allowed stat (what opposing teams score against them)
            cursor.execute(f"""
                SELECT AVG(opp_ts.{col}) as avg_allowed
                FROM team_game_stats opp_ts
                WHERE opp_ts.opponent_id = ?
                  AND opp_ts.date < ?
            """, (opponent, game_date))

            row = cursor.fetchone()
            if row and row[0] is not None:
                opp_avg_allowed = row[0]
                op_values.append(team_stat - opp_avg_allowed)

        if not op_values:
            return None

        return round(statistics.mean(op_values), 3)

    except Exception as e:
        print(f"Error calculating outperformance for {team_id}/{stat}: {e}")
        return None
    finally:
        if close_conn:
            conn.close()


def generate_op_features(
    home_team: str,
    away_team: str,
    games_lookback: int = 10,
    db_conn=None
) -> Dict[str, Optional[float]]:
    """
    Generate out-performance feature dict for an upcoming game.

    Args:
        home_team: Home team abbreviation
        away_team: Away team abbreviation
        games_lookback: Lookback window

    Returns:
        Dict of feature_name -> value, e.g.:
        {
            'home_op_pace': 1.2,
            'home_op_offensive_rating': 3.5,
            'away_op_defensive_rating': -2.1,
            ...
        }
    """
    conn = db_conn or get_db()
    close_conn = db_conn is None

    try:
        features = {}
        for stat in STATS:
            features[f'home_op_{stat}'] = calculate_outperformance(
                home_team, stat, games_lookback, conn
            )
            features[f'away_op_{stat}'] = calculate_outperformance(
                away_team, stat, games_lookback, conn
            )

        # Derived differential features
        for stat in STATS:
            h = features.get(f'home_op_{stat}')
            a = features.get(f'away_op_{stat}')
            if h is not None and a is not None:
                features[f'diff_op_{stat}'] = round(h - a, 3)
            else:
                features[f'diff_op_{stat}'] = None

        return features

    finally:
        if close_conn:
            conn.close()


def get_raw_stat_avg(team_id: str, stat: str, games_lookback: int = 10, db_conn=None) -> Optional[float]:
    """Get simple rolling average of a raw stat."""
    conn = db_conn or get_db()
    close_conn = db_conn is None
    try:
        col = STAT_COLUMNS.get(stat, stat)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT AVG(sub.val)
            FROM (
                SELECT ts.{col} as val
                FROM team_game_stats ts
                WHERE ts.team_id = ?
                ORDER BY ts.date DESC
                LIMIT ?
            ) sub
        """, (team_id, games_lookback))
        row = cursor.fetchone()
        return round(row[0], 3) if row and row[0] is not None else None
    finally:
        if close_conn:
            conn.close()


def op_vs_raw_comparison(
    team_id: str,
    stat: str,
    games_lookback: int = 10,
    db_conn=None
) -> Dict:
    """
    Compare raw stat average vs out-performance metric.

    Returns dict with both values and context about which
    is more informative (out-performance adjusts for opponent quality).
    """
    conn = db_conn or get_db()
    close_conn = db_conn is None

    try:
        raw = get_raw_stat_avg(team_id, stat, games_lookback, conn)
        op = calculate_outperformance(team_id, stat, games_lookback, conn)

        result = {
            'team': team_id,
            'stat': stat,
            'lookback': games_lookback,
            'raw_avg': raw,
            'outperformance': op,
            'interpretation': None
        }

        if op is not None:
            if op > 0:
                result['interpretation'] = (
                    f"{team_id} outperforms opponents by {op:.1f} in {stat} "
                    f"(raw avg: {raw}). Positive OP = better than opponent quality suggests."
                )
            else:
                result['interpretation'] = (
                    f"{team_id} underperforms by {abs(op):.1f} in {stat} "
                    f"(raw avg: {raw}). Negative OP = worse than opponent quality suggests."
                )

        return result

    finally:
        if close_conn:
            conn.close()


# --- Usage examples ---
if __name__ == '__main__':
    print("=== Out-Performance Feature Examples ===\n")

    # Get two sample team IDs
    import sqlite3 as _sq
    conn = _sq.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT team_id FROM team_game_stats LIMIT 2")
    teams = [r[0] for r in cur.fetchall()]
    conn.close()

    if len(teams) < 2:
        print("Not enough teams in DB for demo")
    else:
        home, away = teams[0], teams[1]
        print(f"Generating OP features for team {home} vs team {away}...\n")
        features = generate_op_features(home, away)
        for k, v in sorted(features.items()):
            print(f"  {k}: {v}")

        print(f"\n--- Raw vs OP comparison (team {home}, ortg) ---")
        comp = op_vs_raw_comparison(home, 'ortg')
        print(f"  Raw avg: {comp['raw_avg']}")
        print(f"  Out-performance: {comp['outperformance']}")
        if comp['interpretation']:
            print(f"  {comp['interpretation']}")
