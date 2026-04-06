from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.settings import settings
from app.schemas import FraudPredictionRequest
from app.preprocess import prepare_dataframe, transform_features
from app.inference import predict_fraud
from app.events import publish_event
import pika

router = APIRouter(prefix="/demo", tags=["Demo"])

engine = create_engine(settings.db_url, future=True)


@router.get("/health")
def demo_health():
    status = {
        "api": "ok",
        "postgres": "unknown",
        "rabbitmq": "unknown"
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except OperationalError as e:
        status["postgres"] = f"error: {str(e)}"

    try:
        params = pika.URLParameters(settings.rabbitmq_url)
        connection = pika.BlockingConnection(params)
        connection.close()
        status["rabbitmq"] = "ok"
    except Exception as e:
        status["rabbitmq"] = f"error: {str(e)}"

    return status


@router.get("/audit/recent")
def recent_audits(limit: int = 10):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, transaction_id, prediction, fraud_probability,
                   risk_level, threshold, timestamp
            FROM prediction_audit
            ORDER BY id DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

    return {"count": len(rows), "items": [dict(r) for r in rows]}


def run_prediction(payload: dict):
    df = prepare_dataframe(payload)
    X_processed = transform_features(df)
    feature_names = list(df.columns)

    response, top_features = predict_fraud(X_processed, feature_names)

    event = {
        "request": payload,
        "prediction": response,
        "top_features": top_features,
    }

    publish_event("fraud.predicted", event)

    if response["risk_level"] in ["LOW", "MODERATE"]:
        publish_event("fraud.auth_requested", event)
        response["authentication"] = {
            "facial_authentication": "TRIGGERED",
            "status": "PENDING_VERIFICATION"
        }

    if response["risk_level"] == "HIGH":
        publish_event("fraud.high_risk", event)
        response["alert"] = "QUEUED_FOR_ALERTING"

    return response


@router.post("/test-high-risk")
def test_high_risk():
    payload = {
        "amount_usd": 5000,
        "fee": 25,
        "exchange_rate_src_to_dest": 1.0,
        "corridor_risk": 0.9,
        "txn_velocity_1h": 8,
        "txn_velocity_24h": 20,
        "new_device": 1,
        "device_trust_score": 0.1,
        "location_mismatch": 1,
        "ip_country": "NG",
        "ip_risk_score": 0.9,
        "risk_score_internal": 0.85,
        "combined_risk_score": 0.92,
        "chargeback_history_count": 3,
        "kyc_tier": "BASIC",
        "account_age_days": 5,
        "home_country": "US",
        "account_age_group": "NEW",
        "hour": 2,
        "day_of_week": 6,
        "is_weekend": 1,
        "is_night": 1,
        "amount_outlier": 1
    }
    return run_prediction(payload)


@router.post("/test-low-risk")
def test_low_risk():
    payload = {
        "amount_usd": 120,
        "fee": 2,
        "exchange_rate_src_to_dest": 1.0,
        "corridor_risk": 0.05,
        "txn_velocity_1h": 0,
        "txn_velocity_24h": 2,
        "new_device": 0,
        "device_trust_score": 0.95,
        "location_mismatch": 0,
        "ip_country": "US",
        "ip_risk_score": 0.02,
        "risk_score_internal": 0.01,
        "combined_risk_score": 0.03,
        "chargeback_history_count": 0,
        "kyc_tier": "ENHANCED",
        "account_age_days": 500,
        "home_country": "US",
        "account_age_group": "OLD",
        "hour": 14,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_night": 0,
        "amount_outlier": 0
    }
    return run_prediction(payload)