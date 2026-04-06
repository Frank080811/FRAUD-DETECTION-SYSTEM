import json
import pika
from app.settings import settings

EXCHANGE_NAME = "fraud.events"
QUEUE_NAME = "fraud.auth"
ROUTING_KEY = "fraud.auth_requested"


def callback(ch, method, properties, body):
    event = json.loads(body.decode("utf-8"))
    print("Auth workflow triggered for:", event["request"].get("transaction_id"))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print("Auth worker listening...")
    channel.start_consuming()


if __name__ == "__main__":
    main()