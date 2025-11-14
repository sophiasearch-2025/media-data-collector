import json
import redis
import utils.redis_utils as redis_utils

##### Anexar un log_data a la lista list_name
##### Retorna True si la inserción es exitosa, False si falló
def anexar_log(log_data: dict, list_name: str):
    redis_client = redis_utils.get_redis_client()
    try:
        redis_client.lpush(list_name, json.dumps(log_data))
        return True
    except redis.ConnectionError as e:
        print(
            f"Falló la conexión con Redis: {e}. No pudo loggearse {log_data} en {list_name}"
        )
    except redis.TimeoutError as e:
        print(
            f"Timeout en la operación con Redis: {e}. No pudo loggearse {log_data} en {list_name}"
        )
    except Exception as e:
        print(
            f"Error inesperado al loggear con Redis: {e}. No pudo loggearse {log_data} en {list_name}"
        )
    return False

##### --- limpiar lista de logs, borra toda log entry ---
##### --- retorna True si la inserción es exitosa, False si falló ---
def clear_logs_list(list_name: str):
    redis_client = redis_utils.get_redis_client()
    try:
        redis_client.delete(list_name)
        return True
    except redis.ConnectionError as e:
        print(f"Falló la conexión con Redis: {e}. No pudo vaciarse {list_name}")
    except redis.TimeoutError as e:
        print(f"Timeout en la operación con Redis: {e}. No pudo vaciarse {list_name}")
    except Exception as e:
        print(
            f"Error inesperado al vaciar lista en Redis: {e}. No pudo vaciarse {list_name}"
        )
    return False
