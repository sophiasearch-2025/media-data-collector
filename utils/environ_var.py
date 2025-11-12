import os


# Getter de variables de entorno necesarias
# Arroja una excepción OSError si no está seteada la variable de entorno
def get_environ_var(environ_var: str) -> str:
    var = os.getenv(environ_var)
    if var is None:
        print(f"Variable de entorno no seteada o vacía: {environ_var}")
        raise OSError(f"{environ_var} no está seteada")
    return var
