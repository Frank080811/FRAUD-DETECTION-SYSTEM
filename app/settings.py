from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = "Fraud Detection API"

    # RabbitMQ (NO hardcoded fallback to docker hostname)
    rabbitmq_url: str = os.getenv("RABBITMQ_URL") or "amqp://guest:guest@localhost:5672/"

    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_to: str = os.getenv("SMTP_TO", "")

    # Database (CRITICAL FIX)
    db_url: str = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/postgres"


settings = Settings()
