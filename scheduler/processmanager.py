import sys
import subprocess

class ProcessManager:
    def __init__(self, error_callback=None):
        self.error_callback = error_callback

    def _execute_popen(self, command, name):
        """
        Método privado que gestiona las llamadas
        subprocess, según el comando provisto.
        """
        try:
            proc = subprocess.Popen(command)
            return proc
        except Exception as e:
            msg = f"ProcessManager no pudo lanzar el subproceso {name}. Excepción: {str(e)}"
            if self.error_callback:
                self.error_callback(msg)
            return None

    def launch_module(self, module_path, name, args=None):
        """
        Método para lanzar un módulo específico
        de Python, con flag -m

        Recibe la ruta del módulo (con puntos, sin .py)
        Ej: logger.logger
        Y recibe también el nombre del módulo
        """
        if args is None:
            args = []
        command = [sys.executable, "-m", module_path] + args
        return self._execute_popen(command, name)

    def launch_script(self, script_path, name, args=None):
        """
        Método para lanzar un script de Python,
        sin la flag -m y directamente desde la
        ruta natural.
        Recibe la ruta del script y el nombre.
        """
        if args is None:
            args = []
        command = [sys.executable, script_path] + args
        return self._execute_popen(command, name)

    def terminate_process(self, proc, name, timeout=10):
        """
        Enviar terminate, esperar a que cierre;
        si se supera el timeout de espera, kill.
        """
        if not proc or proc.poll() is not None:
            return # proceso ya muerto
        try:
            print(f"[ProcessManager] Deteniendo {name}...")
            proc.terminate()
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"[ProcessManager] {name} no responde. Forzando con kill...")
            proc.kill()
            proc.wait()
        except Exception as e:
            msg = f"ProcessManager no pudo cerrar el subproceso {name}. Excepción: {str(e)}"
            if self.error_callback:
                self.error_callback(msg)
