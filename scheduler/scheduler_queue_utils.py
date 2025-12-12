"""
Utilidades para verificación de colas de RabbitMQ en el scheduler.
Separadas para evitar conflictos con el código original del scheduler.
"""

import json
import os
import time
import requests
from datetime import datetime

# Bloqueo de archivos multiplataforma
if os.name == "nt":  # Windows
    import msvcrt
    def file_lock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def file_unlock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:  # Linux/Unix/MacOS
    import fcntl
    def file_lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    def file_unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def initialize_scraper_progress(medio):
    """
    Inicializa/resetea el archivo scraper_progress.json para un medio específico.
    Usa file locking para evitar race conditions con múltiples procesos.
    
    Args:
        medio: Nombre del medio (biobiochile, latercera, etc.)
    """
    progress_file = "metrics/scraper_progress.json"
    os.makedirs("metrics", exist_ok=True)
    
    # Reintentar si hay problemas de acceso concurrente
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Usar 'a+' para crear si no existe, o abrir si existe
            with open(progress_file, "a+", encoding="utf-8") as f:
                # Adquirir lock exclusivo
                file_lock(f)
                
                try:
                    # Leer contenido existente
                    f.seek(0)
                    content = f.read()
                    if content.strip():
                        existing_progress = json.loads(content)
                    else:
                        existing_progress = {}
                except (json.JSONDecodeError, ValueError):
                    existing_progress = {}
                
                # Inicializar/resetear solo el medio actual
                existing_progress[medio] = {
                    "total_articulos_exitosos": 0,
                    "total_articulos_fallidos": 0,
                    "duracion_promedio_ms": 0,
                    "articulos_por_minuto": 0,
                    "ultima_actualizacion": "",
                    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Sobrescribir archivo
                f.seek(0)
                f.truncate()
                json.dump(existing_progress, f, ensure_ascii=False, indent=2)
                
                # Liberar lock (automático al cerrar)
                file_unlock(f)
                
            print(f"[scheduler_queue_utils] Archivo {progress_file} inicializado para medio '{medio}'")
            return True
            
        except IOError as e:
            if attempt < max_retries - 1:
                time.sleep(0.1)
            else:
                print(f"[scheduler_queue_utils] Error inicializando scraper_progress.json después de {max_retries} intentos: {e}")
                return False
    
    return False


def get_queue_details(queue_name="scraper_queue"):
    """
    Obtiene detalles completos de la cola desde RabbitMQ Management API.
    Incluye mensajes ready, unacked, consumers, etc.
    
    Returns:
        dict con 'messages_ready', 'messages_unacknowledged', 'consumers'
        o None si hay error
    """
    try:
        url = f"http://localhost:15672/api/queues/%2F/{queue_name}"
        auth = ("guest", "guest")  # credenciales por defecto
        
        response = requests.get(url, auth=auth, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                'messages_ready': data.get('messages_ready', 0),
                'messages_unacknowledged': data.get('messages_unacknowledged', 0),
                'consumers': data.get('consumers', 0),
                'total': data.get('messages', 0)
            }
    except Exception as e:
        print(f"Scheduler: Error consultando Management API: {e}")
    return None


def wait_for_scraper_queue_empty(proc_scrapers, medio, running_flag):
    """
    Espera a que la cola de scraper esté vacía (scrapers terminaron de procesar).

    Args:
        proc_scrapers: Lista de procesos scraper
        medio: Nombre del medio (biobiochile, latercera)
        running_flag: Referencia al flag self._running del scheduler
    """
    try:
        import pika

        rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        rabbit_ch = rabbit_conn.channel()

        # Verificar si hay scrapers vivos
        if isinstance(proc_scrapers, dict):
            procesos = list(proc_scrapers.values())
        else:
            procesos = proc_scrapers

        scrapers_alive = sum(1 for p in procesos if p.poll() is None)
        print(f"[Scheduler] {scrapers_alive} scrapers activos")

        if scrapers_alive == 0:
            print(
                "[Scheduler] ADVERTENCIA - No hay scrapers vivos para procesar la cola"
            )
            rabbit_ch.close()
            rabbit_conn.close()
            return

        # Esperar un poco para que los scrapers empiecen a consumir
        print("Scheduler: Dando 5 segundos a los scrapers para empezar a consumir...")
        time.sleep(5)

        # Primero esperar scraper_queue
        print("Scheduler: Verificando scraper_queue...")
        max_wait = 600  # 10 minutos máximo para sitios grandes
        wait_time = 0
        last_count = -1
        stall_count = 0

        while wait_time < max_wait and running_flag._running:
            try:
                queue_state = rabbit_ch.queue_declare(
                    queue="scraper_queue", passive=True
                )
                current_count = queue_state.method.message_count

                # Verificar si los scrapers siguen vivos
                scrapers_alive = sum(1 for p in procesos if p.poll() is None)
                if scrapers_alive == 0 and current_count > 0:
                    print(
                        f"Scheduler: ADVERTENCIA - Scrapers murieron con {current_count} mensajes sin procesar"
                    )
                    break

                if current_count == 0:
                    # Esperar 5 segundos adicionales para confirmar que está vacía
                    print(
                        "Scheduler: scraper_queue vacía, verificando en 5 segundos..."
                    )
                    time.sleep(5)
                    queue_state = rabbit_ch.queue_declare(
                        queue="scraper_queue", passive=True
                    )
                    if queue_state.method.message_count == 0:
                        print("Scheduler: scraper_queue confirmada vacía")

                        # Verificar que los scrapers hayan terminado de procesar comparando con crawler
                        print(
                            "Scheduler: Verificando que scrapers terminaron de procesar..."
                        )
                        crawler_file = f"Crawler/{medio}.csv"
                        scraper_progress_file = "metrics/scraper_progress.json"

                        urls_crawler = 0
                        urls_procesadas = 0

                        try:
                            import csv

                            if os.path.exists(crawler_file):
                                with open(crawler_file, "r", encoding="utf-8") as f:
                                    urls_crawler = (
                                        sum(1 for _ in csv.reader(f)) - 1
                                    )  # -1 por header
                                print(
                                    f"Scheduler: Crawler encontró {urls_crawler} URLs"
                                )

                            if os.path.exists(scraper_progress_file):
                                with open(
                                    scraper_progress_file, "r", encoding="utf-8"
                                ) as f:
                                    progress = json.load(f)
                                    urls_procesadas = progress.get("urls_procesadas", 0)
                                print(
                                    f"Scheduler: Scrapers procesaron {urls_procesadas} URLs"
                                )

                            if urls_crawler > 0 and urls_procesadas < urls_crawler:
                                diff = urls_crawler - urls_procesadas
                                print(
                                    f"Scheduler: ADVERTENCIA - Faltan {diff} URLs por procesar, esperando 30 segundos más..."
                                )
                                time.sleep(30)
                                # Recargar progreso después de esperar
                                if os.path.exists(scraper_progress_file):
                                    with open(
                                        scraper_progress_file, "r", encoding="utf-8"
                                    ) as f:
                                        progress = json.load(f)
                                        urls_procesadas = progress.get(
                                            "urls_procesadas", 0
                                        )
                                    print(
                                        f"Scheduler: Scrapers ahora tienen {urls_procesadas} URLs procesadas"
                                    )

                        except Exception as e:
                            print(f"Scheduler: Error verificando progreso: {e}")

                        break
                    else:
                        print(
                            f"Scheduler: Llegaron {queue_state.method.message_count} mensajes nuevos, continuando..."
                        )
                        last_count = queue_state.method.message_count
                        continue

                # Detectar si la cola está estancada (no baja)
                if current_count == last_count:
                    stall_count += 1
                    if stall_count >= 10:  # 20 segundos sin cambios
                        print(
                            f"Scheduler: ADVERTENCIA - Cola estancada en {current_count} mensajes por 20 segundos"
                        )
                        break
                else:
                    stall_count = 0
                    print(
                        f"Scheduler: {current_count} mensajes en scraper_queue ({scrapers_alive} scrapers activos)"
                    )

                last_count = current_count
            except Exception as e:
                print(f"Scheduler: Error verificando cola: {e}")
                break
            time.sleep(2)
            wait_time += 2

        if wait_time >= max_wait:
            print(
                "Scheduler: ADVERTENCIA - Timeout de 10 minutos esperando scraper_queue"
            )

        rabbit_ch.close()
        rabbit_conn.close()

    except Exception as e:
        print(f"Scheduler: Error verificando scraper_queue: {e}")


def wait_for_logging_queues_empty(proc_logger, running_flag):
    """
    Espera a que las colas de logging estén vacías (logger procesó todos los mensajes).

    Args:
        proc_logger: Proceso del logger
        running_flag: Referencia al flag self._running del scheduler
    """
    # Verificar si el logger está vivo
    if not proc_logger or proc_logger.poll() is not None:
        print(
            "Scheduler: ADVERTENCIA - Logger no está ejecutándose, no puede consumir mensajes"
        )
        print("Scheduler: Saltando verificación de colas de logging")
        return

    try:
        import pika

        rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        rabbit_ch = rabbit_conn.channel()

        print("Scheduler: Verificando colas de logging (logger activo)...")
        log_queues = ["scraping_log_queue", "crawler_log_queue", "scheduler_log_queue"]
        max_wait_logs = (
            300  # 5 minutos máximo para logs (puede haber muchos mensajes acumulados)
        )
        wait_time = 0

        while wait_time < max_wait_logs and running_flag._running:
            # Verificar que el logger siga vivo durante la espera
            if proc_logger.poll() is not None:
                print(
                    "Scheduler: ADVERTENCIA - Logger murió durante la espera de colas"
                )
                break

            all_empty = True
            for queue_name in log_queues:
                try:
                    queue_state = rabbit_ch.queue_declare(
                        queue=queue_name, passive=True
                    )
                    msg_count = queue_state.method.message_count
                    if msg_count > 0:
                        print(f"Scheduler: {msg_count} mensajes en {queue_name}")
                        all_empty = False
                except Exception as e:
                    print(f"Scheduler: Error verificando {queue_name}: {e}")

            if all_empty:
                print("Scheduler: Todas las colas de logging vacías")
                break

            time.sleep(2)
            wait_time += 2

        if wait_time >= max_wait_logs:
            print("Scheduler: ADVERTENCIA - Timeout esperando colas de logging")

        rabbit_ch.close()
        rabbit_conn.close()

    except Exception as e:
        print(f"Scheduler: Error verificando colas: {e}")
