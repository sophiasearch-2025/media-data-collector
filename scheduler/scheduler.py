import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime as dtime
from enum import Enum, auto

from scheduler.processmanager import ProcessManager
import utils.environ_var as ev
from logger.queue_sender_generic_error import error_send
from logger.queue_sender_logger_ctrl import logging_batch_send

from utils.config_scrapers import SCRAPER_MAP

class SchedulerStages(Enum):
    # Fases de inicio
    INIT = auto()
    START_LOGGER = auto()
    START_SENDER = auto()
    START_CRAWLER = auto()
    START_SCRAPERS = auto()

    # Ejecución
    RUNNING_MAIN_LOOP = auto()

    # Finalización de las tareas
    # para la detención natural
    CRAWLING_COMPLETE = auto()
    SCRAPING_COMPLETE = auto()
    SENDING_COMPLETE = auto()
    LOGGING_COMPLETE = auto()

    CRAWLER_FINISHED = auto() # refactorizar por `CRAWLING_COMPLETE`.

    # Finalización de tareas
    # para la detención forzada-controlada
    # (Mid-ejecución: por acción de usuario,
    # o bien, por error del scheduler)
    INTERRUPT_RECEIVED = auto()
    CRAWLING_STOPPED = auto()
    SCRAPING_STOPPED = auto()
    SENDING_STOPPED = auto()
    LOGGING_STOPPED = auto()

    SHUTDOWN_SIGNAL_RECEIVED = auto() # suprimir
    SHUTDOWN_SUBPROCESOS = auto() # suprimir
    SHUTDOWN_COMPLETE = auto()


class Scheduler:
    def __init__(self, medio, n_scrapers):
        self._medio: str = medio
        self._n_scrapers: int = n_scrapers
        self._running: bool = True
        self._working_batch_id: int = int(dtime.now().timestamp())

        self._stage = SchedulerStages.INIT

        # Handlers para las señales de shutdown
        signal.signal(signal.SIGINT, self._signal_shutdown)
        signal.signal(signal.SIGTERM, self._signal_shutdown)

        # Atributos gestión de procesos
        self._process_manager = ProcessManager(error_callback=self._handle_error)
        self._proc_logger = None
        self._proc_sender = None
        self._proc_crawler = None
        self._proc_scrapers = []

    def _handle_error(self, error_msg):
        """
        Envía mensaje de error a RabbitMQ y lo imprime en consola.
        """
        try:
            print(f"Error de Scheduler: {error_msg}")
            # Enviar mensaje de error al logger (por RabbitMQ)
            error_send(
                "scheduler", dtime.now(), error_msg, self._medio, self._stage.name
            )
        except Exception as e:
            print(f"Scheduler: Fallo crítico al intentar enviar error a RabbitMQ: {e}")

    # --- STARTERS ---

    def _start_logger(self, send_start_batch=True):
        self._stage = SchedulerStages.START_LOGGER
        ruta_logger = ev.get_environ_var("LOGGER")
        self._proc_logger = self._process_manager.launch_module(ruta_logger, "Logger")
        time.sleep(1)
        
        # Solo enviar start_batch en el inicio inicial, no en reinicios
        if send_start_batch:
            try:
                logging_batch_send(self._working_batch_id, "start_batch", dtime.now())
                print("Señal 'start_batch' enviada a RabbitMQ.")
            except Exception as e:
                print(f"Advertencia: No se pudo enviar 'start_batch': {e}")

    def _start_sender(self):
        self._stage = SchedulerStages.START_SENDER
        ruta_senddata = ev.get_environ_var("SENDDATA")
        self._proc_sender = self._process_manager.launch_module(ruta_senddata, "Sender")

    def _start_crawler(self):
        self._stage = SchedulerStages.START_CRAWLER
        ruta_crawler = ev.get_environ_var("CRAWLER")
        self._proc_crawler = self._process_manager.launch_script(ruta_crawler, "Crawler")

    def _start_scrapers(self):
        self._stage = SchedulerStages.START_SCRAPERS
        ruta_scraper = self._get_scraper_module()
        for i in range(self._n_scrapers):
            proc = self._process_manager.launch_module(
                ruta_scraper, f"Scraper {i + 1}"
            )
            if proc:
                self._proc_scrapers.append(proc)

    def _get_scraper_module(self):
        """
        Busca en el mapa importado la clave
        de entorno correspondiente.
        """
        env_key = SCRAPER_MAP.get(self._medio)
        if not env_key:
            # Si se escribió mal el nombre del medio
            # o si se escribió uno que no está
            # configurado
            medios_disponibles = list(SCRAPER_MAP.keys())
            raise ValueError(
                f"El medio '{self._medio}' no está configurado.\n"
                f"Medios disponibles: {medios_disponibles}"
            )
        return ev.get_environ_var(env_key)

    def orquestar(self):
        """
        ******************************************
        Método público para iniciar la ejecución
        de la recolección de prensa, orquestando
        los procesos correspondientes.
        ******************************************
        """
        print(f"Scheduler está orquestando para el medio {self._medio}")

        try:
            self._start_logger()
            self._start_sender()
            self._start_crawler()

            if not self._proc_crawler:
                raise RuntimeError("El crawler no pudo iniciarse. Abortando operación.")

            self._start_scrapers()  # lanza un total de `_n_scrapers` (cantidad) de procesos

            self._stage = SchedulerStages.RUNNING_MAIN_LOOP
            while self._running:
                # Verificar si el logger murió inesperadamente
                if self._proc_logger and self._proc_logger.poll() is not None:
                    print("Scheduler: ADVERTENCIA - Logger murió inesperadamente, reiniciando...")
                    self._start_logger(send_start_batch=False)  # NO limpiar logs al reiniciar
                
                if self._proc_crawler and self._proc_crawler.poll() is not None:
                    self._stage = SchedulerStages.CRAWLER_FINISHED
                    print("Orquestador ha registrado que crawler concluyó sus tareas")
                    print("Scheduler: Esperando a que scrapers terminen de procesar scraper_queue...")
                    self._wait_for_scraper_queue_empty()
                    self._shutdown_subprocesos()
                    break
                time.sleep(1)

        except Exception as e:
            self._handle_error(f"Error crítico en Scheduler: {str(e)}")
            self._shutdown_subprocesos()

    def _signal_shutdown(self, signum, frame):
        """
        Recibir signal INT/TERM y lanzar shutdown
        """
        self._stage = SchedulerStages.SHUTDOWN_SIGNAL_RECEIVED
        print(
            f"\nScheduler ha recibido señal {signum} para detener su orquestador. Cerrando..."
        )
        self._running = False
        self._shutdown_subprocesos()

    def _wait_for_scraper_queue_empty(self):
        """
        Espera a que la cola de scraper esté vacía (scrapers terminaron de procesar).
        """
        try:
            import pika
            
            rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
            rabbit_ch = rabbit_conn.channel()
            
            # Verificar si hay scrapers vivos
            scrapers_alive = sum(1 for p in self._proc_scrapers if p.poll() is None)
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
            
            while wait_time < max_wait and self._running:
                try:
                    queue_state = rabbit_ch.queue_declare(queue="scraper_queue", passive=True)
                    current_count = queue_state.method.message_count
                    
                    # Verificar si los scrapers siguen vivos
                    scrapers_alive = sum(1 for p in self._proc_scrapers if p.poll() is None)
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
                            crawler_file = f"Crawler/{self._medio}.csv"
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

    def _wait_for_logging_queues_empty(self):
        """
        Espera a que las colas de logging estén vacías (logger procesó todos los mensajes).
        """
        # Verificar si el logger está vivo
        if not self._proc_logger or self._proc_logger.poll() is not None:
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
            
            while wait_time < max_wait_logs and self._running:
                # Verificar que el logger siga vivo durante la espera
                if self._proc_logger.poll() is not None:
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

    def _shutdown_subprocesos(self):
        """
        Shutdown controlado de los subprocesos.
        El logger es lo último que se cierra.
        """
        self._stage = SchedulerStages.SHUTDOWN_SUBPROCESOS
        print("Scheduler está cerrando sus subprocesos...")

        procesos_except_logger = []  # a cerrar antes que el logger

        if self._proc_crawler:
            procesos_except_logger.append(("Crawler", self._proc_crawler))
        if self._proc_sender:
            procesos_except_logger.append(("Sender", self._proc_sender))
        for i, proceso in enumerate(self._proc_scrapers):
            procesos_except_logger.append((f"Scraper {i+1}", proceso))

        for nombre, proceso in procesos_except_logger:
            self._kill_subproceso(proceso, nombre)

        # Señalizar al logger que debe empezar a cerrar (antes de esperar colas)
        try:
            logging_batch_send(self._working_batch_id, "end_batch_received", dtime.now())
            print("Scheduler: Señal 'end_batch_received' enviada al logger")
        except Exception as e:
            print(f"Scheduler: Error enviando end_batch_received: {e}")

        # Ahora que los scrapers están muertos y logger sabe que debe cerrar,
        # esperar que las colas de logging se vacíen
        print("Scheduler: Esperando que logger procese mensajes restantes...")
        self._wait_for_logging_queues_empty()

        # Dar tiempo al logger para cerrar gracefully antes de matarlo
        if self._proc_logger and self._proc_logger.poll() is None:
            print("Scheduler: Esperando 10 segundos para que logger cierre solo...")
            time.sleep(10)
        
        # Si el logger todavía está vivo, matarlo
        if self._proc_logger:
            self._kill_subproceso(self._proc_logger, "Logger")

        print("Scheduler: Cierre completo.")
        self._stage = SchedulerStages.SHUTDOWN_COMPLETE
        sys.exit(0)

    def _kill_subproceso(self, proc, nombre):
        """
        Esperar a que el proceso se cierre con
        normalidad, o bien, forzar con SIGKILL
        """
        if proc.poll() is None: # Si sigue vivo
            print(f" Terminando {nombre}...")
            try:
                proc.terminate() # SIGTERM
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print(f"{nombre} no responde. Forzando kill.")
                proc.kill() # SIGKILL
            except Exception as e:
                print(f" Error cerrando {nombre}: {e}")
