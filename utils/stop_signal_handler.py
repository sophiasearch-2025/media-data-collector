import signal

"""
Clase genérica que maneja señales de detención,
aplicable a cualquier proceso que siga la lógica
de consumir todos los mensajes en una cola (singular)
antes de finalizar dicho proceso.
Es decir, verificar que la cola esté vacía antes de
cerrar.

Se instancia con:
    - un canal de RabbitMQ,
    - un nombre de cola RabbitMQ,
    - un nombre de proceso (para trazado en print).
"""


class StopSignalHandler:
    def __init__(self, channel, queue_name, proc_name):
        self.channel = channel
        self.queue_name = queue_name
        self.proc_name = proc_name
        self._stop_signal_received = False

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        print(f"[{self.proc_name}] Recibida señal para detener.")
        self._stop_signal_received = True

    def _is_queue_empty(self):
        try:
            message_count = self.channel.queue_declare(
                queue=self.queue_name, passive=True
            ).method.message_count
            return message_count == 0
        except Exception as e:
            print(f"[{self.proc_name}] Error al verificar cola {self.queue_name}: {e}")
            return False

    def _should_stop(self):
        return self._stop_signal_received and self._is_queue_empty()
