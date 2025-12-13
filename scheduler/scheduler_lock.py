import utils.redis_utils as redis_utils


class SchedulerLock:
    def __init__(self, medio: str):
        self._medio = medio
        self._redis_client = redis_utils.get_redis_client()
        self._lock_key = "scheduler_lock"  # llave redis

    def acquire(self, owner_id: str) -> bool:
        """
        Intenta adquirir el lock de ejecución.
        Retorna True si tuvo éxito (el lock estaba libre).
        Retorna False si falló (ya existe una ejecución).
        """
        try:
            # set(nx=True) es atómico: solo escribe si la clave NO existe
            acquired = self._redis_client.set(self._lock_key, owner_id, nx=True)
            if acquired:
                print(
                    f"[SchedulerLock] Lock de ejecución adquirido para '{self._medio}' (Owner: {owner_id})."
                )
                return True
            else:
                current_owner = self._redis_client.get(self._lock_key)
                if isinstance(current_owner, bytes):
                    current_owner = current_owner.decode("utf-8")

                print(
                    f"[SchedulerLock] BLOQUEADO: Ya existe una ejecución activa para '{self._medio}' (Owner actual: {current_owner})."
                )
                return False
        except Exception as e:
            print(
                f"[Lock] Error crítico conectando a Redis al intentar adquirir lock: {e}"
            )
            # Impedir arranque si falla conexión Redis
            # para evitar duplicidad ciega.
            return False

    def release(self):
        """
        Libera el lock eliminando la clave en Redis.
        """
        try:
            self._redis_client.delete(self._lock_key)
            print("[SchedulerLock] Lock de ejecución liberado.")
        except Exception as e:
            print(f"[SchedulerLock] Error liberando lock en Redis: {e}")
