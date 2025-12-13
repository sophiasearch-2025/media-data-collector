# Crawler biobio

## Resumen

- Script async que recorre biobiochile.cl para extraer links de noticias, estos luego son enviados al scrapper via RabbitMQ.

- Links de noticias encontrados son enviados al scrapper via RabbitMQ (cola `scraper_queue`).

- Implementa duplicado en memoria (set `seen_links`) para evitar enviar duplicados al scrapper (futura implementación en Redis).

- Genera un archivo CSV que contiene categorías y url de cada noticia encontrada, y un archivo JSON con métricas de medición.

## Requisitos

- Python 3.10+, virtualenv con dependencias:
  - playwright
  - beautifulsoup4
  - asyncio
  - pika
- RabbitMQ corriendo localmente (por defecto `localhost`).

Para activar el entorno virtual, debe ejecutar los siguientes comandos en su terminal:
```
python -m venv venv
venv/Scripts/activate
```

## Instalación

Use el siguiente comando para instalar los paquetes necesarios para los scripts del proyecto:
```
pip install -r requirements.txt
```
Paquetes que se instalarán:
[Requisitos](../requirements.txt)

En la carpeta `Crawler/` se encuentra el script de recopilación de artículos de noticias y el output de este mismo en formato `csv`. En `scraper/` se encuentra el script de scraping para cada artículo de noticias que el crawler recolecte.

## Configuración

- Definido en memoria (futura implementación en base de datos):
```python
SITES = {
    "biobiochile": {
        "start_url": "https://www.biobiochile.cl/",
        "category_pattern": "lista/categorias",
        "news_pattern": ["/noticias/"],
        "load_more_selector": ".fetch-btn",
        "pagination_type": "loadmore",
        "max_clicks": 2
    },
        "latercera": {
        "start_url":"https://www.latercera.com/",
        "category_pattern": "canal",
        "news_pattern": ["/noticia/"],
        "load_more_selector": ".result-list__see-more",
        "pagination_type": "loadmore", 
        "max_clicks": 2
    }
}
```

- `start_url`: Url base del sitio de noticias a escrapear (https://www.biobiochile.cl/ o https://www.latercera.com/ para este sprint).

- `category_pattern`: Patrón de slug de categorías (por ejemplo, lista/categorias en biobiochile.cl, /canal/ en latercera.cl).

- `news_pattern`: Patron de slug de links de noticias de la página que se desea escrapear ("/noticias/" en biobiochile.cl, "/noticia" en latercera.cl).

- `pagination_type`: Tipo de paginación de la página de categorías(`loadmore` si existe un boton javascript que carga mas noticias dinamicamente, `pagination` si existe paginación en la página).

- `load_more_selector`: En caso de haber un boton javascript que carga más noticias, se necesita el classname o id de dicho boton en  (.fetch-btn en biobiochile.cl, .result-list__see-more en latercera.cl).

- `max_clicks`: Cantidad máxima de clicks en botones de "cargar más noticias" o número páginas a cargar en caso de paginación (2 para esta prueba).

## Funcionamiento
* `crawler.py`: 
    - Recibe nombre de medio que se desea scrapear, configuración de cómo obtener links de noticias de este medio guardados en diccionario `SITES`.
    - Llama a funciones en `crawler_loadmore.py` para obtener los links de noticias.
    - Durante ejecución inicializa y reescribe ``metrics/crawker_progress.json` para mostrar estado en tiempo real.
    - Al final escribe `Crawler/{medio}.csv` y `metrics/crawler_metrics.json`.

* `crawler_loadmore.py`:
    1. `crawl_categories(config)`: 
        - Navega la home y devuelve un set de URLs de categoría.
    2. `crawl_news(config, category_list)`:
        - Por cada categoría usa `scrape_category_loadmore` para cargar items (clicks).
        - Extrae hrefs que coinciden con `news_pattern`.
        - Extrae la categoría real de cada link con reglas (ver “Extracción de categoría”).
        - Llama a funciones en `crawler_sender.py` para publicar inmediatamente el link a RabbitMQ (si no fue enviado antes).
        - Acumula en `all_news` para métricas y CSV.
* `crawler_sender.py`
    1. `send_link(link, tags)`:
        - Envía mensaje a cola de scrapper con link de noticia y sus tags de categorías.
    2. `error_send(link, e, stage)`:
        - Envia mensaje de error a cola de LOG con link de medio donde falló, error y etapa del proceso de crawler donde falló.

## Funciones principales
- `async crawl_categories(site_config) -> set[str]`:
  Navega `start_url`, parsea enlaces y retorna URLs que contienen `category_pattern`. Maneja timeouts y cierra el navegador si falla.

- ``async scrape_category_loadmore(page, category_url, load_more_selector, news_pattern, max_clicks=10) -> set[str]``: 
  Abre la categoría, hace hasta `max_clicks` clicks en el botón `load_more_selector`, parsea HTML y retorna set de links de noticias.

- ``async crawl_news(site_config, category_links) -> set[tuple(str categoria, str link)] ``:
  Itera `category_links`, obtiene links por categoría, normaliza categoría y publica a RabbitMQ (función `send_link`).

## Helpers y utilidades
- ``block_assets(page)``: bloquea recursos pesados (imágenes, css, fonts, media) para acelerar navegación.
- ``get_category(link, slug) -> str:`` extrae hasta 3 niveles de categoría desde `/noticias/` o `/especial/`, detiene si encuentra un año (4 dígitos), elimina el segmento redundante `noticias`, y mapea rutas `biobiochile/noticias-patrocinadas/...` a `noticias-patrocinadas`.

- ``send_link(link, tags)``: publica JSON a la cola `scraper_queue`. Usa `pika.BlockingConnection` y `crawler_channel.basic_publish`.

## Salida / artefactos
- CSV: `Crawler/biobiochile.csv` — filas: categoria, url.
- Métricas: `metrics/crawler_metrics.json` con:
  - sitio, total_categorias, total_urls_encontradas, urls_por_categoria, duracion_segundos, urls_por_minuto.
- Métricas: `metrics/crawler_progress.json` con:
  - sitio, status (en progreso o completado), total_categorias, categorias_procesadas, porcentaje y rusl_encontradas. 

## Timeouts y rendimiento
- Constantes configurables (en ms):
```python
  GOTO_TIMEOUT_START = 15000
  GOTO_TIMEOUT_CATEGORY = 15000
  SHORT_WAIT = 500
  CLICK_WAIT = 500
```
- Recomendación: si hay timeouts frecuentes, subir GOTO_TIMEOUT_CATEGORY a 20000 ms o añadir reintentos; bloquear assets acelera mucho.

## Errores
- Key Error al inicio del programa si sitio que se desea scrapear no está en el diccionario de medios ingresados.

- Timeouts en `goto` se atrapan y provocan retorno de set vacío para esa navegación (no abortan todo).

## Integración RabbitMQ

- `scraper_queue`: Cola de mensajes RabbitMQ para que el scrapper inicie su trabajo. El mensaje tiene la siguiente estructura: 
```json
{
  "url": string, 
  "tags": string
}
```

- `crawler_log_queue`: Cola de mensajes mensaje RabbitMQ de Log de errores del crawler. El mensaje tiene la siguiente estructura:

```JSON
{
  "origen": string,
  "error_timestamp": datetime,
  "error_detail": string,
  "arg_medio": string,
  "etapa": string
}
```

## Ejemplos de uso

- Activar venv y ejecutar crawler:
```bash
cd ~/ArquitecturaSoftware/media-data-collector
source .venv/bin/activate
python -u Crawler/crawler.py <medio>
```
- Ejecutar desde scheduler (recomendado):
```bash
python -m scheduler.main <medio> <cantidad_de_scrapers>"
```

## Limitaciones conocidas

- Si la web genera enlaces vía JS que necesitan estilos o scripts complejos, bloquear assets puede omitir enlaces. En ese caso desactivar `_block_assets` para esa categoría.

- Set links enviados solo en memoria: reinicios provocan reenvío de links previos.
