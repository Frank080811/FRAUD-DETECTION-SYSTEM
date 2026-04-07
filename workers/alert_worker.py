import json
import pika
import time
import resend
from sqlalchemy import create_engine, text
from app.settings import settings

# Initialize Resend
resend.api_key = settings.resend_api_key

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.alerts"
ROUTING_KEY = "fraud.high_risk"

engine = create_engine(settings.db_url, future=True)


def connect_with_retry(max_retries=20, delay=5):
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


def get_active_recipients():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT email
            FROM alert_stakeholders
            WHERE is_active = TRUE
            ORDER BY id ASC
        """)).fetchall()

    recipients = [row[0] for row in rows]
    return recipients


def send_email_alert(event: dict):
    import os
    import resend

    try:
        print("🚀 Starting email alert process...")

        # Safe extraction (prevents KeyError crashes)
        data = event.get("request", {})
        pred = event.get("prediction", {})
        top_features = event.get("top_features", {})

        # Get recipients
        receivers = get_active_recipients()

        print("📧 Receivers:", receivers)

        if not receivers:
            print("⚠️ No active alert recipients configured")
            return

        # Validate required settings
        if not settings.email_from:
            print("❌ EMAIL_FROM is not set")
            return

        resend_api_key = os.getenv("RESEND_API_KEY")

        if not resend_api_key:
            print("❌ RESEND_API_KEY is missing in environment variables")
            return

        resend.api_key = resend_api_key

        print("🔑 Resend API key loaded:", bool(resend.api_key))
        print("📨 Sending FROM:", settings.email_from)

        # Email content
        subject = f"🚨 HIGH FRAUD ALERT ({pred.get('risk_level', 'UNKNOWN')})"

        body = f"""
<h2>🚨 Fraud Alert Triggered</h2>

<p><strong>Risk Level:</strong> {pred.get('risk_level')}</p>
<p><strong>Fraud Probability:</strong> {pred.get('fraud_probability')}</p>
<p><strong>Timestamp (UTC):</strong> {pred.get('timestamp')}</p>

<h3>Transaction Details:</h3>
<pre>{json.dumps(data, indent=2)}</pre>

<h3>Top Features:</h3>
<pre>{json.dumps(top_features, indent=2)}</pre>
"""

        print("📧 Sending email to:", receivers)

        # Send email via Resend
        response = resend.Emails.send({
            "from": settings.email_from,
            "to": receivers,
            "subject": subject,
            "html": body,
        })

        print("✅ Email sent successfully:", response)

    except Exception as e:
        print("🔥 FULL EMAIL ERROR:", str(e))
        raise

def callback(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    print("🚨 Received high-risk event:", event["prediction"])

    try:
        send_email_alert(event)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("🚀 Alert worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
