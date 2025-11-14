import json
import subprocess
import sys
from datetime import datetime as dtime

import pika

# --- colas a preparar ---
LOG_QUEUE = "log_queue"
# --- medios disponibles ---
medios = ["biobiochile"]
# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
sche_channel = connection.channel()
# --- declaración de la cola de error ---
sche_channel.queue_declare(queue=LOG_QUEUE, durable=True)


def main():
    # --- crear listener del logger inicialmente (prioritario) ---
    logger_process = subprocess.Popen(["python", "-m", "logger.logger"])
    # --- se recibe el medio el cual se quiere crawlear por argumento ---
    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
    else:
        try:
            # --- llamar al crawler con el medio ---
            medio = sys.argv[1]
            if medio not in medios:
                print("No existe el medio ingresado")
            else:
                # --- crear el listener de envio de datos ---
                send_datos_process = subprocess.Popen(
                    ["python", "RabbitMQ/send_data.py"]
                )
                # --- crear listener del scraper (el cual espera a mensajes de crawler) ---
                scrap_process = subprocess.Popen(
                    ["python", "scraper/scraper_biobio.py"]
                )
                # # --- crear listener del crawler ---
                crawl_process = subprocess.Popen(
                    ["python", "Crawler/crawler.py", medio]
                )
                # --- se esperan a los procesos para continuar ---
                # send_datos_process.wait()
                # scrap_process.wait()
                # logger_process.wait()
                crawl_process.wait()

        # --- FALLO DEL SCHEDULER ---
        except Exception as e:
            # --- se genera el mensaje de error ---
            error_msg = {
                "starting_time": dtime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "state": "error",
                "error": str(e),
                "from": "scheduler",
            }
            # --- se envia el mensaje de error a "errores y logs" ---
            sche_channel.basic_publish(
                exchange="",
                routing_key=LOG_QUEUE,
                body=json.dumps(error_msg),  # --- mensaje en formato JSON ---
                properties=pika.BasicProperties(delivery_mode=2),
            )


if "__main__" == __name__:
    main()
