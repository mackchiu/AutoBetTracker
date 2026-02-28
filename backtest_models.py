import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss

DB_PATH = '/data/.openclaw/workspace/data/nba.db'
SEASONS_TRAIN = [2020, 2021, 2022]
SEASON_TEST = 2024
LAST_N_GAMES = 10


def fetch_games(conn, seasons):
    sql = f'''SELECT id as game_id, date, season, home_team_id, visitor_team_id as away_team_id, home_team_score, visitor_team_score as away_team_score, status FROM games WHERE season in ({','.join(str(s) for s in seasons)}) ORDER BY date ASC'''
    return pd.read_sql_query(sql, conn)

def fetch_player_stats(conn, game_ids):
    sql = f'''SELECT * FROM player_stats WHERE game_id in ({','.join(str(int(g)) for g in game_ids)})'''
    return pd.read_sql_query(sql, conn)

def fetch_team_game_stats(conn, game_ids):
    sql = f'''SELECT * FROM team_game_stats WHERE game_id in ({','.join(str(int(g)) for g in game_ids)})'''
    return pd.read_sql_query(sql, conn)

def rolling_team_averages(player_stats, games, stat_cols):
    # Calculate rolling averages of last N games for every team for each game
    result = []
    games_sorted = games.sort_values('date')
    for ix, row in games_sorted.iterrows():
        for side in ['home', 'away']:
            tid = row[f'{side}_team_id']
            gid = row['game_id']
            ctime = row['date']
            mask = (player_stats['team_id'] == tid) & (player_stats['date'] < ctime)
            ps = player_stats[mask].sort_values('date').tail(LAST_N_GAMES)
            res_row = {'game_id': gid, 'side': side, 'team_id': tid}
            for stat in stat_cols:
                if stat == 'fg_pct':
                    if ps['fga'].sum() > 0:
                        res_row[stat] = ps['fgm'].sum() / ps['fga'].sum() * 100
                    else:
                        res_row[stat] = np.nan
                else:
                    res_row[stat] = ps[stat].mean() if not ps.empty else np.nan
            result.append(res_row)
    return pd.DataFrame(result)

def get_opponent_avg_pts_allowed(team_stats, games):
    # For each team, figure out how many points they usually give up
    piv = team_stats.pivot_table(index=['team_id', 'game_id'], values=['pts_allowed'], aggfunc='first').reset_index()
    return piv.groupby('team_id')['pts_allowed'].mean().to_dict()

def build_features(conn, games, player_stats, team_game_stats, mode):
    features = []
    for ix, row in games.iterrows():
        record = {'game_id': row['game_id'], 'home_team_id': row['home_team_id'], 'away_team_id': row['away_team_id'],
                  'home_team_win': 1 if row['home_team_score'] > row['away_team_score'] else 0}
        if mode == 1:  # Raw stats
            for side, tid in [('home', row['home_team_id']), ('away', row['away_team_id'])]:
                mask = (player_stats['team_id'] == tid) & (player_stats['game_id'].isin(games[games['date'] < row['date']]['game_id']))
                ps = player_stats[mask].tail(LAST_N_GAMES * 5)  # Approx last N games (5 players per team)
                record[f'{side}_avg_pts'] = ps['pts'].mean() if not ps.empty else np.nan
                record[f'{side}_avg_reb'] = ps['reb'].mean() if not ps.empty else np.nan
                record[f'{side}_avg_ast'] = ps['ast'].mean() if not ps.empty else np.nan
                fga_sum = ps['fga'].sum()
                record[f'{side}_fg_pct'] = ps['fgm'].sum() / fga_sum * 100 if fga_sum > 0 else np.nan
        elif mode == 2:  # Outperformance (FIXED - no data leakage)
            # Use ONLY historical data (before current game date)
            for side, tid, opp_tid in [
                ('home', row['home_team_id'], row['away_team_id']),
                ('away', row['away_team_id'], row['home_team_id'])]:
                # Team's rolling avg points scored BEFORE this game
                team_prev_games = team_game_stats[(team_game_stats['team_id'] == tid) & (team_game_stats['date'] < row['date'])]
                avg_pts_scored = team_prev_games['points_scored'].tail(LAST_N_GAMES).mean() if not team_prev_games.empty else np.nan
                # Opponent's avg points allowed BEFORE this game
                opp_prev_games = team_game_stats[(team_game_stats['team_id'] == opp_tid) & (team_game_stats['date'] < row['date'])]
                avg_pts_allowed = opp_prev_games['points_allowed'].tail(LAST_N_GAMES).mean() if not opp_prev_games.empty else np.nan
                record[f'{side}_outperformance_pts'] = avg_pts_scored - avg_pts_allowed if not np.isnan(avg_pts_scored) and not np.isnan(avg_pts_allowed) else np.nan
        features.append(record)
    fdf = pd.DataFrame(features).dropna()
    return fdf

def bet_roi(y_true, y_prob, odds_dict=None, margin=0.025, kelly_frac=0.1):
    """
    Value-based betting with Kelly sizing.

    Args:
        y_true: array of 1 (home win) / 0 (away win)
        y_prob: array of model P(home win)
        odds_dict: dict mapping game index -> {'home': decimal_odds, 'away': decimal_odds}
                   If None, uses default -110 (1.909) for both sides.
        margin: required edge above implied prob (default 2.5% = half the ~5% vig)
        kelly_frac: Kelly fraction (default 1/10)

    Returns:
        (roi, num_bets, avg_edge)
    """
    from kelly_sizing import kelly_fraction as kf, implied_probability

    default_odds = 1 + 100 / 110  # ~1.909 for -110

    total_wagered = 0.0
    total_pnl = 0.0
    edges = []

    for i, (yt, yp) in enumerate(zip(y_true, y_prob)):
        home_odds = odds_dict[i]['home'] if odds_dict and i in odds_dict else default_odds
        away_odds = odds_dict[i]['away'] if odds_dict and i in odds_dict else default_odds

        model_home_prob = yp
        model_away_prob = 1.0 - yp

        implied_home = implied_probability(home_odds)
        implied_away = implied_probability(away_odds)

        # Check value on home side
        home_edge = model_home_prob - implied_home
        if home_edge > margin:
            stake = kf(model_home_prob, home_odds, fraction=kelly_frac)
            if stake > 0:
                profit = stake * (home_odds - 1) if yt == 1 else -stake
                total_wagered += stake
                total_pnl += profit
                edges.append(home_edge)

        # Check value on away side
        away_edge = model_away_prob - implied_away
        if away_edge > margin:
            stake = kf(model_away_prob, away_odds, fraction=kelly_frac)
            if stake > 0:
                profit = stake * (away_odds - 1) if yt == 0 else -stake
                total_wagered += stake
                total_pnl += profit
                edges.append(away_edge)

    num_bets = len(edges)
    roi = total_pnl / total_wagered if total_wagered > 0 else 0.0
    avg_edge = np.mean(edges) if edges else 0.0
    return roi, num_bets, avg_edge


def run_model(mode, conn, games_train, games_test, player_stats, team_game_stats):
    feat_train = build_features(conn, games_train, player_stats, team_game_stats, mode)
    feat_test = build_features(conn, games_test, player_stats, team_game_stats, mode)

    X_train = feat_train.drop(['game_id','home_team_id','away_team_id','home_team_win'],axis=1)
    y_train = feat_train['home_team_win']
    X_test = feat_test.drop(['game_id','home_team_id','away_team_id','home_team_win'],axis=1)
    y_test = feat_test['home_team_win']

    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob > 0.5).astype(int)
    acc = accuracy_score(y_test, y_pred)
    brier = brier_score_loss(y_test, y_prob)
    roi, n_bets, avg_edge = bet_roi(y_test.values, y_prob)
    return acc, brier, roi, n_bets, avg_edge


def main():
    conn = sqlite3.connect(DB_PATH)
    games_train = fetch_games(conn, SEASONS_TRAIN)
    games_test = fetch_games(conn, [SEASON_TEST])
    all_gids = pd.concat([games_train, games_test])['game_id'].unique()
    player_stats = fetch_player_stats(conn, all_gids)
    team_game_stats = fetch_team_game_stats(conn, all_gids)

    results = {}
    for mode in [1,2]:
        acc, brier, roi, n_bets, avg_edge = run_model(mode, conn, games_train, games_test, player_stats, team_game_stats)
        results[mode] = {'acc': acc, 'brier': brier, 'roi': roi, 'bets': n_bets, 'avg_edge': avg_edge}

    print("Model Backtest Results (2020-2022 train, 2024 test):")
    for mode, label in zip([1,2],["Raw Stats","Out-Performance"]):
        res = results[mode]
        print(f"{label}\n  Accuracy: {res['acc']:.3f}\n  Brier Score: {res['brier']:.3f}\n  ROI: {res['roi']:.3f} ({res['bets']} bets)\n  Avg Edge: {res['avg_edge']:.3f}")

if __name__ == "__main__":
    main()
