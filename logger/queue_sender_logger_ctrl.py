import json
from datetime import datetime

from pika.exceptions import AMQPChannelError, AMQPConnectionError, StreamLostError

import utils.rabbitmq_utils as rabbit

"""
logging_ctrl_queue recibe:
    - mensaje que indica el inicio del proceso de logging
    - mensaje que indica la finalización del proceso de logging
"""

QUEUE_NAME = "logging_control_queue"


# Declarar cola
def declare_logging_ctrl_queue():
    if not hasattr(declare_logging_ctrl_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            if rabbit_connect is None:
                raise RuntimeError(
                    "No se ha podido conectar a RabbitMQ. rabbit_connect is None."
                )
            rabbit_channel = rabbit_connect.channel()
            rabbit_channel.queue_declare(QUEUE_NAME, durable=False, auto_delete=True)

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola '{QUEUE_NAME}' en RabbitMQ: {e}"
            ) from e


def _attempt_send(batch_msg):
    """Función auxiliar interna para intentar el envío"""
    rabbit_channel = rabbit_channel = rabbit.get_rabbit_connection().channel()
    declare_logging_ctrl_queue()
    rabbit_channel.basic_publish(
        exchange="", routing_key=QUEUE_NAME, body=json.dumps(batch_msg)
    )


##### Encolar mensaje que advierte si se inició o concluyó la tanda
def logging_batch_send(id_logging_process: int, msg_action: str, msg_time: datetime):
    if msg_action not in ("start_batch", "end_batch_received", "end_batch_completed"):
        print(
            "Error de logging: Se proporcionó un action inválido para log de type ctrl"
        )
        return

    batch_msg = {
        "id_logging_process": id_logging_process,
        "action": msg_action,
        "timestamp": msg_time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        # Intento 1: Envío normal
        _attempt_send(batch_msg)

    except (AMQPConnectionError, StreamLostError, RuntimeError) as e:
        # Si falla por conexión (EOF, StreamLost, etc.)
        try:
            # Forzar reseteo de la conexión
            rabbit.reset_connection()
            # Intento 2: Reintentar envío con conexión fresca
            _attempt_send(batch_msg)

        except Exception as e2:
            print(f"Error fatal. No se pudo insertar mensaje en cola {QUEUE_NAME} tras reintento: {e2}")

    except Exception as e:
        print(f"Error inesperado al publicar batch_msg en cola {QUEUE_NAME}: {e}")
