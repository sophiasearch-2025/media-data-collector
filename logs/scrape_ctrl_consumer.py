import pika
import utils.rabbitmq_utils as rabbit

"""
CONSUMIR MENSAJES DE CONTROL DE SCRAPEO

"""


# Se debe definir una función callback para la cola
def callback_ctrl(ch, method, properties, body):
    print(f" [x] Received {body}")
    # CONSUMIR MENSAJE
    # SI ES start_batch, empezar a consumir desde otra cola
    # SI ES end_batch y la otra cola está vacía, terminar de consumir desde la otra cola


def scrape_ctrl_consume():
    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    rabbit_channel.basic_consume(
        queue="scrape_ctrl", auto_ack=True, on_message_callback=callback_ctrl
    )

    try:
        rabbit_channel.start_consuming()
    except Exception as e:
        print("Error al intentar consumir mensaje de scrape_ctrl en RabbitMQ")
        raise RuntimeError(f"Error al consumir mensajes en RabbitMQ: {e}") from e
