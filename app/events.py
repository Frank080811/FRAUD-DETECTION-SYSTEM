import json
import pika
from app.settings import settings


EXCHANGE_NAME = "fraud.events"


def get_connection():
    params = pika.URLParameters(settings.rabbitmq_url)
    return pika.BlockingConnection(params)


def publish_event(routing_key: str, message: dict):
    connection = get_connection()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True
    )

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=routing_key,
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=2)
    )

    connection.close()