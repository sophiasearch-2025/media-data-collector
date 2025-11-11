import pika
import utils.rabbitmq_utils as rabbit

"""
CONSUMIR RESULTADOS DE SCRAPEO

"""


# Se debe definir una función callback para la cola
def callback_results(ch, method, properties, body):
    print(f" [x] Received {body}")


def scrape_results_consume():
    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    rabbit_channel.basic_consume(
        queue="scrape_results", auto_ack=True, on_message_callback=callback_results
    )

    try:
        rabbit_channel.start_consuming()
    except Exception as e:
        print("Error al intentar consumir mensaje de scrape_results en RabbitMQ")
        raise RuntimeError(f"Error al consumir mensajes en RabbitMQ: {e}") from e
