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
  - pika
- RabbitMQ corriendo localmente (por defecto `localhost`).

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
    }
}
```

- `start_url`: Url base del sitio de noticias a escrapear (https://www.biobiochile.cl/ para este entregable).

- `category_pattern`: Patrón de slug de categorías (por ejemplo, lista/categorias en biobiochile.cl).

- `news_pattern`: Patron de slug de links de noticias de la página que se desea escrapear ("/noticias/" en biobiochile.cl).

- `pagination_type`: Tipo de paginación de la página de categorías(`loadmore` si existe un boton javascript que carga mas noticias dinamicamente, `pagination` si existe paginación en la página).

- `load_more_selector`: En caso de haber un boton javascript que carga más noticias, se necesita el classname o id de dicho boton en  (.fetch-btn en biobiochile.cl).

- `max_clicks`: Cantidad máxima de clicks en botones de "cargar más noticias" o número páginas a cargar en caso de paginación (2 para esta prueba).

## Funcionamiento
* `crawler_biobio.py`:
    1. `crawl_categories(config)`: 
        - Navega la home y devuelve un set de URLs de categoría.
    2. `crawl_news(config, category_list)`:
        - Por cada categoría usa `scrape_category_loadmore` para cargar items (clicks),
        - Extrae hrefs que coinciden con `news_pattern`,
        - Extrae la categoría real de cada link con reglas (ver “Extracción de categoría”),
        - Publica inmediatamente el link a RabbitMQ (si no fue enviado antes),
        - Acumula en `all_news` para métricas y CSV.
* Al final escribe `Crawler/{medio}.csv` y `metrics/crawler_metrics.json`.

## Funciones principales
- async crawl_categories(site_config) -> set[str]  
  Navega `start_url`, parsea enlaces y retorna URLs que contienen `category_pattern`. Maneja timeouts y cierra el navegador si falla.

- async scrape_category_loadmore(page, category_url, load_more_selector, news_pattern, max_clicks=10) -> set[str]  
  Abre la categoría, hace hasta `max_clicks` clicks en el botón `load_more_selector`, parsea HTML y retorna set de links de noticias (absolutos).

- async crawl_news(site_config, category_links) -> set[tuple(str categoria, str link)]  
  Itera `category_links`, obtiene links por categoría, normaliza categoría y publica a RabbitMQ (función `send_link`).

## Helpers y utilidades
- _block_assets(page): bloquea recursos pesados (imágenes, css, fonts, media) para acelerar navegación.
- get_category(link, slug) -> str: extrae hasta 3 niveles de categoría desde `/noticias/` o `/especial/`, detiene si encuentra un año (4 dígitos), elimina el segmento redundante `noticias`, y mapea rutas `biobiochile/noticias-patrocinadas/...` a `noticias-patrocinadas`.
- send_link(link, tags): publica JSON a la cola `scraper_queue`. Usa `pika.BlockingConnection` y `crawler_channel.basic_publish`.

## Salida / artefactos
- CSV: `Crawler/biobiochile.csv` — filas: categoria, url
- Métricas: `metrics/crawler_metrics.json` con:
  - sitio, total_categorias, total_urls_encontradas, urls_por_categoria, duracion_segundos, urls_por_minuto

## Timeouts y rendimiento
- Constantes configurables:
  - GOTO_TIMEOUT_START = 15000 (ms)
  - GOTO_TIMEOUT_CATEGORY = 15000 (ms)
  - SHORT_WAIT = 500 (ms)
  - CLICK_WAIT = 500 (ms)
- Recomendación: si hay timeouts frecuentes, subir GOTO_TIMEOUT_CATEGORY a 20_000 ms o añadir reintentos; bloquear assets acelera mucho.

## Errores y robustez
- Timeouts en `goto` se atrapan y provocan retorno de set vacío para esa navegación (no abortan todo).
- Deduplicado en ejecución: `seen_links` evita reenvíos al scrapper dentro del mismo run.
- Limitación: `seen_links` es volátil (no persiste entre runs). Para persistencia usar sqlite/redis/file si se requiere idempotencia entre ejecuciones.

## Integración RabbitMQ
- Cola producida: `scraper_queue` (mensajes JSON: {"url":..., "tags": ...}).
- Cola de logs: `log_queue` (opcional).
- Scheduler debe ejecutarse desde la raíz del proyecto para resolver rutas relativas, o usar el scheduler parcheado que usa rutas absolutas.

## Ejemplos de uso

- Activar venv y ejecutar crawler:
```bash
cd ~/ArquitecturaSoftware/media-data-collector
source .venv/bin/activate
python -u Crawler/crawler_biobio.py biobiochile
```
- Ejecutar desde scheduler (recomendado):
```bash
.venv/bin/python -u RabbitMQ/scheduler.py biobiochile
```

## Limitaciones conocidas

- Si la web genera enlaces vía JS que necesitan estilos o scripts complejos, bloquear assets puede omitir enlaces. En ese caso desactivar `_block_assets` para esa categoría.

- Dedupe solo en memoria: reinicios provocan reenvío de links previos.

## Testing
- Para tests unitarios, mockear Playwright y `scrape_category_loadmore` / `crawl_categories` y verificar:
  - llamadas a `send_link`
  - escritura del CSV
  - formato de categorías extraídas por `get_category`

- Logs estándar: impresiones por stdout (útiles cuando `PYTHONUNBUFFERED=1`).
