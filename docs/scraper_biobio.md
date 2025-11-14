# Scraper biobiochile.cl

El script `scraper_biobio.py` implementa la función `scrap_news_article(url, tags)`, la cual se encarga de recopilar la información del artículo de la URL otorgada y envía el output a un trabajador de RabbitMQ para su posterior distribución en el sistema Sophia Search. La forma del output es la siguiente:

```json
{
    "titulo": string,
    "fecha": string,
    "autor": string,
    "desc_autor": string,
    "abstract": string,
    "cuerpo": string,
    "multimedia": list[string],
    "tipo_multimedia": string
}
```

## Dependencias
- `requests`: Descargar el HTML de la web
- `BeautifulSoup`: Parseo y búsqueda dentro del HTML
- `urllib.parse.urljoin`: Armar URLs absolutas a partir de rutas relativas.
- `re`: Detección de imágenes embebidas en atributos _style_
- `json`: Exportar la información estructurada

## Funciones auxiliares
- `extract(soup, selectors, default=None)`

Busca texto dentro de elementos específicos mediante múltiples selectores CSS.
Retorna el primer texto encontrado o un valor por defecto.

- `extract_text_only(soup, selectors, default=None)`

Similar a extract(), pero obtiene solo texto directo, ignorando nodos hijos (útil para fechas o autores anidados).

- `extract_multimedia(soup, selectors, default="")`

Busca imágenes o elementos multimedia dentro de los selectores indicados.
Reconoce atributos como src, data-src y data-lazy-src, e incluso URLs embebidas en style.

- `extract_body(soup, selectors, default="")`

Recorre selectores de contenido para construir el cuerpo completo del artículo.
Devuelve un texto unificado con saltos de línea.

## Función principal `scrap_news_article(url, tags)`
Realiza el scraping completo de una noticia individual. El output de esta función es el que se encuentra arriba en el documento. Esta función puede devolver tanto un diccionario de python como una `lista con los elementos de la noticia faltantes`, dependiendo de los parámetros y el output.

Parámetros
- `url` _(str)_: Dirección URL del artículo a scrapear.
- `validate`_(bool, opcional)_: Si es True, la función devolverá un None si el output no cuenta con parámetros obligatorios _(Estos siendo: título, fecha y cuerpo)_

## Función integradora a RabbitMQ `consume_article()`
Esta función actúa como `callback` para _RabbitMQ_, es decir, se ejecuta automáticamente cada vez que llega un mensaje a la cola `scraper_queue`, definida en la cabecera del script.

Su rol es:
1. Leer el mensaje entregado desde el crawler y extraer la `url` de la noticia a scrapear.

2. Llamar a la función `scrap_news_article(url, validate = True)`, la cual entregará toda la información del artículo.

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

Mensaje el cual contiene la siguiente información:

```json
{
    "url": string,       | Entregados por
    "tags": string,      | el crawler
    "titulo": string,
    "fecha": string,
    "autor": string,
    "desc_autor": string,
    "abstract": string,
    "cuerpo": string,
    "multimedia": list[string],
    "tipo_multimedia": string
}
```

## Tests de scraping dada una URL
Se define una función `test()` para realizar tests de scraping a una URL en específico. Para usarla debe colocar la URL a scrapear en la variable `test_url` y debe ejecutar el script:
```bash
python scraper/scraper_biobio.py
```
A continuación, se imprimirá en la consola el output del scraping realizado.

## Integración
Si se desea integrar la función a otro script dentro del proyecto, se puede importar la función directamente:
```python
from scraper.scraper_biobio import scrap_news_article

result = scrap_news_article(
    "https://www.biobiochile.cl/...", 
    validate = True
)
```

## Manejo de errores
Las funciones para extraer la información de los HTML scrapeados están pensadas de una manera en que puedas, explicado de forma simple, _decirle a la función los posibles lugares a donde buscar la información_, a través de la sintaxis `componente.classname`

### Ejemplos:

`extract()`
```python
extract(soup, [
    "div.post-date",
    "div.autor-fecha-container p.fecha",
    "div.nota p.fecha",
    "div.nota-top-content div.top-content-text p.fecha",
])
```
Aquí, la función va a buscar primero en `div.post-date`, si no encuentra el componente, buscará `p.fecha` dentro del componente padre `div.autor-fecha-container`, y así. La función parará de buscar en cuanto encuentre un componente válido dentro del HTML. Todo depende de la forma del html de la página (que puede variar dependiendo de la categoría de la noticia).

`extract_body()`
```python
extract_body(soup, [
    "div.post-main div.post-content div.container-redes-contenido p, div.post-main div.post-content div.container-redes-contenido h2",
    "div.container-redes-contenido div.contenido-nota h2, div.container-redes-contenido div.contenido-nota p",
    "div.contenido-nota div[class^='banners-contenido-nota-'] h2, div.contenido-nota div[class^='banners-contenido-nota-'] p",
    "div.container-nota-body div.nota-content div.contenido p, div.container-nota-body div.nota-content div.contenido h2",
])
```

En extract body, se desea buscar los componentes `<p>` y `<h2>`, por lo que para indicarle a `BeautifulSoup` que busque más de un componente a la vez, las búsquedas se separan por comas dentro de un mismo string.

Un caso en particular a destacar es cuando se utiliza `div[class^='banners-contenido-nota-']`, lo cual, el uso del operador `^=` le está diciendo a `BeautifulSoup` _"Busca dentro de cualquier `<div>` cuyo classname comience con `banners-contenido-nota`"_. Esto se utiliza porque para ciertas páginas de _BioBio Chile_, el classname del componente que contiene el cuerpo de la noticia tiene un identificador único, por lo que esta sintaxis es útil para estos casos.

`extract_multimedia()`
```python
extract_multimedia(soup, [
    "div.post-main div.post-image img",
    "div.post-main div.post-content div.container-redes-contenido img",
    "div.imagen",
    "div.contenedor-imagen-titulo div.imagen img",
    "div.nota-top-content img"
])
```

Aquí se busca únicamente imágenes puesto que en _BioBio Chile_, el único multimedia que se encuentra en la página relacionado al archivo son imágenes.

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
