from datetime import datetime, timedelta
import pika
import utils.rabbitmq_utils as rabbit
import json


##### Creación de scrape_results queue
def declare_scrape_results_queue():
    if not hasattr(declare_scrape_results_queue, "_queue_exists"):
        try:
            rabbit_connect = rabbit.get_rabbit_connection()
            rabbit_channel = rabbit.channel(rabbit_connect)
            rabbit_channel.queue_declare("scrape_results")
            declare_scrape_results_queue._queue_exists = True

        except Exception as e:
            raise RuntimeError(
                f"Error al declarar la cola 'scrape_results' en RabbitMQ: {e}"
            ) from e


##### Encolar mensaje con información de un resultado atómico de scraping
def msg_results_send(
    url: str,
    medio: str,
    batch_id: int,
    starting_time: datetime,
    finishing_time: datetime,
    status: str,  # SUCCESS or ERROR
    error: str = None,
    code: int = None,
):
    try:
        rabbit_channel = rabbit.get_rabbit_connection().channel()
    except pika.exceptions.AMQPChannelError as e:
        print("Error al establecer canal en RabbitMQ")
        raise RuntimeError(f"Error de canal en RabbitMQ: {e}") from e

    declare_scrape_results_queue()

    duration = starting_time - finishing_time
    duration_ms = duration / timedelta(milliseconds=1)
    results_msg = {
        "url": url,
        "medio": medio,
        "batch_id": batch_id,
        "starting_time": starting_time.isoformat(),
        "finishing_time": finishing_time.isoformat(),
        "duration_ms": duration_ms,
        "status": status,
        "error": error,
        "http_code": code,
    }
    try:
        rabbit_channel.basic_publish(
            exchange="", routing_key="scrape_results", body=json.dumps(results_msg)
        )
    except Exception as e:
        print(
            f"Error inesperado. No se pudo insertar mensaje en cola scrape_results: {e}"
        )
        raise RuntimeError(
            f"Error al publicar results_msg en cola scrape_results: {e}"
        ) from e
