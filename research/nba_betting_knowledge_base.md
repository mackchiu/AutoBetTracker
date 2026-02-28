## Insights from "Machine learning for sports betting: Should model selection be based on accuracy or calibration?" by Walsh & Joshi (2024) - [2026-02-27]

### Model Selection & Performance:
- **Prioritize Calibration**: For sports betting models, selecting models based on **calibration** (e.g., using Classwise Expected Calibration Error) is significantly more profitable than selecting based on accuracy.
    - Calibration-based selection: +34.69% ROI
    - Accuracy-based selection: -35.17% ROI
- **Why Accuracy Fails**: Accuracy doesn't measure the distance from true probability. Miscalibrated models lead to poor bet sizing and selection, even if often "correct."

### Key Concepts & Metrics:
- **Classwise Expected Calibration Error (classwise-ECE)**: Essential metric for evaluating model calibration, especially in multi-class scenarios like NBA betting. Use 20 bins for calculation.
- **Kelly Criterion / Fractional Kelly**: Adopt for optimal bet sizing to maximize long-term bankroll growth. This strategy is highly dependent on well-calibrated probabilities.

### Feature Engineering Recommendations:
- **Relative Performance**: Use features capturing "average out-performance vs. opponents" instead of raw individual/team statistics to better reflect team strength.
- **Historical Performance**: Include "previous season winning percentage" as a robust indicator.
- **Data Preprocessing**:
    - Implement **feature standardization**.
    - Crucially, integrate **covariate shift detection** to manage changes in data distribution over time (e.g., rule changes, team dynamics).

### Model Pipeline Considerations:
- **Model Variety**: Test a range of models including Logistic Regression, Random Forest, SVM, and Multi-layer Perceptrons (MLP).
- **Calibration-Focused Hyperparameter Optimization**: When optimizing models, ensure hyperparameters are tuned to improve calibration metrics (e.g., classwise-ECE) rather than just accuracy.

### Betting Strategy Implementation:
- **Value Betting**: Define value bets as instances where `model probability > implied probability` derived from bookmaker odds.
- **Bookmaker Margin**: Always account for the typical bookmaker margin (~5%) in calculations.
- **Closing Odds**: Base pre-game betting decisions on **closing odds**, as they represent the most informed market price.
