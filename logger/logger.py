from datetime import datetime
import pika
import json
from . import logs_operations
import utils.rabbitmq_utils as rabbit
import os
import sys


def callback_crawler(id_logging_process: int):
    def callback(ch, method, properties, body):
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, "crawler_errors")
        print(f"[crawler_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def callback_scheduler(id_logging_process: int):
    def callback(ch, method, properties, body):
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, "scheduler_errors")
        print(f"[scheduler_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def callback_scraping(id_logging_process: int):
    def callback(ch, method, properties, body):
        msg = json.loads(body)
        msg["id_logging_process"] = id_logging_process
        logs_operations.anexar_log(msg, "scraping_results")
        print(f"[scraping_log_queue] Mensaje recibido: {msg}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    return callback


def main():
    starting_time = datetime.now()
    id_logging_process = int(starting_time.timestamp())

    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    for queue_name in [
        "crawler_log_queue",
        "scheduler_log_queue",
        "scraping_log_queue",
    ]:
        rabbit_channel.queue_declare(queue=queue_name, durable=True)

    rabbit_channel.basic_consume(
        queue="crawler_log_queue",
        on_message_callback=callback_crawler(id_logging_process),
    )
    rabbit_channel.basic_consume(
        queue="scheduler_log_queue",
        on_message_callback=callback_scheduler(id_logging_process),
    )
    rabbit_channel.basic_consume(
        queue="scraping_log_queue",
        on_message_callback=callback_scraping(id_logging_process),
    )

    print("Escuchando logs en RabbitMQ...")
    try:
        rabbit_channel.start_consuming()
    except Exception as e:
        print("Error al tratar de recibir mensajes en RabbitMQ")
        raise RuntimeError(f"Error al consumir mensajes en RabbitMQ: {e}") from e


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
