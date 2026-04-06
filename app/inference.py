from datetime import datetime, timezone
import numpy as np
from app.model_loader import model, threshold


def classify_risk(prob: float) -> str:
    if prob < 0.05:
        return "LOW"
    elif prob < 0.20:
        return "MODERATE"
    return "HIGH"


def predict_fraud(X_processed, feature_names):
    prob = float(model.predict_proba(X_processed)[:, 1][0])
    prediction = int(prob > threshold)
    label = "FRAUD" if prediction else "NOT FRAUD"
    risk_level = classify_risk(prob)
    timestamp = datetime.now(timezone.utc).isoformat()

    importances = model.feature_importances_
    top_indices = np.argsort(importances)[-3:][::-1]
    top_features = {feature_names[i]: float(importances[i]) for i in top_indices}

    response = {
        "prediction": label,
        "fraud_probability": round(prob, 4),
        "risk_level": risk_level,
        "threshold": float(threshold),
        "timestamp": timestamp,
    }
    return response, top_features