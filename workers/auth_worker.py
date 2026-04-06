import json
import pika
import time
from app.settings import settings

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.auth"
ROUTING_KEY = "fraud.auth_requested"


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


def callback(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    print("Auth workflow triggered for:", event["request"].get("transaction_id"))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Auth worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
