import os


# Getter de variables de entorno necesarias en la conexión RabbitMQ
# Arroja una excepción KeyError si no está seteada la variable de entorno
def get_environ_var(environ_var):
    var = os.getenv(environ_var)
    if var is None:
        raise KeyError(f"{environ_var} no está seteada")
    return var
