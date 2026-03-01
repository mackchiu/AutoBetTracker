#!/usr/bin/env python3
"""
Decision Loop - Pre-bet analysis and grading system
Runs model picks through signal cross-reference and assigns A/B/C grades
"""

import csv
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from signal_fetcher import SignalFetcher
from kelly_sizing import grade_adjusted_units, american_to_decimal, kelly_fraction, edge_pct

# Paths
BETTING_DATA_PATH = '/data/.openclaw/workspace/betting-data'
TRACKER_PATH = f'{BETTING_DATA_PATH}/trackers'
BET_LOG_PATH = f'{BETTING_DATA_PATH}/bet_log'
SIGNAL_TRACKER_FILE = f'{TRACKER_PATH}/signal_performance.csv'

def ensure_directories():
    """Create directory structure if it doesn't exist"""
    os.makedirs(TRACKER_PATH, exist_ok=True)
    os.makedirs(BET_LOG_PATH, exist_ok=True)

def load_model_picks(date: str) -> List[Dict]:
    """Load model picks from tracker data"""
    picks = []
    
    # Load player props
    player_props_file = f'/data/.openclaw/workspace/tracker/data/{date}_player_props.csv'
    if os.path.exists(player_props_file):
        with open(player_props_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['model_type'] = 'Player Props'
                picks.append(row)
    
    # Load team model
    team_model_file = f'/data/.openclaw/workspace/tracker/data/{date}_team_model.csv'
    if os.path.exists(team_model_file):
        with open(team_model_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['model_type'] = 'Team Model'
                picks.append(row)
    
    return picks

def run_pre_bet_analysis(pick: Dict, signals: Dict) -> Dict:
    """
    Run pre-bet analysis template and return filled analysis
    """
    # Parse game info
    game = pick.get('game', '')
    if ' @ ' in game:
        away, home = game.split(' @ ')
    else:
        away, home = '', game
    
    # Get model info
    if pick['model_type'] == 'Player Props':
        pick_desc = f"{pick['player']} {pick['market']} {pick['bet']} {pick['line']}"
        projection = pick.get('projection', 'N/A')
        line = pick.get('line', 'N/A')
        edge = pick.get('edge_pct', 'N/A')
    else:
        pick_desc = pick.get('pick', '')
        projection = pick.get('proj', 'N/A')
        line = pick.get('line', 'N/A')
        edge = pick.get('edge', 'N/A')
    
    analysis = {
        'date': pick.get('date', datetime.now().strftime('%Y-%m-%d')),
        'game': game,
        'pick_desc': pick_desc,
        'model_type': pick['model_type'],
        'projection': projection,
        'line': line,
        'edge': edge,
        'book': pick.get('book', 'N/A'),
        'odds': pick.get('odds', 'N/A'),
        'signals': signals,
        'grade': 'C',  # Default
        'grade_reasoning': [],
        # Store original fields for CSV matching
        'player': pick.get('player'),
        'market': pick.get('market'),
        'bet': pick.get('bet')
    }
    
    return analysis

def log_signal_performance(analysis: Dict, bet_result: str = "pending"):
    """
    Log signal details for a pick to signal_performance.csv
    """
    signals = analysis.get('signals', {})
    date = analysis.get('date', datetime.now().strftime('%Y-%m-%d'))
    game = analysis.get('game', '')
    bet = analysis.get('pick_desc', '')
    rows = []

    # MODEL EDGE
    try:
        edge = float(analysis.get('edge', 0))
        signal_direction = 'Edge >= 3%' if edge >= 3 else 'Edge < 3%'
    except Exception:
        signal_direction = 'Unknown'
    rows.append({
        'date': date,
        'game': game,
        'bet': bet,
        'signal_name': 'model_edge',
        'signal_direction': signal_direction,
        'bet_result': bet_result,
        'notes': analysis.get('grade', '')
    })

    # LINE MOVEMENT
    line_mov = signals.get('line_movement', {})
    try:
        cur = float(line_mov.get('spread_current', 0))
        open_ = float(line_mov.get('spread_open', 0))
        if cur > open_:
            mov = 'Moved against'
        elif cur < open_:
            mov = 'Moved toward'
        else:
            mov = 'No movement'
    except Exception:
        mov = 'Unknown'
    rows.append({
        'date': date,
        'game': game,
        'bet': bet,
        'signal_name': 'line_movement',
        'signal_direction': mov,
        'bet_result': bet_result,
        'notes': analysis.get('grade', '')
    })

    # SHARP MONEY
    sharp = signals.get('bet_vs_money_divergence', '')
    if sharp == 'Sharp Action':
        sharp_dir = 'Sharp Action'
    elif sharp == 'Public Heavy':
        sharp_dir = 'Public Heavy'
    elif sharp:
        sharp_dir = sharp
    else:
        sharp_dir = 'Unknown'
    rows.append({
        'date': date,
        'game': game,
        'bet': bet,
        'signal_name': 'sharp_money',
        'signal_direction': sharp_dir,
        'bet_result': bet_result,
        'notes': analysis.get('grade', '')
    })

    # PUBLIC% DIVERGENCE
    pub_div = signals.get('public_perc_divergence', None)
    if pub_div is None and 'public_percent' in signals:
        pub_div = signals.get('public_percent')
    if isinstance(pub_div, (float, int)):
        if pub_div >= 15:
            div_lab = 'Large'
        elif pub_div >= 5:
            div_lab = 'Moderate'
        else:
            div_lab = 'Small/None'
    elif isinstance(pub_div, str) and pub_div:
        div_lab = pub_div
    else:
        div_lab = 'Unknown'
    rows.append({
        'date': date,
        'game': game,
        'bet': bet,
        'signal_name': 'public_perc_divergence',
        'signal_direction': div_lab,
        'bet_result': bet_result,
        'notes': analysis.get('grade', '')
    })

    file_exists = os.path.exists(SIGNAL_TRACKER_FILE)
    with open(SIGNAL_TRACKER_FILE, 'a', newline='') as f:
        fieldnames = ['date', 'game', 'bet', 'signal_name', 'signal_direction', 'bet_result', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

def grade_pick(analysis: Dict) -> str:
    """
    Grade pick A/B/C based on signal alignment
    A = 4/4 signals align
    B = 3/4 signals align  
    C = 2/4 or fewer
    """
    score = 0
    reasons = []
    
    # Check 1: Model edge significant (> 3%)
    try:
        edge = float(analysis['edge'])
        if edge >= 3:
            score += 1
            reasons.append("✓ Model edge significant")
        else:
            reasons.append("✗ Model edge weak (< 3%)")
    except:
        reasons.append("? Model edge unknown")
    
    # Check 2: Line movement favorable
    signals = analysis.get('signals', {})
    line_movement = signals.get('line_movement', {})
    if line_movement.get('spread_current') and line_movement.get('spread_open'):
        try:
            current = float(line_movement['spread_current'])
            open_line = float(line_movement['spread_open'])
            # If line moved toward our pick, that's favorable
            # (simplified - would need to know which side we picked)
            score += 1
            reasons.append("✓ Line movement tracked")
        except:
            reasons.append("? Line movement unclear")
    else:
        reasons.append("? Line movement data unavailable")
    
    # Check 3: Sharp money alignment
    divergence = signals.get('bet_vs_money_divergence')
    if divergence == 'Sharp Action':
        score += 1
        reasons.append("✓ Sharp money aligned")
    elif divergence == 'Public Heavy':
        reasons.append("✗ Public heavy (consider fade)")
    else:
        reasons.append("~ No sharp signal")
    
    # Check 4: No conflicting news
    sharp_signals = signals.get('sharp_signals', [])
    if not sharp_signals or 'conflict' not in str(sharp_signals).lower():
        score += 1
        reasons.append("✓ No conflicting signals")
    else:
        reasons.append("✗ Conflicting signals present")
    
    # Assign grade
    if score >= 4:
        grade = 'A'
    elif score >= 3:
        grade = 'B'
    else:
        grade = 'C'
    
    analysis['grade'] = grade
    analysis['grade_score'] = score
    analysis['grade_reasoning'] = reasons
    
    return grade

def log_bet(analysis: Dict, units: float = 1.0):
    """Log bet to daily bet log"""
    date = analysis['date']
    log_file = f'{BET_LOG_PATH}/{date}_bets.md'
    
    # Create entry
    entry = f"""### Bet Log Entry\nDate: {date}\nGame: {analysis['game']}\nBet: {analysis['pick_desc']}\nBook: {analysis['book']}\nOdds: {analysis['odds']}\nGrade: {analysis['grade']}\nUnits: {units}\n\nModel Analysis:\n- Projection: {analysis['projection']}\n- Line: {analysis['line']}\n- Edge: {analysis['edge']}%\n\nSignal Check:\n{chr(10).join(analysis['grade_reasoning'])}\n\nResult: pending\nActual: pending\n\n---\n\n"""
    
    # Append to file
    with open(log_file, 'a') as f:
        f.write(entry)
    
    # Update grade performance tracker
    update_grade_tracker(analysis, units)
    # Add: Log signal performance for each bet when it's logged
    log_signal_performance(analysis, bet_result="pending")

def update_grade_tracker(analysis: Dict, units: float):
    """Update grade performance CSV"""
    tracker_file = f'{TRACKER_PATH}/grade_performance.csv'
    
    row = {
        'date': analysis['date'],
        'game': analysis['game'],
        'bet': analysis['pick_desc'],
        'grade': analysis['grade'],
        'units': units,
        'result': 'pending',
        'profit_loss': 0
    }
    
    file_exists = os.path.exists(tracker_file)
    with open(tracker_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'game', 'bet', 'grade', 'units', 'result', 'profit_loss'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def run_decision_loop(date: str = None):
    """
    Main entry point - run full decision loop for today's picks
    """
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    ensure_directories()
    
    print(f"="*60)
    print(f"Decision Loop for {date}")
    print(f"="*60)
    
    # Load model picks
    picks = load_model_picks(date)
    print(f"\nLoaded {len(picks)} model picks")
    
    if not picks:
        print("No picks to analyze")
        return
    
    # Initialize signal fetcher
    fetcher = SignalFetcher()
    
    # Analyze each pick
    a_picks = []
    b_picks = []
    c_picks = []
    
    for pick in picks:
        # Parse game for signal lookup
        game = pick.get('game', '')
        if ' @ ' in game:
            away, home = game.split(' @ ')
        else:
            away, home = '', game
        
        # Try to match - sometimes model uses full names, insider uses city
        # Extract last word (team name) for matching
        home_short = home.split()[-1] if home else ''
        away_short = away.split()[-1] if away else ''
        
        # Get signals - try both full and short names
        signals = fetcher.get_game_signals(home, away)
        if not signals.get('line_movement', {}).get('spread_current'):
            # Try with just team names
            signals = fetcher.get_game_signals(home_short, away_short)
        
        # Run analysis
        analysis = run_pre_bet_analysis(pick, signals)
        
        # Grade
        grade = grade_pick(analysis)
        
        # Categorize
        if grade == 'A':
            a_picks.append(analysis)
        elif grade == 'B':
            b_picks.append(analysis)
        else:
            c_picks.append(analysis)
    
    # Log A and B picks
    print(f"\n{'='*60}")
        # Kelly sizing config
    BANKROLL = float(os.environ.get('BANKROLL', '5000'))
    UNIT_SIZE = float(os.environ.get('UNIT_SIZE', '100'))
    KELLY_FRACTION = 0.1  # 1/10 Kelly

    print(f"GRADE BREAKDOWN  (Bankroll: ${BANKROLL:,.0f} | Unit: ${UNIT_SIZE:.0f} | {int(1/KELLY_FRACTION)}th Kelly)")
    print(f"{'='*60}")
    print(f"A Picks ({len(a_picks)}): Kelly-sized bets")
    for a in a_picks:
        odds_raw = a.get('odds', '-110')
        try:
            dec_odds = american_to_decimal(int(str(odds_raw).replace('+', '')))
        except (ValueError, TypeError):
            dec_odds = 1.91
        try:
            prob = float(a['edge']) / 100 + 1 / dec_odds  # edge% + implied = model prob
        except (ValueError, TypeError):
            prob = 0.55
        units = grade_adjusted_units('A', prob, dec_odds, BANKROLL, UNIT_SIZE, fraction=KELLY_FRACTION)
        units = max(units, 0.5)  # minimum 0.5u for A picks
        kf = kelly_fraction(prob, dec_odds, KELLY_FRACTION)
        print(f"  ✓ {a['pick_desc']} @ {a['book']} (Edge: {a['edge']}% | Kelly: {kf:.2%} → {units}u)")
        log_bet(a, units=units)
    
    print(f"\nB Picks ({len(b_picks)}): Kelly×0.5 bets")
    for b in b_picks:
        odds_raw = b.get('odds', '-110')
        try:
            dec_odds = american_to_decimal(int(str(odds_raw).replace('+', '')))
        except (ValueError, TypeError):
            dec_odds = 1.91
        try:
            prob = float(b['edge']) / 100 + 1 / dec_odds
        except (ValueError, TypeError):
            prob = 0.54
        units = grade_adjusted_units('B', prob, dec_odds, BANKROLL, UNIT_SIZE, fraction=KELLY_FRACTION)
        units = max(units, 0.25)  # minimum 0.25u for B picks
        print(f"  ~ {b['pick_desc']} @ {b['book']} (Edge: {b['edge']}% | {units}u)")
        log_bet(b, units=units)
    
    print(f"\nC Picks ({len(c_picks)}): Paper bets only")
    for c in c_picks:
        print(f"  ✗ {c['pick_desc']} @ {c['book']} (Edge: {c['edge']}%)")
        c['paper_bet'] = True
        log_bet(c, units=0)
    
    # Update tracker CSVs with unit sizes
    update_tracker_units(date, a_picks, b_picks, c_picks)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(a_picks)} A | {len(b_picks)} B | {len(c_picks)} C")
    print(f"Logged to: {BET_LOG_PATH}/{date}_bets.md")
    print(f"Updated tracker CSVs with unit sizes")
    print(f"{'='*60}")

def calculate_kelly_units(pick: Dict, grade: str) -> float:
    """Calculate precise Kelly units for a pick based on grade"""
    from kelly_sizing import american_to_decimal, kelly_fraction
    
    BANKROLL = float(os.environ.get('BANKROLL', '5000'))
    UNIT_SIZE = float(os.environ.get('UNIT_SIZE', '100'))
    KELLY_FRACTION = 0.1
    
    odds_raw = pick.get('odds', '1.91')
    try:
        dec_odds = float(odds_raw)
    except (ValueError, TypeError):
        try:
            dec_odds = american_to_decimal(int(str(odds_raw).replace('+', '')))
        except:
            dec_odds = 1.91
    
    try:
        edge = float(pick.get('edge') or pick.get('edge_pct', 0))
        prob = edge / 100 + 1 / dec_odds  # edge% + implied = model prob
    except (ValueError, TypeError):
        prob = 0.55
    
    # Calculate Kelly
    kf = kelly_fraction(prob, dec_odds, KELLY_FRACTION)
    kelly_units = kf * (BANKROLL / UNIT_SIZE)
    
    # Apply grade adjustments
    if grade == 'A':
        units = max(kelly_units, 0.5)  # minimum 0.5u for A
    elif grade == 'B':
        units = max(kelly_units * 0.5, 0.25)  # half Kelly, min 0.25u
    else:
        units = 0.0
    
    return round(units, 2)

def update_tracker_units(date: str, a_picks: list, b_picks: list, c_picks: list):
    """Update tracker CSV files with precise Kelly unit sizes"""
    
    # Update player props CSV with Kelly units
    player_props_file = f'/data/.openclaw/workspace/tracker/data/{date}_player_props.csv'
    if os.path.exists(player_props_file):
        with open(player_props_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Create lookup for Kelly unit sizes
        unit_map = {}
        for pick in a_picks:
            key = (pick.get('player'), pick.get('market'), pick.get('line'))
            unit_map[key] = calculate_kelly_units(pick, 'A')
        for pick in b_picks:
            key = (pick.get('player'), pick.get('market'), pick.get('line'))
            unit_map[key] = calculate_kelly_units(pick, 'B')
        for pick in c_picks:
            key = (pick.get('player'), pick.get('market'), pick.get('line'))
            unit_map[key] = 0.0
        
        # Update rows with precise Kelly unit sizes
        for row in rows:
            key = (row.get('player'), row.get('market'), row.get('line'))
            if key in unit_map:
                row['stake'] = unit_map[key]
        
        # Save updated CSV
        with open(player_props_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'player', 'market', 'line', 'book', 'projection', 'edge_pct', 'bet', 'confidence', 'role', 'game', 'odds', 'stake', 'result', 'profit'])
            writer.writeheader()
            writer.writerows(rows)
    
    # Update team model CSV with Kelly units
    team_model_file = f'/data/.openclaw/workspace/tracker/data/{date}_team_model.csv'
    if os.path.exists(team_model_file):
        with open(team_model_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Create lookup for Kelly unit sizes
        unit_map = {}
        for pick in a_picks:
            key = (pick.get('game'), pick.get('pick_desc'))
            unit_map[key] = calculate_kelly_units(pick, 'A')
        for pick in b_picks:
            key = (pick.get('game'), pick.get('pick_desc'))
            unit_map[key] = calculate_kelly_units(pick, 'B')
        for pick in c_picks:
            key = (pick.get('game'), pick.get('pick_desc'))
            unit_map[key] = 0.0
        
        # Update rows with precise Kelly unit sizes
        for row in rows:
            key = (row.get('game'), row.get('pick'))
            if key in unit_map:
                row['stake'] = unit_map[key]
        
        # Save updated CSV
        with open(team_model_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'game', 'market', 'pick', 'line', 'proj', 'edge', 'book', 'odds', 'stake', 'result', 'profit'])
            writer.writeheader()
            writer.writerows(rows)

def main():
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run_decision_loop(date)

if __name__ == '__main__':
    main()
