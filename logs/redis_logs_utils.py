import json
import redis


##### 'Getter' de conexión redis_client
def get_redis_client():
    # _client funciona como un atributo estático privado
    # para verificar si la conexión ya se estableció o no
    # y evitar crear conexiones nuevas
    if not hasattr(get_redis_client, "_client"):
        try:
            get_redis_client._client = redis.Redis(port=6379, decode_responses=True)
            connection = (
                get_redis_client._client.ping()
            )  # para efectos de testeo, borrar después
            print(connection)  # para efectos de testeo, borrar después
        except redis.ConnectionError as e:
            print(f"[RedisError] No se pudo conectar a Redis: {e}")
        except redis.TimeoutError as e:
            print(f"[RedisError] Timeout en la operación: {e}")
        except Exception as e:
            print(f"[RedisError] Error inesperado: {e}")
    return get_redis_client._client


##### Anexar un log_registro a la lista scrape_logs
##### Retorna True si la inserción es exitosa, False si falló
def anexar_scrape_log(
    url,  # URL scrapeada
    medio,  # Medio de la noticia extraída (estandarizar con ID o string simplemente?)
    starting_time,
    finishing_time,
    duration,
    status,  # ERROR o SUCCESS
    error=None,  # indicar el error si lo hay
    code=None,  # código de estado solicitud http (200, 404, 400, 429, etc)
):
    redis_client = get_redis_client()
    log_registro = {
        "url": url,
        "medio": medio,
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
    redis_client = get_redis_client()
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
