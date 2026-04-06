from pydantic import BaseModel


class FraudPredictionRequest(BaseModel):
    amount_usd: float
    fee: float
    exchange_rate_src_to_dest: float
    corridor_risk: float
    txn_velocity_1h: int
    txn_velocity_24h: int
    new_device: int
    device_trust_score: float
    location_mismatch: int
    ip_country: str
    ip_risk_score: float
    risk_score_internal: float
    combined_risk_score: float
    chargeback_history_count: int
    kyc_tier: str
    account_age_days: int
    home_country: str
    account_age_group: str
    hour: int
    day_of_week: int
    is_weekend: int
    is_night: int
    amount_outlier: int


class FraudPredictionResponse(BaseModel):
    prediction: str
    fraud_probability: float
    risk_level: str
    threshold: float
    timestamp: str
    authentication: dict | None = None
    alert: str | None = None
