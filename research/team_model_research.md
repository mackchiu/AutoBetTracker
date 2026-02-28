# Team-Based NBA Betting Model v1: Actionable Insights

This report synthesizes research findings into actionable insights for building a foundational team-based NBA betting model. The focus is on approaches implementable with existing data (games, team stats, historical odds).

## 1. Model Architectures

*   **Recommendation:** Start with **regression models** for predicting point differentials and total points, and **logistic regression for win probability**. For a more advanced v1, consider a simple **ensemble method** (e.g., a weighted average of a few different regression models, or a basic stacking model with a linear meta-learner). This offers a balance between complexity and predictive power.
*   **Weighting Recent Form vs. Season-Long Data:** Implement **Exponentially Weighted Moving Averages (EWMA)** for recent form, giving more weight to recent games while still incorporating season-long trends. For Elo-like ratings, calculate them iteratively, updating after each game to reflect season-long performance. A good starting point would be to use a decay factor that prioritizes recent 10-20 games, alongside a long-term Elo.
*   **Home Court Advantage Quantification:** Include **home court advantage as a distinct feature** (e.g., a binary indicator, or a quantifiable points adjustment) within regression models. This can be refined by analyzing historical point differentials for home vs. away teams.

## 2. Feature Engineering

Prioritize features that are highly predictive and can be derived from standard game and team statistics.

*   **Core Team Efficiency Metrics:**
    *   **Offensive Rating (ORtg)** and **Defensive Rating (DRtg)**: Calculate points scored/allowed per 100 possessions. These are pace-adjusted and highly predictive.
    *   **Pace**: Possessions per game. Essential for adjusting other metrics.
    *   **True Shooting Percentage (TS%)**: Measures scoring efficiency.
    *   **Four Factors**: Effective Field Goal Percentage (eFG%), Turnover Percentage (TOV%), Offensive Rebounding Percentage (OREB%), and Free Throw Rate (FTR).
*   **Situational Factors:**
    *   **Rest/Travel:** Create features for back-to-back games, days of rest for both teams, and potentially travel distance/time.
    *   **Lineup Changes & Injury Impacts:** This is crucial. For v1, focus on significant injuries to key players (starters, high-usage bench players). Develop a system to quantify their "impact" by looking at team performance "with/without" them, or using simplified usage differentials. This will likely require manual updates or a robust data source for injury status.
    *   **Momentum/Streaks:** Implement win/loss streak features, possibly weighted by opponent strength, using EWMA to emphasize recent performance.
*   **Derived Features:**
    *   **Opponent-Adjusted Metrics:** Calculate ORtg/DRtg *against* opponent average ORtg/DRtg to get a more refined measure of a team's actual efficiency.
    *   **Recent Performance Differentials:** Create features that compare a team's recent (e.g., last 5, 10 games) performance in key metrics (ORtg, DRtg, Pace) against their season average.

## 3. Market-Specific Strategies

*   **Spreads (Point Differential Prediction):**
    *   **Model Output:** Design regression models to directly predict the point differential for a game.
    *   **Value Identification:** Bet on spreads where your model’s predicted point differential significantly deviates from the bookmaker’s spread (e.g., 2+ points).
    *   **Covering Trends & Public Betting:** While initially focusing on core model predictions, keep an eye on public betting percentages (if available) for potential contrarian plays.
*   **Totals (Pace + Efficiency):**
    *   **Model Output:** Build regression models to predict the combined total score of a game.
    *   **Key Drivers:** Integrate predicted Pace, ORtg, and DRtg for both teams into the totals model.
    *   **Matchup Styles:** Account for how different team styles (e.g., fast-paced vs. slow-paced, strong defense vs. strong offense) interact to influence the total.
*   **Moneyline (Win Probability Models):**
    *   **Model Output:** Use logistic regression or similar classification models to predict the probability of each team winning.
    *   **Implied Odds Comparison:** Convert bookmaker odds into implied win probabilities. Bet when your model’s win probability for a team is significantly higher (e.g., >5%) than the implied odds, indicating an Expected Value (EV) play.

## 4. Backtesting & Validation

*   **Avoiding Lookahead Bias (Crucial!):**
    *   **Walk-Forward Validation:** Train your model on historical seasons (e.g., 2010-2020), then test on the next season (2021). Retrain on 2010-2021, test on 2022, and so on. This mimics real-world application.
    *   **Rolling Features:** Ensure all features used for a prediction are derived *only* from data available *before* that game. For example, a team's "recent 10-game average" must only include games played prior to the game being predicted.
    *   **Season Holdout:** Always hold out the most recent complete season (or even the current season's data) as a final, unseen test set.
*   **Key Validation Metric: Closing Line Value (CLV):**
    *   **Calculation:** For every bet, compare your odds to the closing line odds. A positive CLV means your bet beat the market, indicating you found value. Track average CLV.
    *   **Importance:** Positive CLV is the strongest indicator of a profitable model in the long run, even more so than raw win rate.
*   **Other Metrics:** Track ROI, Net Profit, and win rate across different odds ranges.

## 5. Successful Examples (Adaptations for v1)

*   **"KenPom/BartTorvik" Adaptations:**
    *   **Efficiency-Based Ratings:** Develop your own tempo-free Offensive and Defensive Efficiency ratings similar to KenPom. These will be core to your model.
    *   **Player-Level Impact (Simplified DARKO):** For v1, a simplified approach could be to quantify the impact of key players by looking at team performance (ORtg/DRtg) when they are on/off the court, or their individual usage rates.
*   **Syndicate Approaches:** While complex, the core idea of **exploiting market inefficiencies** by identifying discrepancies between your model's prediction and the market odds is paramount.

## 6. Key Pitfalls

*   **Overfitting:**
    *   **Mitigation:** Employ rigorous cross-validation (walk-forward), use simpler models initially, and limit the number of highly correlated features. Use techniques like L1/L2 regularization if using linear models.
*   **Over-reliance on Recent Games:**
    *   **Mitigation:** Balance recent form with season-long data using EWMA and long-term Elo/ratings. Ensure your model is not overly sensitive to short-term fluctuations.
*   **Ignoring Market Efficiency:**
    *   **Mitigation:** Always prioritize **Expected Value (EV)**. Don't just bet on games your model "wins" a lot; bet on games where your model identifies a clear edge over the market's implied probability. CLV is your guide here.
*   **Not Accounting for Variance (Small Samples):**
    *   **Mitigation:** The NBA has significant variance. Use large historical datasets for training. Acknowledge that short-term results will always be subject to variance, and focus on long-term profitability through EV and positive CLV. Implement robust bankroll management (e.g., 1-2% per wager).

By adhering to these actionable insights, you can build a robust and well-validated team-based NBA betting model v1, focusing on leveraging existing data effectively.
