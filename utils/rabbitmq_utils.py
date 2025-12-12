import pika
from pika.exceptions import AMQPConnectionError

from . import environ_var as ev


# 'Getter' de conexión con RabbitMQ
def get_rabbit_connection():
    if (
        not hasattr(get_rabbit_connection, "_connection")
        or get_rabbit_connection._connection.is_closed
    ):
        try:
            host = ev.get_environ_var("RABBITMQ_HOST")
            port = int(ev.get_environ_var("RABBITMQ_PORT"))
            user = ev.get_environ_var("RABBITMQ_USER")
            password = ev.get_environ_var("RABBITMQ_PASSWORD")
            rmq_credentials = pika.PlainCredentials(user, password)
            rmq_parameters = pika.ConnectionParameters(host, port, "/", rmq_credentials)
            get_rabbit_connection._connection = pika.BlockingConnection(rmq_parameters)
            return get_rabbit_connection._connection

        except AMQPConnectionError as e:
            print(f"No se pudo conectar a RabbitMQ: {e}")
            raise RuntimeError("Error de conexión RabbitMQ") from e

        except OSError as e:
            print(f"Error de conexión a RabbitMQ por variable de entorno: {e}")
            raise EnvironmentError from e

        except Exception as e:
            print(f"Error inesperado al obtener conexión RabbitMQ: {e}")
            raise Exception from e

    return get_rabbit_connection._connection

def reset_connection():
    """Fuerza el cierre y eliminación de la conexión actual para obligar una reconexión."""
    if hasattr(get_rabbit_connection, "_connection"):
        try:
            if get_rabbit_connection._connection.is_open:
                get_rabbit_connection._connection.close()
        except Exception:
            pass # Ignorar errores al cerrar si ya estaba cerrada
        # Eliminar el atributo para que get_rabbit_connection cree una nueva la próxima vez
        delattr(get_rabbit_connection, "_connection")
