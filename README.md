# Early Risk Detection Model for Safer Gambling

## Overview
This project implements an **explainable hybrid ML system** for identifying customers at risk of problematic gambling behavior. The system combines **financial ratios, behavioral signals, session characteristics, and machine learning predictions** to compute:

- A **normalized early risk score**  
- A **ML-predicted risk probability**  
- **Per-customer explainable drivers** via SHAP and business-rule triggers  

The model enables **real-time scoring**, monitoring, and intervention for high-risk customers.

---

## Features Used

The scoring system leverages **financial, behavioral, and session-based features**:

| Feature | Description |
|---------|-------------|
| `deposit_to_wager_ratio` | Ratio of deposits to wagers, identifies aggressive depositing behavior. |
| `loss_to_deposit_ratio` | Proportion of losses relative to deposits, highlighting exposure. |
| `session_intensity` | Gambling session intensity (e.g., active hours, wagers per hour). |
| `financial_stress_score` | Flags failed deposits or low withdrawals as a proxy for financial vulnerability. |
| `behavioral_risk_score` | Weighted sum of behavioral triggers (e.g., long sessions, binges, high wagering). |
| `<behavior_flag>_score` | Individual weighted contribution of behavioral flags. |

Optional: rolling windows (e.g., 7-day deposits/losses, session activity) can be used for **adaptive, responsive scoring**.

---

## Scoring Methodology

1. **Normalization**  
   All numeric features are **min-max scaled** to 0–1 for comparability.

2. **Early Risk Score**  
   Combination of normalized financial and behavioral scores: early_risk_score = 0.5 * financial_risk_score + 0.5 * behavioral_risk_score

3. **ML Prediction**  
   Logistic Regression predicts **ML risk probability** based on financial and behavioral features plus raw feature inputs.

4. **Hybrid Final Score**  
   Combines rule-based early risk with ML probability: final_risk_score = 0.5 * early_risk_score + 0.5 * ml_risk_prob


5. **Flagging**  
Customers are flagged as high risk if:
- `final_risk_score >= threshold` (default 0.5), or  
- ML model indicates unusual behavior (`ml_flag = True`)

---

## Explainability

- **Drivers**: Lists key triggers contributing to risk:
- Behavioral triggers (weighted)  
- High financial risk indicators  
- ML anomaly flags  

- **SHAP Values**: Shows **top 5 features contributing to ML risk prediction** per customer.

Example output in JSON (from API):

```json
{
  "customer_id": "CUST_000123",
  "risk": {
    "final_score": 0.705,
    "band": "MEDIUM",
    "flag": true
  },
  "scores": {
    "ml_probability": 0.76,
    "early_score": 0.65,
    "financial_score": 0.65,
    "behavioral_score": 0.75
  },
  "drivers": {
    "top_reasons": [
      "tr_extended_gameplay triggered",
      "ML anomaly"
    ],
    "ml_shap_top": {
      "financial_risk_score": 0.25,
      "behavioral_risk_score": 0.2,
      "session_intensity": 0.1
    }
  },
  "metadata": {
    "model_version": "v1.0",
    "scored_at": "2026-03-24T12:34:56.789Z"
  }
}
```

---

## Output

The model can export a CSV containing:

| Column                  | Description                            |
| ----------------------- | -------------------------------------- |
| `customer_id`           | Unique customer identifier             |
| `final_risk_score`      | Hybrid normalized score (0–1)          |
| `early_risk_score`      | Rule-based early risk score (0–1)      |
| `ml_risk_prob`          | ML-predicted risk probability          |
| `financial_risk_score`  | Normalized financial score (0–1)       |
| `behavioral_risk_score` | Normalized behavioral score (0–1)      |
| `risk_reasons`          | List of triggers and anomalies         |
| `ml_shap_top`           | Top 5 feature contributions to ML risk |

---

## Usage

The model is to be trained, then consumed by the 'DataProcessor' service.

## Architecture
<img width="1536" height="1024" alt="architecturalDiagram" src="https://github.com/user-attachments/assets/80bd1806-d745-48cb-81a1-0d92ec59d9a2" />
