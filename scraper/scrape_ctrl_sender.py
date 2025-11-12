import pika
import utils.rabbitmq_utils as rabbit
import json

"""
scrape_ctrl recibe los mensajes de inicio y fin de cada tanda/lote de scrapeo.
"""


##### Creación de scrape_ctrl_queue
def declare_scrape_ctrl_queue():
    if not hasattr(declare_scrape_ctrl_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            rabbit_channel = rabbit_connect.channel()
            rabbit_channel.queue_declare("scrape_ctrl")
            declare_scrape_ctrl_queue._queue_exists = True

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola 'scrape_ctrl' en RabbitMQ: {e}"
            ) from e


##### Encolar mensaje que advierte si se inició o concluyó el batch de trabajo
def msg_batch_send(batch_id: int, msg_type: str):
    if msg_type not in ("start_batch", "end_batch"):
        print("Error de scraping: Se proporcionó un msg_type inválido")
        return

    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    declare_scrape_ctrl_queue()
    batch_msg = {"batch_id": batch_id, "type": msg_type}
    try:
        rabbit_channel.basic_publish(
            exchange="", routing_key="scrape_ctrl", body=json.dumps(batch_msg)
        )
    except Exception as e:
        print(f"Error inesperado. No se pudo insertar mensaje en cola scrape_ctrl: {e}")
        raise RuntimeError(
            f"Error al publicar batch_msg en cola scrape_ctrl: {e}"
        ) from e
