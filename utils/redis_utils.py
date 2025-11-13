import redis
from . import environ_var as ev


##### 'Getter' de conexión redis_client
def get_redis_client():
    # _client funciona como un atributo estático privado
    # para verificar si la conexión ya se estableció o no
    # y evitar crear conexiones nuevas
    if not hasattr(get_redis_client, "_client"):
        try:
            redis_port = ev.get_environ_var("REDIS_PORT")
            get_redis_client._client = redis.Redis(
                port=redis_port, decode_responses=True
            )
            return get_redis_client._client

        except redis.ConnectionError as e:
            print("No se pudo conectar a Redis")
            raise RuntimeError("Error de conexión Redis") from e
        except OSError as e:
            print(f"Error de conexión a Redis por variable de entorno: {e}")
            raise EnvironmentError from e
        except Exception as e:
            print(f"Error inesperado al intentar conectarse a Redis: {e}")
            raise
