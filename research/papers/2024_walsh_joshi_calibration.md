# Machine learning for sports betting: Should model selection be based on accuracy or calibration? by Walsh & Joshi (2024)

## Abstract

This paper investigates the effectiveness of different model selection criteria in machine learning for sports betting, specifically comparing accuracy-based and calibration-based approaches. The central hypothesis is that calibration is a more crucial metric than accuracy for profitable sports betting, as it directly relates to the trustworthiness of predicted probabilities, which is essential for value betting strategies.

## Key Findings & Insights:

### 1. Central Hypothesis: Calibration > Accuracy for Sports Betting Model Selection
The research strongly supports the hypothesis that prioritizing model calibration over accuracy leads to significantly better betting outcomes.
-   **Calibration-based selection**: Achieved a positive Return on Investment (ROI) of +34.69%.
-   **Accuracy-based selection**: Resulted in a negative ROI of -35.17%.
This demonstrates a substantial performance difference, highlighting the critical importance of selecting models based on their ability to accurately reflect true probabilities rather than just their predictive correctness.

### 2. Key Concepts

-   **Classwise Expected Calibration Error (classwise-ECE)**: This metric was utilized to quantify the calibration of models. Unlike overall calibration, classwise-ECE assesses calibration within specific prediction classes (e.g., home win, away win), which is particularly relevant in imbalanced or multi-class prediction scenarios common in sports.
-   **Why accuracy fails for betting**: Accuracy measures how often a model is correct, but it does not account for the *distance* between the predicted probability and the true probability. In sports betting, where implied probabilities from odds are compared to model probabilities, miscalibrated probabilities can lead to poor bet sizing and selection, even if the model's predictions are frequently "correct." A highly accurate but poorly calibrated model might consistently over- or under-estimate probabilities, leading to systematic losses when betting on value.
-   **Kelly criterion and fractional Kelly for bet sizing**: The Kelly criterion is an optimal betting strategy that maximizes the long-term growth rate of a bankroll by determining the optimal fraction of one's bankroll to wager on a bet. The paper likely employed this, or a fractional variant (e.g., half-Kelly), to size bets based on the model's predicted probabilities and the implied probabilities from bookmaker odds. Proper calibration is paramount for the Kelly criterion to function effectively, as it assumes the predicted probabilities are reliable.

### 3. Feature Engineering

The study emphasized specific feature engineering techniques to enhance model performance in a sports betting context:
-   **Average out-performance vs opponents (not raw stats)**: Instead of using raw team statistics (e.g., points scored, rebounds), the models incorporated features that capture a team's performance relative to their opponents. This could involve metrics like point differential against average opponent, or advanced metrics that normalize performance based on strength of schedule. This approach aims to capture true team strength more effectively.
-   **Previous season winning percentage**: This is a strong indicator of team quality and consistency, providing a baseline performance measure.
-   **Feature standardization + covariate shift detection**:
    -   **Feature Standardization**: Scaling features to a standard range (e.g., mean 0, variance 1) is crucial for many machine learning algorithms, preventing features with larger numerical ranges from dominating the learning process.
    -   **Covariate Shift Detection**: Sports data can exhibit covariate shift, where the distribution of input features changes over time (e.g., rule changes, team roster changes, meta-game shifts). Detecting and potentially mitigating this shift can improve model robustness and generalization to future data.

### 4. Model Pipeline

The research employed a robust modeling pipeline:
-   **Logistic Regression, Random Forest, SVM, MLP tested**: A diverse set of machine learning models were evaluated, representing linear, tree-based, kernel-based, and neural network approaches. This allows for a comprehensive comparison of how different model architectures perform under calibration-based selection.
-   **Hyperparameter optimization on calibration vs accuracy branches**: A critical aspect of the study was optimizing hyperparameters specifically for either calibration or accuracy. This means that for each model type, two distinct optimization paths were likely followed: one aiming to minimize a calibration error metric (like classwise-ECE) and another aiming to maximize accuracy. This directly contrasts the impact of the selection criteria.
-   **20 bins for classwise-ECE calculation**: The classwise-ECE was calculated by dividing the probability prediction range into 20 bins. This fine-grained binning allows for a detailed assessment of calibration across the entire spectrum of predicted probabilities, providing a more precise calibration error measure.

### 5. Betting Strategy

The study outlined a clear betting strategy predicated on the model outputs:
-   **Value bets**: Bets are placed when the model's predicted probability for an outcome is greater than the implied probability derived from the bookmaker's odds. This identifies situations where the bookmaker is underestimating an outcome's likelihood according to the model.
-   **Bookmaker margin ~5%**: Acknowledges the inherent "vig" or commission built into bookmaker odds, typically around 5%. Profitable betting strategies must overcome this margin.
-   **Pre-game betting based on closing odds**: The strategy focuses on placing bets before the game starts, using the "closing odds." Closing odds are generally considered the most efficient market price, as they incorporate the most information up to game time. Betting against closing odds is often seen as a robust test of a model's predictive edge.

## Conclusion

The findings strongly advocate for the use of calibration-based model selection criteria, such as classwise-ECE, when developing machine learning models for sports betting. Models optimized for calibration demonstrate superior profitability compared to those optimized solely for accuracy. This suggests that the reliability of probability estimates is more critical than raw predictive correctness for successful value betting strategies that leverage concepts like the Kelly criterion and exploit discrepancies between model probabilities and closing bookmaker odds.
