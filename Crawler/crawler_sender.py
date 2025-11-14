from crawler_sender import *
import pika, json
from datetime import datetime

SCRAPER_QUEUE = "scraper_queue"
LOG_QUEUE = "crawler_log_queue"

# Conectar con RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
# Abrir un canal de conexión con RabbitMQ
crawler_channel = connection.channel()
# declarar el canal
for q in [SCRAPER_QUEUE, LOG_QUEUE]:
    crawler_channel.queue_declare(queue=q, durable=True)

def send_link (link, tags):
    message = {
        "url":link,     # Link Noticia enviada a scrapper
        "tags":tags     # Tags Categorías 
    }
    # Enviar el mensaje al componente de scrapping
    crawler_channel.basic_publish(
        exchange='',
        routing_key = SCRAPER_QUEUE,
        body = json.dumps(message),
        properties = pika.BasicProperties(
            delivery_mode = 2
        )
    )
    print("Mensaje enviado hacia scraper desde crawler...")
def send_error(link, e, stage):
    message = {
        "origen":"Crawler",
        "error_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_detail":str(e),
        "arg_medio":link,
        "etapa":stage
    }
    crawler_channel.basic_publish(
        exchange='',
        routing_key = LOG_QUEUE,
        body = json.dumps(message),
        properties = pika.BasicProperties(
            delivery_mode = 2
        )

    )
    print("Mensaje error enviado hacia LOG desde crawler...")