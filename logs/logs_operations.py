from datetime import datetime, time
import json
import redis
import utils.redis_utils as redis_utils


##### Anexar un log_registro a la lista scrape_logs
##### Retorna True si la inserción es exitosa, False si falló
def anexar_scrape_log(
    url: str,  # URL scrapeada
    medio: str,  # Medio de la noticia extraída (estandarizar con ID o string simplemente?)
    batch_id: int,
    starting_time: datetime,
    finishing_time: datetime,
    duration: time,
    status: str,  # ERROR o SUCCESS
    error=None,  # indicar el error si lo hay
    code=None,  # código de estado solicitud http (200, 404, 400, 429, etc)
):
    redis_client = redis_utils.get_redis_client()
    log_registro = {
        "url": url,
        "medio": medio,
        "batch_id": batch_id,
        "starting_time": starting_time,
        "finishing_time": finishing_time,
        "duration_ms": duration,
        "status": status,
        "error": error,
        "http_code": code,
    }
    try:
        redis_client.lpush("scrape_logs", json.dumps(log_registro))
        return True
    except redis.ConnectionError as e:
        print(f"[RedisError] Falló la conexión con Redis: {e}")
    except redis.TimeoutError as e:
        print(f"[RedisError] Timeout en la operación: {e}")
    except Exception as e:
        print(f"[RedisError] Error inesperado: {e}")
    return False


##### Limpiar lista scrape_logs, borra toda log entry
##### Retorna True si la inserción es exitosa, False si falló
def clear_scrape_logs():
    redis_client = redis_utils.get_redis_client()
    try:
        redis_client.delete("scrape_logs")
        return True
    except redis.ConnectionError as e:
        print(f"[RedisError] Falló la conexión con Redis: {e}")
    except redis.TimeoutError as e:
        print(f"[RedisError] Timeout en la operación: {e}")
    except Exception as e:
        print(f"[RedisError] Error inesperado: {e}")
    return False
