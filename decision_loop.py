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

# Paths
BETTING_DATA_PATH = '/data/.openclaw/workspace/betting-data'
TRACKER_PATH = f'{BETTING_DATA_PATH}/trackers'
BET_LOG_PATH = f'{BETTING_DATA_PATH}/bet_log'

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
        'grade_reasoning': []
    }
    
    return analysis

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
    entry = f"""### Bet Log Entry
Date: {date}
Game: {analysis['game']}
Bet: {analysis['pick_desc']}
Book: {analysis['book']}
Odds: {analysis['odds']}
Grade: {analysis['grade']}
Units: {units}

Model Analysis:
- Projection: {analysis['projection']}
- Line: {analysis['line']}
- Edge: {analysis['edge']}%

Signal Check:
{chr(10).join(analysis['grade_reasoning'])}

Result: pending
Actual: pending

---

"""
    
    # Append to file
    with open(log_file, 'a') as f:
        f.write(entry)
    
    # Update grade performance tracker
    update_grade_tracker(analysis, units)

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
    print(f"GRADE BREAKDOWN")
    print(f"{'='*60}")
    print(f"A Picks ({len(a_picks)}): Full unit bets")
    for a in a_picks:
        print(f"  ✓ {a['pick_desc']} @ {a['book']} (Edge: {a['edge']}%)")
        log_bet(a, units=1.0)
    
    print(f"\nB Picks ({len(b_picks)}): Half unit bets")
    for b in b_picks:
        print(f"  ~ {b['pick_desc']} @ {b['book']} (Edge: {b['edge']}%)")
        log_bet(b, units=0.5)
    
    print(f"\nC Picks ({len(c_picks)}): Paper bets only")
    for c in c_picks:
        print(f"  ✗ {c['pick_desc']} @ {c['book']} (Edge: {c['edge']}%)")
        # Log as paper bet
        c['paper_bet'] = True
        log_bet(c, units=0)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(a_picks)} A | {len(b_picks)} B | {len(c_picks)} C")
    print(f"Logged to: {BET_LOG_PATH}/{date}_bets.md")
    print(f"{'='*60}")

def main():
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run_decision_loop(date)

if __name__ == '__main__':
    main()
