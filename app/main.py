from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest
import time

from app.schemas import FraudPredictionRequest, FraudPredictionResponse
from app.preprocess import prepare_dataframe, transform_features
from app.inference import predict_fraud
from app.events import publish_event

app = FastAPI(title="Fraud Detection API")

REQUEST_COUNT = Counter(
    "fraud_api_requests_total",
    "Total API requests",
    ["method", "endpoint"]
)

REQUEST_LATENCY = Histogram(
    "fraud_api_request_latency_seconds",
    "Request latency",
    ["endpoint"]
)


@app.get("/")
def home():
    return {"message": "Fraud Detection API running"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.post("/predict", response_model=FraudPredictionResponse)
def predict(data: FraudPredictionRequest):
    start = time.time()
    REQUEST_COUNT.labels(method="POST", endpoint="/predict").inc()

    try:
        payload = data.model_dump()

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

    finally:
        REQUEST_LATENCY.labels(endpoint="/predict").observe(time.time() - start)
