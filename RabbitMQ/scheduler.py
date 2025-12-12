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
# --- declaración de la cola de error (durable=False para coincidir con logger) ---
sche_channel.queue_declare(queue=LOG_QUEUE, durable=False, auto_delete=True)


def proceso_send_datos():
    # --- crear el listener de envio de datos ---
    subprocess.Popen([sys.executable, "RabbitMQ/send_data.py"])


def proceso_scrapper(n):
    # --- crear listener del scraper (el cual espera a mensajes de crawler) ---
    for _ in range(int(n)):
        subprocess.Popen([sys.executable, "scraper/scraper_biobio.py"])


def proceso_crawler(medio):
    # --- crear listener del crawler ---
    crawl_process = subprocess.Popen([sys.executable, "Crawler/crawler.py", medio])
    # --- se esperan a los procesos para continuar ---
    crawl_process.wait()


def main():
    # --- crear listener del logger inicialmente (prioritario) ---
    starting_time = dtime.now()
    id_logging_process = int(
        starting_time.timestamp()
    )  # identificador distintivo del proceso de logging
    proceso_logging = subprocess.Popen(
        [sys.executable, "-m", "logger.logger", "--id", str(id_logging_process)]
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
            stage = "Esperando finalización de scrapers"
            print("[scheduler] Crawler completado. Esperando a que los scrapers terminen...")
            
            # Esperar a que la cola de scraper esté vacía
            import time
            rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
            rabbit_ch = rabbit_conn.channel()
            
            # Primero esperar a que scraper_queue esté vacía
            while True:
                queue_state = rabbit_ch.queue_declare(queue="scraper_queue", passive=True)
                messages_pending = queue_state.method.message_count
                if messages_pending == 0:
                    print("[scheduler] Cola de scrapers vacía. Esperando 5 segundos adicionales...")
                    time.sleep(5)
                    # Verificar nuevamente por si llegaron más mensajes
                    queue_state = rabbit_ch.queue_declare(queue="scraper_queue", passive=True)
                    if queue_state.method.message_count == 0:
                        break
                else:
                    print(f"[scheduler] Esperando... {messages_pending} mensajes pendientes en scraper_queue")
                    time.sleep(2)
            
            # Ahora esperar a que las colas de logging también estén vacías
            print("[scheduler] Esperando a que las colas de logging se vacíen...")
            log_queues = ["scraping_log_queue", "crawler_log_queue", "scheduler_log_queue"]
            max_wait = 60  # máximo 60 segundos esperando las colas de log
            wait_time = 0
            
            while wait_time < max_wait:
                all_empty = True
                for queue_name in log_queues:
                    try:
                        queue_state = rabbit_ch.queue_declare(queue=queue_name, passive=True)
                        msg_count = queue_state.method.message_count
                        if msg_count > 0:
                            print(f"[scheduler] {msg_count} mensajes pendientes en {queue_name}")
                            all_empty = False
                    except Exception as e:
                        print(f"[scheduler] Error verificando {queue_name}: {e}")
                
                if all_empty:
                    print("[scheduler] Todas las colas de logging vacías!")
                    break
                
                time.sleep(2)
                wait_time += 2
            
            if wait_time >= max_wait:
                print("[scheduler] ADVERTENCIA: Timeout esperando colas de logging. Continuando de todas formas...")
            
            rabbit_ch.close()
            rabbit_conn.close()
            
            stage = "Señalizar fin de logging"
            print("[scheduler] Todos los scrapers completados. Enviando señal de finalización al logger...")
            logging_batch_send(id_logging_process, "end_batch_received", dtime.now())
            print("[scheduler] Esperando a que el logger procese los mensajes finales...")
            proceso_logging.wait(timeout=30)  # Esperar máximo 30 segundos
            print("[scheduler] Logger finalizado correctamente")

        # --- FALLO DEL SCHEDULER ---
        except subprocess.TimeoutExpired:
            print("[scheduler] Logger no terminó a tiempo, forzando cierre...")
            proceso_logging.kill()
        except KeyboardInterrupt:
            print("\n[scheduler] Interrupción manual detectada. Finalizando logger...")
            logging_batch_send(id_logging_process, "end_batch_received", dtime.now())
            proceso_logging.wait(timeout=10)
        except Exception as e:
            # --- se envia el mensaje de error a "errores y logs" ---
            error_send(
                "scheduler",
                dtime.now(),
                str(e),
                medio,
                stage,
            )
            # Intentar finalizar el logger de todas formas
            try:
                logging_batch_send(id_logging_process, "end_batch_received", dtime.now())
                proceso_logging.wait(timeout=10)
            except:
                pass


if "__main__" == __name__:
    main()
