import pika, json, subprocess, sys
from datetime import datetime as dtime

# --- colas a preparar ---
ERROR_QUEUE = "error_queue"
# --- medios disponibles ---
medios = [
    "biobiochile"
]
# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
sche_channel = connection.channel()
# --- declaración de la cola de error ---
sche_channel.queue_declare(queue=ERROR_QUEUE, durable=True)

def main():
    # --- se recibe el medio el cual se quiere crawlear por argumento --- 
    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
    else:
        try:
            # --- llamar al crawler con el medio ---
            medio = sys.argv[1]
            if(medio not in medios):
                print("No existe el medio ingresado")
            else:
                # --- crear scraper (el cual espera a mensajes de crawler) ---
                scrap_process = subprocess.Popen(  ['python',
                                                    '../scraper/scraper_biobio.py'])
                # --- crear crawler ---
                crawl_process = subprocess.Popen(  ['python',
                                                    '../Crawler/crawler_biobio.py',
                                                    medio])
                # --- se esperan a los procesos para continuar ---
                crawl_process.wait(); scrap_process.wait()

        # --- FALLO DEL SCHEDULER ---
        except Exception as e:
            # --- se genera el mensaje de error ---
            error_msg = {
                "from": "scheduler", # agregar esto quizás?
                "time_error": str(dtime.now().timestamp()), # en timestamp
                "state": "error",
                "error": str(e)
            }
            # --- se envia el mensaje de error a "errores y logs" ---
            sche_channel.basic_publish(
                exchange='',
                routing_key=ERROR_QUEUE,
                body=json.dumps(error_msg), # --- mensaje en formato JSON ---
                properties=pika.BasicProperties(
                    delivery_mode=2
                )
            )

if("__main__" == __name__):
    main()