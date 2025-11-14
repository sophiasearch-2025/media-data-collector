import json
from datetime import datetime

import pika
from pika.exceptions import AMQPChannelError  # pyright me tira error sin esto xd

import utils.rabbitmq_utils as rabbit

"""
crawler_log_queue es exception-only:
    - recibe solo mensajes de error
"""

CRAWLER_QUEUE_NAME = "crawler_log_queue"


##### Declarar crawler_log_queue
def declare_crawler_log_queue():
    if not hasattr(declare_crawler_log_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            rabbit_channel = rabbit_connect.channel()
            rabbit_channel.queue_declare(CRAWLER_QUEUE_NAME, durable=True)
            declare_crawler_log_queue._queue_exists = True

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola '{CRAWLER_QUEUE_NAME}' en RabbitMQ: {e}"
            ) from e


"""
scheduler_log_queue es exception-only:
    - recibe solo mensajes de error
"""

SCHEDULER_QUEUE_NAME = "scheduler_log_queue"


##### Creación de scheduler_log_queue
def declare_scheduler_log_queue():
    if not hasattr(declare_scheduler_log_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            rabbit_channel = rabbit_connect.channel()
            rabbit_channel.queue_declare(SCHEDULER_QUEUE_NAME, durable=True)
            declare_scheduler_log_queue._queue_exists = True

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola '{SCHEDULER_QUEUE_NAME}' en RabbitMQ: {e}"
            ) from e


"""
El formato de los mensajes de error provenientes del scheduler es el siguiente:
    {
        "from": "scheduler"
        "arg_medio": arg_medio, correspondiente al argumento 'medio' suministrado
        "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "stage": etapa que falló,
        "error_detail": error_detail,
    }

El formato de los mensajes de error provenientes del crawler es el siguiente:
    {
        "from": "crawler"
        "arg_medio": arg_medio, correspondiente al argumento 'medio' suministrado
        "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "stage": etapa que falló,
        "error_detail": error_detail,
    }
"""


##### Encolar mensaje con información de error capturado en proceso scheduler
def error_send(
    origen: str,
    error_timestamp: datetime,
    error_detail: str,
    arg_medio: str | None = None,
    etapa: str | None = None,
):
    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"""Error de canal en RabbitMQ: {e}.
            No se pudo loggear error {error_detail}.""") from e

    queue_name = ""
    msg_to_enqueue = {}

    if arg_medio is None:
        arg_medio = ""
    if etapa is None:
        etapa = ""

    if origen not in ["scheduler", "crawler"]:
        raise RuntimeError(
            f"Origen no especificado para error {error_detail}. Fallo al loggearlo."
        )

    if origen == "crawler":
        msg_to_enqueue = {
            "from": "crawler",
            "arg_medio": arg_medio,
            "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "stage": etapa,
            "error_detail": error_detail,
        }
        declare_crawler_log_queue()
        queue_name = CRAWLER_QUEUE_NAME

    elif origen == "scheduler":
        msg_to_enqueue = {
            "from": "scheduler",
            "arg_medio": arg_medio,
            "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "stage": etapa,
            "error_detail": error_detail,
        }
        declare_scheduler_log_queue()
        queue_name = SCHEDULER_QUEUE_NAME

    try:
        rabbit_channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(msg_to_enqueue),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    except Exception as e:
        print(
            f"Error inesperado. No se pudo insertar {msg_to_enqueue} en cola {queue_name}: {e}"
        )
        raise RuntimeError(
            f"Error al publicar {msg_to_enqueue} en cola {queue_name}: {e}"
        ) from e
