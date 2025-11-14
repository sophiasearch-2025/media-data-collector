import os
import subprocess
import sys
from datetime import datetime as dtime

import pika

# Importa error_send() y scraping_batch_send() desde logger/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger.queue_sender_generic_error import error_send
from logger.queue_sender_logger_ctrl import logging_batch_send

# --- colas a preparar ---
LOG_QUEUE = "scheduler_log_queue"
# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
sche_channel = connection.channel()
# --- declaración de la cola de error ---
sche_channel.queue_declare(queue=LOG_QUEUE, durable=True)


def proceso_send_datos():
    # --- crear el listener de envio de datos ---
    subprocess.Popen(["python", "RabbitMQ/send_data.py"])


def proceso_scrapper(n):
    # --- crear listener del scraper (el cual espera a mensajes de crawler) ---
    for _ in n:
        subprocess.Popen(["python", "scraper/scraper_biobio.py"])


def proceso_crawler(medio):
    # --- crear listener del crawler ---
    crawl_process = subprocess.Popen(["python", "Crawler/crawler.py", medio])
    # --- se esperan a los procesos para continuar ---
    crawl_process.wait()


def main():
    # --- crear listener del logger inicialmente (prioritario) ---
    starting_time = dtime.now()
    id_logging_process = int(
        starting_time.timestamp()
    )  # identificador distintivo del proceso de logging
    proceso_logging = subprocess.Popen(
        ["python", "-m", "logger.logger", "--id", str(id_logging_process)]
    )
    logging_batch_send(
        id_logging_process, "start_batch", starting_time
    )  # envía alerta de que se iniciará tanda de scrapeo

    # --- se recibe el medio el cual se quiere crawlear por argumento ---
    if len(sys.argv) != 3:
        error_send(
            "scheduler",
            dtime.now(),
            "Intento de ejecución con uso incorrecto de argumentos",
            "",
            "Fallo inicial de ejecución",
        )
        print("Se debe ejecutar con ./scheduler.py <medio> <cantidad_de_scrappers>")
    else:
        # --- recuperamos el medio ---
        medio = sys.argv[1]
        n_scrapers = sys.argv[2]
        stage = ""
        try:
            # --- llamamos los procesos ---
            stage = "Llamando subproceso de envío de datos"
            proceso_send_datos()
            stage = "Llamando subproceso de scraping"
            proceso_scrapper(n_scrapers)
            stage = "Llamando subproceso crawler"
            proceso_crawler(medio)
            stage = "Señalizar fin de logging"
            logging_batch_send(id_logging_process, "end_batch_received", dtime.now())
            proceso_logging.wait()

        # --- FALLO DEL SCHEDULER ---
        except Exception as e:
            # --- se envia el mensaje de error a "errores y logs" ---
            error_send(
                "scheduler",
                dtime.now(),
                str(e),
                medio,
                stage,
            )


if "__main__" == __name__:
    main()
