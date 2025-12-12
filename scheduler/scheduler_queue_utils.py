"""
Utilidades para verificación de colas de RabbitMQ en el scheduler.
Separadas para evitar conflictos con el código original del scheduler.
"""
import json
import os
import time


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
        scrapers_alive = sum(1 for p in proc_scrapers if p.poll() is None)
        print(f"Scheduler: {scrapers_alive} scrapers activos")
        
        if scrapers_alive == 0:
            print("Scheduler: ADVERTENCIA - No hay scrapers vivos para procesar la cola")
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
                queue_state = rabbit_ch.queue_declare(queue="scraper_queue", passive=True)
                current_count = queue_state.method.message_count
                
                # Verificar si los scrapers siguen vivos
                scrapers_alive = sum(1 for p in proc_scrapers if p.poll() is None)
                if scrapers_alive == 0 and current_count > 0:
                    print(f"Scheduler: ADVERTENCIA - Scrapers murieron con {current_count} mensajes sin procesar")
                    break
                
                if current_count == 0:
                    # Esperar 5 segundos adicionales para confirmar que está vacía
                    print("Scheduler: scraper_queue vacía, verificando en 5 segundos...")
                    time.sleep(5)
                    queue_state = rabbit_ch.queue_declare(queue="scraper_queue", passive=True)
                    if queue_state.method.message_count == 0:
                        print("Scheduler: scraper_queue confirmada vacía")
                        
                        # Verificar que los scrapers hayan terminado de procesar comparando con crawler
                        print("Scheduler: Verificando que scrapers terminaron de procesar...")
                        crawler_file = f"Crawler/{medio}.csv"
                        scraper_progress_file = "metrics/scraper_progress.json"
                        
                        urls_crawler = 0
                        urls_procesadas = 0
                        
                        try:
                            import csv
                            if os.path.exists(crawler_file):
                                with open(crawler_file, 'r', encoding='utf-8') as f:
                                    urls_crawler = sum(1 for _ in csv.reader(f)) - 1  # -1 por header
                                print(f"Scheduler: Crawler encontró {urls_crawler} URLs")
                            
                            if os.path.exists(scraper_progress_file):
                                with open(scraper_progress_file, 'r', encoding='utf-8') as f:
                                    progress = json.load(f)
                                    urls_procesadas = progress.get('urls_procesadas', 0)
                                print(f"Scheduler: Scrapers procesaron {urls_procesadas} URLs")
                            
                            if urls_crawler > 0 and urls_procesadas < urls_crawler:
                                diff = urls_crawler - urls_procesadas
                                print(f"Scheduler: ADVERTENCIA - Faltan {diff} URLs por procesar, esperando 30 segundos más...")
                                time.sleep(30)
                                # Recargar progreso después de esperar
                                if os.path.exists(scraper_progress_file):
                                    with open(scraper_progress_file, 'r', encoding='utf-8') as f:
                                        progress = json.load(f)
                                        urls_procesadas = progress.get('urls_procesadas', 0)
                                    print(f"Scheduler: Scrapers ahora tienen {urls_procesadas} URLs procesadas")
                            
                        except Exception as e:
                            print(f"Scheduler: Error verificando progreso: {e}")
                        
                        break
                    else:
                        print(f"Scheduler: Llegaron {queue_state.method.message_count} mensajes nuevos, continuando...")
                        last_count = queue_state.method.message_count
                        continue
                
                # Detectar si la cola está estancada (no baja)
                if current_count == last_count:
                    stall_count += 1
                    if stall_count >= 10:  # 20 segundos sin cambios
                        print(f"Scheduler: ADVERTENCIA - Cola estancada en {current_count} mensajes por 20 segundos")
                        break
                else:
                    stall_count = 0
                    print(f"Scheduler: {current_count} mensajes en scraper_queue ({scrapers_alive} scrapers activos)")
                
                last_count = current_count
            except Exception as e:
                print(f"Scheduler: Error verificando cola: {e}")
                break
            time.sleep(2)
            wait_time += 2
        
        if wait_time >= max_wait:
            print("Scheduler: ADVERTENCIA - Timeout de 10 minutos esperando scraper_queue")
        
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
        print("Scheduler: ADVERTENCIA - Logger no está ejecutándose, no puede consumir mensajes")
        print("Scheduler: Saltando verificación de colas de logging")
        return
    
    try:
        import pika
        
        rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        rabbit_ch = rabbit_conn.channel()
        
        print("Scheduler: Verificando colas de logging (logger activo)...")
        log_queues = ["scraping_log_queue", "crawler_log_queue", "scheduler_log_queue"]
        max_wait_logs = 300  # 5 minutos máximo para logs (puede haber muchos mensajes acumulados)
        wait_time = 0
        
        while wait_time < max_wait_logs and running_flag._running:
            # Verificar que el logger siga vivo durante la espera
            if proc_logger.poll() is not None:
                print("Scheduler: ADVERTENCIA - Logger murió durante la espera de colas")
                break
            
            all_empty = True
            for queue_name in log_queues:
                try:
                    queue_state = rabbit_ch.queue_declare(queue=queue_name, passive=True)
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
