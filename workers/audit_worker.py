import json
import pika
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.settings import settings

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.audit"
ROUTING_KEY = "fraud.predicted"

engine = create_engine(settings.db_url, future=True)


def wait_for_postgres(max_retries=20, delay=5):
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Connected to PostgreSQL")
            return
        except OperationalError as e:
            print(f"Postgres not ready (attempt {attempt}/{max_retries}): {e}")
            time.sleep(delay)

    raise RuntimeError("Could not connect to PostgreSQL after retries")


def connect_rabbitmq(max_retries=20, delay=5):
    params = pika.URLParameters(settings.rabbitmq_url)

    for attempt in range(1, max_retries + 1):
        try:
            connection = pika.BlockingConnection(params)
            print("Connected to RabbitMQ")
            return connection
        except Exception as e:
            print(f"RabbitMQ not ready (attempt {attempt}/{max_retries}): {e}")
            time.sleep(delay)

    raise RuntimeError("Could not connect to RabbitMQ after retries")


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prediction_audit (
                id SERIAL PRIMARY KEY,
                transaction_id TEXT,
                prediction TEXT,
                fraud_probability FLOAT,
                risk_level TEXT,
                threshold FLOAT,
                timestamp TEXT,
                payload JSONB
            )
        """))


def callback(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    req = event["request"]
    pred = event["prediction"]

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO prediction_audit
            (transaction_id, prediction, fraud_probability, risk_level, threshold, timestamp, payload)
            VALUES
            (:transaction_id, :prediction, :fraud_probability, :risk_level, :threshold, :timestamp, :payload)
        """), {
            "transaction_id": req.get("transaction_id"),
            "prediction": pred["prediction"],
            "fraud_probability": pred["fraud_probability"],
            "risk_level": pred["risk_level"],
            "threshold": pred["threshold"],
            "timestamp": pred["timestamp"],
            "payload": json.dumps(event),
        })

    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    wait_for_postgres()
    init_db()

    connection = connect_rabbitmq()
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Audit worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
