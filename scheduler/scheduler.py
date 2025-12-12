import signal
import sys
import time
from datetime import datetime as dtime
from enum import Enum, auto

from scheduler.processmanager import ProcessManager
from scheduler.scheduler_queue_utils import wait_for_scraper_queue_empty, wait_for_logging_queues_empty
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

    # Finalización de tareas
    # para la detención forzada-controlada
    # (Mid-ejecución: por acción de usuario,
    # o bien, por error del scheduler)
    INTERRUPT_RECEIVED = auto()
    STOPPING_CRAWLER = auto()
    STOPPING_SCRAPERS = auto()
    STOPPING_SENDER = auto()
    STOPPING_LOGGER = auto()

    SHUTDOWN_COMPLETE = auto()


class Scheduler:
    def __init__(self, medio, n_scrapers):
        self._medio: str = medio
        self._n_scrapers: int = n_scrapers
        self._running: bool = True
        self._working_batch_id: int = int(dtime.now().timestamp())

        self._stage = SchedulerStages.INIT

        # Handlers para las señales de shutdown
        signal.signal(signal.SIGINT, self._receive_interrupt)
        signal.signal(signal.SIGTERM, self._receive_interrupt)

        # Atributos gestión de procesos
        self._process_manager = ProcessManager(error_callback=self._handle_error)
        self._proc_logger = None
        self._proc_sender = None
        self._proc_crawler = None
        self._proc_scrapers = {}

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
        time.sleep(10)
        if send_start_batch: # solo enviar start_batch en el primer launch, no en reinicios
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
            scraper_id = i+1
            proc = self._process_manager.launch_module(
                ruta_scraper, f"Scraper {scraper_id}"
            )
            if proc:
                self._proc_scrapers[scraper_id] = proc

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

    def run(self):
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
                    self._stage = SchedulerStages.CRAWLING_COMPLETE
                    print("[Scheduler] Ha registrado que Crawler concluyó sus tareas")
                    print("[Scheduler] Esperando a que scrapers terminen de procesar scraper_queue...")
                    wait_for_scraper_queue_empty(self._proc_scrapers, self._medio, self)
                    self._forceful_stop_subprocesos()
                    break
                time.sleep(1)

        except Exception as e:
            self._handle_error(f"[Scheduler] Error crítico en Scheduler: {str(e)}")
            self._forceful_stop_subprocesos()

    def _receive_interrupt(self, signum, frame):
        """
        Recibir signal INT/TERM y
        lanzar `_forceful_stop_subprocesos`
        """
        print(
            f"\n[Scheduler] Recibida señal {signum} para detener su orquestador. Cerrando..."
        )
        self._running = False
        self._stage = SchedulerStages.INTERRUPT_RECEIVED
        self._forceful_stop_subprocesos()

    def _forceful_stop_subprocesos(self):
        """
        Para la detención forzada-controlada
        (mid-ejecución),
        por acción de usuario, o bien, por error
        del scheduler.
        El logger es lo último que se cierra.
        """
        print("[Scheduler] Cerrando subprocesos...")

        self._stage = SchedulerStages.STOPPING_CRAWLER
        self._process_manager.terminate_process(self._proc_crawler, "Crawler")
        self._stage = SchedulerStages.STOPPING_SCRAPERS
        for scraper_id, proc in self._proc_scrapers.items():
            self._process_manager.terminate_process(proc, f"Scraper {scraper_id}")
        self._stage = SchedulerStages.STOPPING_SENDER
        self._process_manager.terminate_process(self._proc_sender, "Sender")

        self._stage = SchedulerStages.STOPPING_LOGGER
        # Señalizar el fin de logging batch
        # Señalizar al logger que debe empezar a cerrar (antes de esperar colas)
        try:
            logging_batch_send(self._working_batch_id, "end_batch_received", dtime.now())
            print("Scheduler: Señal 'end_batch_received' enviada al logger")
        except Exception as e:
            print(f"Scheduler: Error enviando end_batch_received: {e}")

        # Ahora que los scrapers están muertos y logger sabe que debe cerrar,
        # esperar que las colas de logging se vacíen
        print("Scheduler: Esperando que logger procese mensajes restantes...")
        wait_for_logging_queues_empty(self._proc_logger, self)

        # Dar tiempo al logger para cerrar gracefully antes de matarlo
        if self._proc_logger and self._proc_logger.poll() is None:
            print("Scheduler: Esperando 10 segundos para que logger cierre solo...")
            time.sleep(10)

        # Si el logger todavía está vivo, matarlo
        if self._proc_logger:
            self._process_manager.terminate_process(self._proc_logger, "Logger", 10)

        print("[Scheduler] Cierre completado.")
        self._stage = SchedulerStages.SHUTDOWN_COMPLETE
        sys.exit(0)
