# Scraper de medios de prensa de Sophia Search
Este componente es el encargado de recopilar toda la información de los artículos de prensa extraidos por el crawler.

**Hasta la fecha, se están recopilando artículos de dos medios diferentes: Biobio Chile y La Tercera**, donde sus respectivos scrapers son `scraper_biobio.py` y `scraper_latercera.py`.

Las características únicas de cada script de scraping de cada medio de prensa se encuentran documentadas en los siguientes archivos:
- [`scraper_biobio.md`](scraper_biobio.md)
- [`scraper_latercera.md`](scraper_latercera.md)

# Estructura de los scrapers
### Librerías
- `json`
- `os`
- `sys`
- `time`
- `datetime`
- `msvcrt` *(Windows)*
- `fcntl` *(Linux/MacOS)*
- `pathlib`

### Dependencias
- `pika`: Librería para RabbitMQ.
- `requests`: Librería para descargar los artículos en formato `html`.
- `bs4`: Librería para extraer información de los artículos descargados.

### Módulos
- `logger.queue_sender_scraper_results`: Se utiliza para enviar el status del scraping al módulo de logs.
- `utils.stop_signal_handler`: Se utiliza para el manejo de la señal de detención de scraping.
- `scraper.scraper_utils`: Importa funciones auxiliares para la extracción de información de los artículos descargados.


## Funciones
### `update_scraper_metrics`:
```python
def update_scraper_metrics(
    medio: str, 
    status: str, 
    duration_ms: float = 0
)
```
Actualiza las métricas del scraper (por medio) en tiempo real utilizando *file locking*


### `scrap_news_article`:
```python
def scrap_news_article(
    url: str, 
    validate: bool = False
) -> dict | list | Exception
```
Realiza el scraping completo de una noticia individual (request a la url y extracción de los datos con BeautifulSoup). 
Devuelve un diccionario si el scraping fue exitoso, una lista si hubo parámetros críticos que no se pudieron extraer del artículo (En el caso de que `validate = True`) o una excepción si ocurrió un error en el proceso. 

Parámetros
- `url` _(str)_: Dirección URL del artículo a scrapear.
- `validate`_(bool, opcional)_: Si es True, la función devolverá un None si el output no cuenta con parámetros obligatorios _(Estos siendo: título, fecha y cuerpo)_


### `consume_article`: 
```python
def consume_article(
    ch: pika.channel.Channel, 
    method: pika.spec.Basic.Deliver , 
    properties: pika.BasicProperties, 
    body: bytes
)
```
Esta función actúa como `callback` para _RabbitMQ_, es decir, se ejecuta automáticamente cada vez que llega un mensaje a la cola `scraper_queue`, definida en la cabecera del script.

Su rol es:
1. Leer el mensaje entregado desde el crawler y extraer la `url` de la noticia a scrapear.

2. Llamar a la función `scrap_news_article()`, la cual entregará toda la información del artículo.

3. Enviar un log a la cola `scraping_log_queue` de la forma:

```python
scraping_results_send(
    url: str,
    medio: str,
    starting_time: datetime,
    status: str,  # success or error
    finishing_time: datetime | None = None,
    error: str | None = None,
)
```

4. Por último enviar un mensaje a la cola `scraper_queue` con los resultados de la operación.
```python
# --- mensaje para send_data ---
send_data_msg = scraper_results
send_data_msg["url"] = url

# --- publicar mensaje hacia send_data ---
scraper_channel.basic_publish(
    exchange="",
    routing_key=SEND_DATA_QUEUE,
    body=json.dumps(send_data_msg),
    properties=pika.BasicProperties(delivery_mode=2),
)
```


## Funciones auxiliares en `scraping_utils.py`

- `extract()`:
```python
def extract(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default = None
) -> str | None:
```
Busca texto dentro de elementos específicos mediante múltiples selectores CSS.
Retorna el primer texto encontrado o un valor por defecto.


- `extract_multiple()`:
```python
def extract_multiple(
    soup: BeautifulSoup, 
    selectors: list, 
    default = ""
) -> list
```
Recorre múltiples selectores de contenido para construir una lista con cada elemento que encuentre.


- `extract_text_only()`:
```python
def extract_text_only(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default = None
) -> str | None
```
Misma funcionalidad que `extract()`, con la diferencia de que solo obtiene texto directo, ignorando nodos hijos (útil para fechas o autores anidados).


- `extract_datetime()`:
```python
def extract_datetime(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default = None
) -> str | None
```
Misma funcionalidad que `extract()`, con la diferencia de que devuelve la propiedad "datetime" en vez del texto del elemento.


- `extract_images()`:
```python
def extract_images(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> list[str]
```
Busca imágenes dentro de los selectores indicados.
Reconoce atributos como src, data-src y data-lazy-src, e incluso URLs embebidas en style.


- `extract_image_with_description()`:
```python
def extract_image_with_description(
    soup: BeautifulSoup, 
    figure_selectors: list, 
    image_selectors: list,
    description_selectors: list,
    default = None
) -> list[dict]
```
Extrae las imágenes del artículo con sus descripciones y las recolecta en una lista con el siguiente formato:
```json
[
    {
        "url": <url-imagen>, 
        "descripcion": <descripcion-imagen> 
    },
]
```


- `extract_videos()`:
```python
def extract_videos(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> list[str]
```
Extrae todos los videos que encuentre del artículo y retorna una lista con sus url.


- `extract_body_video()`:
```python
def extract_body_video(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> str
```
Extrae un único video para aquellos artículos que son únicamente un video (Utilizado únicamente en la tercera de momento).

- `extract_body()`:
```python
def extract_body(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> str
```
Llama a `extract_multiple()` para obtener todos los elementos del cuerpo de la noticia y los unifica en un único string separados por saltos de línea.


- `extract_minutoaminuto_entries()`:
```python
def extract_minutoaminuto_entries(
    soup: BeautifulSoup, 
    fig_selectors: list,
    date_selectors: list,
    body_selectors: list, 
    default = None
) -> list[dict]
```
Extrae todos los pequeños párrafos que se encuentren dentro de `fig_selectors`. Esta función es utilizada para el medio La Tercera, en aquellos reportajes de categoría `EN VIVO`, donde no es un único reportaje el que contiene el artículo sino que son múltiples de ellos cada uno con diferentes fechas y horas. La información se guarda en el siguiente formato:
```json
[
    {
        "fecha": <fecha>,
        "cuerpo": <cuerpo>
    }
]
```


- `extract_filtered_body()`:
```python
def extract_filtered_body(
    soup: BeautifulSoup, 
    selectors: list, 
    excluded_selectors: list,
    default = None
) -> str
```
Extrae el cuerpo de la noticia excluyendo los contenidos de ciertos componentes especificados en `excluded_selectors`.


## Test de scraping
En la raíz del proyecto, se encuentra el archivo `test_scraper.py`, cuyo objetivo es realizar un test de estrés al scraper especificado y así poder mejorarlo, arreglar errores en scrapers de medios ya integrados o incluso probar nuevos scrapers para integrar más medios dentro del sistema.

Este script busca desde el diccionario *DIRECCIONES_CRAWLER* un archivo `csv` que contenga el output del crawler del medio respectivo, y comienza a leer las URL, scrapeando una por una y notificando si hubo un error durante el proceso o si el proceso continúa sin problemas.

El programa se ejecuta de la siguiente manera:
```bash
// Desde la raíz del proyecto
python.exe test_scraper.py --medio <medio> --desde <desde> --hasta <hasta> --output
```
donde:
- `--medio`: Indica el medio a testear. Este se debe encontrar registrado en el diccionario *MEDIOS_DISPONIBLES* al inicio del script.
- `--desde`: Indica desde qué línea del archivo producido por el crawler se comenzará a scrapear.
- `--hasta`: Indica hasta qué línea del archivo producido por el crawler se va a scrapear.
- `--output`: Si se incluye esta flag, en la carpeta `/scraper/data` se producirá un archivo llamado `output_<medio>.json`, que contendrá la información recopilada por el scraper.

*El único argumento obligatorio es **--medio**, del resto se puede prescindir.*

### Cómo añadir un nuevo medio a `test_scraper.py`
1) Realizar un `import` al inicio del script
```python
import scraper.scraper_biobio as biobio
import scraper.scraper_latercera as latercera
```
2) Indicarle al script donde debe buscar el output del crawler y qué función de scraping utilizar para el medio a añadir actualizando los diccionarios *DIRECCIONES_CRAWLER* y *MEDIOS_DISPONIBLES* respectivamente.
```python
DIRECCIONES_CRAWLER = {
    "biobio": "Crawler/biobiochile.csv",
    "latercera": "Crawler/latercera.csv"
}

MEDIOS_DISPONIBLES = {
    "biobio": biobio.scrap_news_article,
    "latercera": latercera.scrap_news_article
}
```
3) Ejecutar el script con el nuevo medio.
```bash
python.exe test_scraper.py --medio <nuevo_medio>
``` 

## Manejo de errores dentro del scraping
Al scrapear, pueden ocurrir ciertos errores que se pueden separar en dos categorías:
- Errores de parseo
- Errores de ejecución


Las funciones que existen actualmente para los scrapers *(Biobio Chile y La Tercera)* pueden devolver tres tipos de datos
1) `dict` -> Si el scraping fue exitoso.
2) `list` -> Si hubo un error de parseo.
3) `str` -> Si hubo un error de ejecución.


Al ejecutar `test_scraper.py`, el script podrá darle 3 mensajes posibles de status:
```bash
// Scraping exitoso
Url <index> scrapeada exitosamente

// Scraping con error de parseo
Error al scrapear la url n° <index>

// Scraping con error de ejecución
Error inesperado al scrapear la url n° <index>
    -> <error-info>
```

Una vez que ocurra un error, es recomendable de que se intente scrapear más a detalle, llendo a la línea indicada en el archivo `<medio>.csv`, copiar el url e ingresar al scraper correspondiente.

Cada script de scraping específico de cada medio contiene una función `test()`, donde puedes ingresar una url de prueba y ejecutar la función para poder revisar de forma manual la información recopilada. 
```python
def test():
    test_url = ""
    noticia = scrap_news_article(test_url)
    if isinstance(noticia, dict):
        print(json.dumps(noticia, indent=3, ensure_ascii=False))
```


Para realizar un test particular, debe agregar la url a la variable `test_url` y cambiar la condición `if __name__ == "__main__":` para que se ejecute `test()` en vez de `main()`:

```python
if __name__ == "__main__":
    test()

```

### Cómo arreglar los errores de parseo
Las funciones para extraer la información de los HTML scrapeados están pensadas de una manera en que puedas, explicado de forma simple, _decirle a la función los posibles lugares a donde buscar la información_, a través de la sintaxis `component.class`

### Ejemplos:

#### `extract()`
```python
extract(soup, [
    "div.post-date",
    "div.autor-fecha-container p.fecha",
    "div.nota p.fecha",
    "div.nota-top-content div.top-content-text p.fecha",
])
```
En este ejemplo, la función va a buscar primero en `div.post-date`, si no encuentra el componente, buscará `p.fecha` dentro del componente padre `div.autor-fecha-container`, y así. La función parará de buscar en cuanto encuentre un componente válido dentro del HTML. Todo depende de la forma del html de la página (que puede variar dependiendo de la categoría de la noticia, actualizaciones a las páginas web, entre otros factores).

#### `extract_body()`
```python
extract_body(soup, [
    "div.post-main div.post-content div.container-redes-contenido p, div.post-main div.post-content div.container-redes-contenido h2",
    "div.container-redes-contenido div.contenido-nota h2, div.container-redes-contenido div.contenido-nota p",
    "div.contenido-nota div[class^='banners-contenido-nota-'] h2, div.contenido-nota div[class^='banners-contenido-nota-'] p",
    "div.container-nota-body div.nota-content div.contenido p, div.container-nota-body div.nota-content div.contenido h2",
])
```

En extract body, se desea buscar los componentes `<p>` y `<h2>`, por lo que para indicarle a `BeautifulSoup` que busque más de un componente a la vez, las búsquedas se separan por comas dentro de un mismo string.

Un caso en particular a destacar es cuando se utiliza `div[class^='banners-contenido-nota-']`, lo cual, el uso del operador `^=` le está diciendo a `BeautifulSoup` _"Busca dentro de cualquier `<div>` cuyo classname comience con `banners-contenido-nota`"_. Esto se utiliza porque para ciertas páginas de _Biobio Chile_, el classname del componente que contiene el cuerpo de la noticia tiene un identificador único, por lo que esta sintaxis es útil para estos casos.

#### `extract_multimedia()`
```python
extract_multimedia(soup, [
    "div.post-main div.post-image img",
    "div.post-main div.post-content div.container-redes-contenido img",
    "div.imagen",
    "div.contenedor-imagen-titulo div.imagen img",
    "div.nota-top-content img"
])
```

Aquí se busca únicamente imágenes puesto que en _Biobio Chile_, el único multimedia que se encuentra en la página relacionado al archivo son imágenes.

Si es que el scraper devuelve una lista al llamarlo en el modo `validate`, es porque uno de los campos obligatorios _(título, fecha o cuerpo, indicado en la lista)_ está vacío. En este caso, se debe buscar en el HTML de la página el dato a scrapear, sus componentes padres, los classnames de cada uno respectivamente y añadirlo a la lista de búsqueda dentro del script.

- Ejemplo
```python
fecha = extract(soup, [
    "div.post-date",
    "div.autor-fecha-container p.fecha",
    "div.nota p.fecha",
    "div.nota-top-content div.top-content-text p.fecha",
    "div.dato-nuevo p.texto" <--
])
```

Para comprobar que el campo se está extrayendo de forma correcta, puede ejecutar este script y revisar el output.
