import os
from dotenv import load_dotenv


# Getter de variables de entorno necesarias
# Arroja una excepción OSError si no está seteada la variable de entorno
def get_environ_var(environ_var: str) -> str:
    try:
        load_dotenv()
    except Exception as e:
        raise RuntimeError(
            f"No se pudieron cargar las variables de entorno desde .env, error: {e}"
        ) from e
    var = os.getenv(environ_var)
    if var is None or var == "":
        print(f"Variable de entorno no seteada o vacía: {environ_var}")
        raise OSError(f"{environ_var} no está seteada")
    return var
