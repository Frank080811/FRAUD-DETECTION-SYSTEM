from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load environment variables (for local dev)
load_dotenv()


class Settings(BaseModel):
    app_name: str = "Fraud Detection API"

    # RabbitMQ (use Railway env in production, fallback for local)
    rabbitmq_url: str = os.getenv("RABBITMQ_URL") or "amqp://guest:guest@localhost:5672/"

    # Database (use Railway env in production, fallback for local)
    db_url: str = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/postgres"

    # Resend Email API (NEW)
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")

    # Email sender (Resend default works without domain setup)
    email_from: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev")


settings = Settings()
