import json
import pika
import smtplib
import time
from email.mime.text import MIMEText
from app.settings import settings

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.alerts"
ROUTING_KEY = "fraud.high_risk"


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


def send_email_alert(event: dict):
    data = event["request"]
    pred = event["prediction"]
    top_features = event["top_features"]

    receivers = [x.strip() for x in settings.smtp_to.split(",") if x.strip()]
    subject = f"🚨 HIGH FRAUD ALERT ({pred['risk_level']})"

    body = f"""
Fraud Alert Triggered

Risk Level: {pred['risk_level']}
Fraud Probability: {pred['fraud_probability']}
Timestamp (UTC): {pred['timestamp']}

Client Info:
Name: {data.get('customer_name', 'N/A')}
Email: {data.get('customer_email', 'N/A')}
Phone: {data.get('customer_phone', 'N/A')}
Transaction ID: {data.get('transaction_id', 'N/A')}

Top Features:
{json.dumps(top_features, indent=2)}
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(receivers)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, receivers, msg.as_string())


def callback(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    try:
        send_email_alert(event)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Email failed: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Alert worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
