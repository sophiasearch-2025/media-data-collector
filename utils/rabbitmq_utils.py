import pika
import environ_var as ev


# 'Getter' de conexión con RabbitMQ
def get_rabbit_connection():
    if not hasattr(get_rabbit_connection, "_connection"):
        try:
            host = ev.get_environ_var("RABBITMQ_HOST")
            port = ev.get_environ_var("RABBITMQ_PORT")
            user = ev.get_environ_var("RABBITMQ_USER")
            password = ev.get_environ_var("RABBITMQ_PASSWORD")
            rmq_credentials = pika.PlainCredentials(user, password)
            rmq_parameters = pika.ConnectionParameters(host, port, "/", rmq_credentials)
            _connection = pika.BlockingConnection(rmq_parameters)
        except Exception as e:
            print(f"[RabbitMQError] No se pudo conectar a RabbitMQ: {e}")
    return get_rabbit_connection._connection
