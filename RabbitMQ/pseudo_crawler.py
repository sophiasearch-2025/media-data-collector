import pika, json, subprocess, sys, time
from datetime import datetime as dtime

# --- colas a preparar ---
SCRAPER_QUEUE = "scraper_queue"
# --- medios disponibles ---
medios = [
    "biobiochile"
]
# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
sche_channel = connection.channel()
# --- declaración de la cola de error ---
sche_channel.queue_declare(queue=SCRAPER_QUEUE, durable=True)

def main():
    # --- se recibe el medio el cual se quiere crawlear por argumento --- 
    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
    else:
        while(True):
            msg = {
                "url": "https://www.biobiochile.cl/noticias/nacional/chile/2025/10/12/franco-parisi-creo-que-paso-a-segunda-vuelta-con-jara-no-hay-tanto-voto-de-ultraderecha-en-chile.shtml",
                "tags": ["politica", "pichula"]
            }
            # --- se envia el mensaje a la cola de scraper, este lo debe recibir y scrapear ---
            sche_channel.basic_publish(
                exchange='',
                routing_key=SCRAPER_QUEUE,
                body=json.dumps(msg), # --- mensaje en formato JSON ---
                properties=pika.BasicProperties(
                    delivery_mode=2
                )
            )
            # --- envio el mimso mensaje cad 5 seg ---
            time.sleep(5)

if("__main__" == __name__):
    main()