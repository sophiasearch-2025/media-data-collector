import redis
import environ_var


##### 'Getter' de conexión redis_client
def get_redis_client():
    # _client funciona como un atributo estático privado
    # para verificar si la conexión ya se estableció o no
    # y evitar crear conexiones nuevas
    if not hasattr(get_redis_client, "_client"):
        try:
            redis_port = environ_var.get_environ_var("REDIS_PORT")
            get_redis_client._client = redis.Redis(
                port=redis_port, decode_responses=True
            )
        except redis.ConnectionError as e:
            print(f"[RedisError] No se pudo conectar a Redis: {e}")
        except redis.TimeoutError as e:
            print(f"[RedisError] Timeout en la operación: {e}")
        except KeyError as e:
            print(f"[RedisError] Error por variable de entorno: {e}")
        except Exception as e:
            print(f"[RedisError] Error inesperado: {e}")
    return get_redis_client._client
