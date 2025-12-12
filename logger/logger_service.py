import functools
import json
from datetime import datetime

from logger import logs_operations
from logger.queue_key_config import QueueKeyConfig as Config


class LoggerService:
    def __init__(self, working_batch_id, channel):
        self._working_batch_id = working_batch_id
        self._channel = channel
        self._terminating = False
        self._last_message_time = datetime.now()
        self._idle_timeout = 120  # Cerrar si no hay mensajes por 2 minutos

        self._basic_queue_to_key = {
            Config.QUEUE_SCHEDULER_LOGS: Config.KEY_SCHEDULER_ERRORS,
            Config.QUEUE_CRAWLER_LOGS: Config.KEY_CRAWLER_ERRORS,
            Config.QUEUE_SCRAPING_LOGS: Config.KEY_SCRAPING_RESULTS,
        }  # asocia cola de RabbitMQ -> lista en Redis (logs genéricos)

        # Para mensajes de CONTROL (logs especiales)
        self._control_queue = Config.QUEUE_CONTROL  # Nombre de cola RabbitMQ
        self._control_key = Config.KEY_CONTROL  # Key a lista en Redis

    def run(self):
        print("[Logger] En ejecución...")
        self._setup_queues()

        # Consumidores genéricos de logs
        for rabbit_queue, redis_list in self._basic_queue_to_key.items():
            callback = functools.partial(self._handle_log_message, redis_key=redis_list)
            self._channel.basic_consume(
                queue=rabbit_queue, on_message_callback=callback
            )

        # Consumidor de control
        self._channel.basic_consume(
            queue=self._control_queue,
            on_message_callback=self._handle_control_message,
        )

        # Empezar a consumir
        self._running = True
        while self._running:
            self._channel.connection.process_data_events(time_limit=1.0)
            
            # Si recibió señal de terminar, verificar si puede cerrarse
            if self._terminating:
                self._verificar_condicion_cierre()
            else:
                # Si no ha recibido señal pero lleva mucho tiempo sin mensajes, cerrarse igual
                idle_time = (datetime.now() - self._last_message_time).total_seconds()
                if idle_time > self._idle_timeout and self._are_queues_empty():
                    print(f"[Logger] Sin mensajes por {idle_time:.0f}s y colas vacías. Cerrando automáticamente...")
                    self._terminating = True
                    self._verificar_condicion_cierre()

        print("[Logger] Terminando ejecución...")

    def _setup_queues(self):
        """
        Declarar las colas antes de empezar a consumir
        """
        for queue in self._basic_queue_to_key.keys():
            self._channel.queue_declare(queue=queue, durable=False, auto_delete=True)
        self._channel.queue_declare(
            queue=self._control_queue, durable=False, auto_delete=True
        )

    def _handle_log_message(self, ch, method, properties, body, redis_key):
        """
        Método de callback para los logs genéricos.
        Es decir, todos los logs que corresponden a:
            1. Errores de scheduler
            2. Errores de crawling
            3. Resultados de scraping
        """
        try:
            msg = json.loads(body)
            msg["id_logging_process"] = self._working_batch_id
            logs_operations.anexar_log(msg, redis_key)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self._last_message_time = datetime.now()  # Actualizar timestamp
        except Exception as e:
            print(f"[Logger] Error al registrar mensaje en {redis_key}: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _handle_control_message(self, ch, method, properties, body):
        """
        Método de callback para los mensajes de control.
        Crítico para el funcionamiento del logger.
        """
        try:
            msg = json.loads(body)
            if msg.get("action") == "start_batch":
                # Se inició una nueva tanda de loggeo, borrar logs previos
                print("[Logger] Se ha recibido start_batch.")
                self._clear_all_logs()
                self._last_message_time = datetime.now()  # Reiniciar timer
            elif msg.get("action") == "end_batch_received":
                # Se recibió señal para concluir el proceso de loggeo
                print("[Logger] Se ha recibido end_batch_received.")
                self._terminating = True
            logs_operations.anexar_log(msg, self._control_key)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self._last_message_time = datetime.now()  # Actualizar timestamp
        except Exception as e:
            print(f"[Logger] Error al registrar mensaje en {self._control_key}: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _clear_all_logs(self):
        for redis_list in self._basic_queue_to_key.values():
            logs_operations.clear_logs_list(redis_list)
        logs_operations.clear_logs_list(self._control_key)

    def _verificar_condicion_cierre(self):
        if self._are_queues_empty():
            self._channel.stop_consuming()
            print("[Logger] Se ha dejado de escuchar.")
            self._anexar_end_batch_completed()
            print("[Logger] end_batch_completed anexado a los logs.")
            self._running = False
        else:
            pass

    def _are_queues_empty(self):
        try:
            queues = list(self._basic_queue_to_key.keys()) + [self._control_queue]
            for queue_name in queues:
                if (
                    self._channel.queue_declare(
                        queue=queue_name, passive=True
                    ).method.message_count
                    > 0
                ):  # si el message_count no es nulo, arrojar False
                    print(f"[Logger] La cola {queue_name} aún no está vacía.")
                    return False
            print("[Logger] Todas las colas del Logger se han vaciado.")
            return True  # se llega aquí si ninguna cola tiene mensajes pendientes
        except Exception as e:
            print(f"[Logger] Ocurrió un error al verificar colas: {e}")
            return False

    def _anexar_end_batch_completed(self):
        msg = {
            "id_logging_process": self._working_batch_id,
            "action": "end_batch_completed",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        logs_operations.anexar_log(msg, self._control_key)
