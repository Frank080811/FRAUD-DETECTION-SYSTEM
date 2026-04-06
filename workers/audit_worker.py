import json
import pika
from sqlalchemy import create_engine, text
from app.settings import settings

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.audit"
ROUTING_KEY = "fraud.predicted"

engine = create_engine(settings.db_url, future=True)


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
    init_db()

    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Audit worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()