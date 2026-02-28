#!/usr/bin/env python3
"""
Analyze signal_performance and grade_performance CSVs and produce
signal win rates by type and direction.

- Loads /betting-data/trackers/signal_performance.csv and grade_performance.csv
- Joins on (date, game, bet) for result
- For each signal_name/signal_direction, computes win rate
- Outputs summary to stdout
"""
import csv
from collections import defaultdict, Counter

SIGNAL_FILE = '/data/.openclaw/workspace/betting-data/trackers/signal_performance.csv'
GRADE_FILE = '/data/.openclaw/workspace/betting-data/trackers/grade_performance.csv'

def load_grade_results():
    results = {}  # key: (date, game, bet) -> 'win'/'loss' (or 'pending')
    with open(GRADE_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = (row['date'], row['game'], row['bet'])
            results[k] = row['result'].strip().lower()  # win/loss/pending
    return results

def analyze_signals():
    grade_results = load_grade_results()
    
    # Structure: {signal_name: {signal_direction: [win/loss/...]}}
    perf = defaultdict(lambda: defaultdict(list))
    total_seen = Counter()
    total_wins = Counter()

    with open(SIGNAL_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['date'], row['game'], row['bet'])
            # Take bet result from grade if not filled in
            result = row['bet_result']
            if not result or result == 'pending':
                result = grade_results.get(key, 'pending')
            if result not in ('win','loss'):
                continue  # Only count settled
            win = 1 if result == 'win' else 0
            sig = row['signal_name']
            dir = row['signal_direction']
            perf[sig][dir].append(win)
            total_seen[(sig, dir)] += 1
            total_wins[(sig, dir)] += win
    
    print("Signal performance summary (settled bets only):")
    for sig in perf:
        print(f"\nSignal: {sig}")
        for dir in perf[sig]:
            wins = sum(perf[sig][dir])
            total = len(perf[sig][dir])
            winrate = 100.0 * wins / total if total else 0
            print(f"  - {dir} : {wins}/{total} win ({winrate:.1f}%)")

if __name__ == '__main__':
    analyze_signals()
