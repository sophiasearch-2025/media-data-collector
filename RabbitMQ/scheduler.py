import sys
import pika
import subprocess
from datetime import datetime as dtime
from ..logger.queue_sender_generic_error import error_send

# --- colas a preparar ---
LOG_QUEUE = "scheduler_log_queue"
# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
sche_channel = connection.channel()
# --- declaración de la cola de error ---
sche_channel.queue_declare(queue=LOG_QUEUE, durable=True)

def proceso_send_datos():
    # --- crear el listener de envio de datos ---
    subprocess.Popen(
        ["python", "RabbitMQ/send_data.py"]
    )

def proceso_scrapper(n):
    # --- crear listener del scraper (el cual espera a mensajes de crawler) ---
    for _ in n:
        subprocess.Popen(
            ["python", "scraper/scraper_biobio.py"]
        )

def proceso_crawler(medio):
    # --- crear listener del crawler ---
    crawl_process = subprocess.Popen(
        ["python", "Crawler/crawler_biobio.py", medio]
    )
    # --- se esperan a los procesos para continuar ---
    crawl_process.wait()

def main():
    # --- crear listener del logger inicialmente (prioritario) ---
    subprocess.Popen(["python", "-m", "logger.logger"])
    # --- se recibe el medio el cual se quiere crawlear por argumento ---
    if len(sys.argv) != 3:
        print("Se debe ejecutar con ./scheduler.py <medio> <cantidad_de_scrappers>")
    else:
        # --- recuperamos el medio ---
        medio = sys.argv[1]
        n_scrapers = sys.argv[2]
        try:
            # --- llamamos los procesos ---
            proceso_send_datos()
            proceso_scrapper(n_scrapers)
            proceso_crawler(medio)
        # --- FALLO DEL SCHEDULER ---
        except Exception as e:
            # --- se envia el mensaje de error a "errores y logs" ---
            error_send(
                "scheduler", 
                str(dtime.now().strftime("%Y-%m-%d %H:%M:%S")),
                str(e),
                medio,
                "Fallo durante el llamado de algún proceso"
            )

if "__main__" == __name__:
    main()