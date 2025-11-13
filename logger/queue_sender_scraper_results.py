import json
from datetime import datetime, timedelta

import pika

import utils.rabbitmq_utils as rabbit

"""
scraping_log_queue recibe:
    - un mensaje que indica el inicio del scrapeo
    - mensajes que indican los resultados del scrapeo para cada URL (success/error)
    - un mensaje que indica el fin del scrapeo
"""

QUEUE_NAME = "scraping_log_queue"


##### Creación de scraping_log_queue
def declare_scraping_log_queue():
    if not hasattr(declare_scraping_log_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            if rabbit_connect is None:
                raise RuntimeError(
                    "No se ha podido conectar a RabbitMQ. rabbit_connect is None."
                )
            rabbit_channel = rabbit_connect.channel()
            rabbit_channel.queue_declare(QUEUE_NAME, durable=True)
            declare_scraping_log_queue._queue_exists = True

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola '{QUEUE_NAME}' en RabbitMQ: {e}"
            ) from e


##### Encolar mensaje que advierte si se inició o concluyó la tanda de trabajo
def scraping_batch_send(msg_scraping_id: int, msg_action: str):
    if msg_action not in ("start_batch", "end_batch"):
        print(
            "Error de logging: Se proporcionó un action inválido para log de type ctrl"
        )
        return

    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    batch_msg = {
        "type": "control",
        "action": msg_action,
    }
    try:
        rabbit_channel.basic_publish(
            exchange="", routing_key=QUEUE_NAME, body=json.dumps(batch_msg)
        )
    except Exception as e:
        print(
            f"Error inesperado. No se pudo insertar mensaje en cola {QUEUE_NAME}: {e}"
        )
        raise RuntimeError(
            f"Error al publicar batch_msg en cola {QUEUE_NAME}: {e}"
        ) from e


##### Encolar mensaje con información de un resultado atómico de scraping
def scraping_results_send(
    url: str,
    medio: str,
    starting_time: datetime,
    status: str,  # success or error
    finishing_time: datetime | None = None,
    error: str | None = None,
):
    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    results_msg = {
        "url": url,
        "medio": medio,
        "starting_time": starting_time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
    }

    if finishing_time is not None:
        duration = finishing_time - starting_time
        duration_ms = duration / timedelta(milliseconds=1)
        results_msg["finishing_time"] = finishing_time.strftime("%Y-%m-%d %H:%M:%S")
        results_msg["duration_ms"] = duration_ms
        results_msg["error"] = error

    else:
        results_msg["finishing_time"] = ""
        results_msg["duration_ms"] = ""
        results_msg["error"] = error

    body_msg = {"type": "result", "data": results_msg}

    declare_scraping_log_queue()
    try:
        rabbit_channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(body_msg),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    except Exception as e:
        print(
            f"Error inesperado. No se pudo insertar {body_msg} en cola {QUEUE_NAME}: {e}"
        )
        raise RuntimeError(
            f"Error al publicar {body_msg} en cola {QUEUE_NAME}: {e}"
        ) from e
