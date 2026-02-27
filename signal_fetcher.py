#!/usr/bin/env python3
"""
Signal Fetcher - Pulls market signals for betting decision loop
Sources:
- thebettinginsider.com (public betting %, line movement, sharp signals)
- the-odds-api (line history, current odds)
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# API Configuration
BETTING_INSIDER_API = "https://thebettinginsider.com/api/public-betting/live-odds"
ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY')
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"

class SignalFetcher:
    def __init__(self):
        self.insider_data = None
        self.odds_data = {}
        
    def fetch_betting_insider(self, sport: str = 'nba') -> Dict:
        """Fetch public betting data from thebettinginsider.com"""
        try:
            url = f"{BETTING_INSIDER_API}?sport={sport}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.insider_data = response.json()
            return self.insider_data
        except Exception as e:
            print(f"Error fetching betting insider: {e}")
            return {}
    
    def fetch_current_odds(self, event_id: str = None) -> Dict:
        """Fetch current odds from the-odds-api"""
        if not ODDS_API_KEY:
            print("THE_ODDS_API_KEY not set")
            return {}
        
        try:
            if event_id:
                url = f"{ODDS_API_BASE}/events/{event_id}/odds"
            else:
                url = f"{ODDS_API_BASE}/odds"
            
            params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'spreads,totals',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching odds: {e}")
            return {}
    
    def get_game_signals(self, home_team: str, away_team: str) -> Dict:
        """Extract signals for a specific game"""
        signals = {
            'line_movement': {},
            'public_betting': {},
            'sharp_signals': [],
            'bet_vs_money_divergence': None,
            'pinnacle': {},
            'signals': {}
        }
        
        if not self.insider_data:
            self.fetch_betting_insider()
        
        if not self.insider_data:
            return signals
        
        # Find game in insider data
        games = self.insider_data.get('games', [])
        for game in games:
            game_home = game.get('home_team', '')
            game_away = game.get('away_team', '')
            
            # Match teams (handle partial names)
            if (home_team in game_home or game_home in home_team or 
                any(word in game_home for word in home_team.split())) and \
               (away_team in game_away or game_away in away_team or
                any(word in game_away for word in away_team.split())):
                
                # Extract public betting %
                signals['public_betting'] = {
                    'spread_bet_pct': game.get('public_spread_bet_pct'),
                    'spread_money_pct': game.get('public_spread_money_pct'),
                    'ml_bet_pct': game.get('public_ml_bet_pct'),
                    'ml_money_pct': game.get('public_ml_money_pct'),
                    'total_over_bet_pct': game.get('public_total_over_bet_pct'),
                    'total_over_money_pct': game.get('public_total_over_money_pct')
                }
                
                # Extract line movement
                signals['line_movement'] = {
                    'spread_open': game.get('opening_spread'),
                    'spread_current': game.get('current_spread'),
                    'spread_movement': game.get('spread_movement'),
                    'total_open': game.get('opening_total'),
                    'total_current': game.get('current_total'),
                    'total_movement': game.get('total_movement')
                }
                
                # Extract Pinnacle lines (sharp book)
                pinnacle = game.get('pinnacle', {})
                signals['pinnacle'] = {
                    'spread_open': pinnacle.get('spread', {}).get('open'),
                    'spread_close': pinnacle.get('spread', {}).get('close'),
                    'total_open': pinnacle.get('total', {}).get('open'),
                    'total_close': pinnacle.get('total', {}).get('close')
                }
                
                # Extract sharp signals
                signal_data = game.get('signals', {})
                signals['signals'] = signal_data
                
                # Parse sharp signals
                sharp_list = []
                for market in ['spread', 'total', 'ml']:
                    market_data = signal_data.get(market, {})
                    for side, side_data in market_data.items():
                        if side_data.get('publicRespect', 0) > 50:
                            sharp_list.append(f"{market}:{side} PublicRespect")
                        if side_data.get('vegasBacked', 0) > 50:
                            sharp_list.append(f"{market}:{side} VegasBacked")
                        if side_data.get('whaleRespect', 0) > 50:
                            sharp_list.append(f"{market}:{side} WhaleRespect")
                
                signals['sharp_signals'] = sharp_list
                
                # Calculate divergence
                spread_bet = signals['public_betting'].get('spread_bet_pct')
                spread_money = signals['public_betting'].get('spread_money_pct')
                
                if spread_bet is not None and spread_money is not None:
                    diff = abs(spread_money - spread_bet)
                    if diff > 15:
                        if spread_money > spread_bet:
                            signals['bet_vs_money_divergence'] = 'Sharp Action'
                        else:
                            signals['bet_vs_money_divergence'] = 'Public Heavy'
                    else:
                        signals['bet_vs_money_divergence'] = 'Aligned'
                
                break
        
        return signals
    
    def format_signal_report(self, home_team: str, away_team: str, 
                             model_pick: str = None, model_line: float = None) -> str:
        """Format signals for pre-bet analysis"""
        signals = self.get_game_signals(home_team, away_team)
        
        pb = signals['public_betting']
        lm = signals['line_movement']
        pin = signals['pinnacle']
        
        report = f"""### Signal Alignment Check

**Game:** {away_team} @ {home_team}
"""
        if model_pick and model_line:
            report += f"**Model says:** {model_pick} (line: {model_line})\n\n"
        
        report += f"""**Line Movement:**
- Spread Open: {lm.get('spread_open', 'N/A')} → Current: {lm.get('spread_current', 'N/A')} (Move: {lm.get('spread_movement', 'N/A')})
- Total Open: {lm.get('total_open', 'N/A')} → Current: {lm.get('total_current', 'N/A')} (Move: {lm.get('total_movement', 'N/A')})

**Pinnacle (Sharp Line):**
- Spread Open: {pin.get('spread_open', 'N/A')} → Close: {pin.get('spread_close', 'N/A')}
- Total Open: {pin.get('total_open', 'N/A')} → Close: {pin.get('total_close', 'N/A')}

**Public Betting %:**
- Spread Bet%: {pb.get('spread_bet_pct', 'N/A')}% | Money%: {pb.get('spread_money_pct', 'N/A')}%
- ML Bet%: {pb.get('ml_bet_pct', 'N/A')}% | Money%: {pb.get('ml_money_pct', 'N/A')}%
- Total Over Bet%: {pb.get('total_over_bet_pct', 'N/A')}% | Money%: {pb.get('total_over_money_pct', 'N/A')}%

**Divergence:** {signals['bet_vs_money_divergence'] or 'N/A'}

**Sharp Signals:** {', '.join(signals['sharp_signals']) if signals['sharp_signals'] else 'None detected'}
"""
        return report

def main():
    """Test the signal fetcher"""
    fetcher = SignalFetcher()
    
    # Test with a sample game
    print("="*60)
    print("TESTING SIGNAL FETCHER")
    print("="*60)
    
    report = fetcher.format_signal_report(
        home_team="Detroit Pistons",
        away_team="Cleveland Cavaliers",
        model_pick="Cavaliers +6.0",
        model_line=6.0
    )
    
    print(report)

if __name__ == '__main__':
    main()
