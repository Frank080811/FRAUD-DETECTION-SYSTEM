from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


class FraudPredictionRequest(BaseModel):
    transaction_id: str = Field(..., examples=["txn_12345"])
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None

    amount: float
    country: str
    device_type: Optional[str] = "unknown"
    payment_method: Optional[str] = "unknown"
    new_device: Optional[bool] = False
    location_mismatch: Optional[bool] = False

    class Config:
        extra = "allow"  

class FraudPredictionResponse(BaseModel):
    prediction: str
    fraud_probability: float
    risk_level: str
    threshold: float
    timestamp: str
    authentication: Optional[Dict[str, Any]] = None
    alert: Optional[str] = None