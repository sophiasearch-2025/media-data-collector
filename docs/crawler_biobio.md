# Crawler biobio.py

El script `crawler_biobio.py` implementa dos funciones para la recopilación de los links de noticias en biobiochile.cl:

1) `crawl_categories(site_config)`, el cual obtiene un set de links de categorías reconocidas en la página que se desea escrapear.

2) `crawl_news(site_config, category_url)` el cual navega la página de categoria dada, según configuración ingresada.

Cabe mencionar que, por ahora que solo se scrapea solo un medio, se define el siguiente diccionario de entrada:


        SITES = {
            "biobiochile": {
                "start_url": "https://www.biobiochile.cl/",
                "category_pattern": "lista/categorias",
                "news_pattern": ["/noticias/"], 
                "pagination_type": "loadmore",
                "load_more_selector": ".fetch-btn", 
                "max_clicks": 2
            }
        }

Este diccionario, por cada medio desde el cual se desea scrapear, define los siguientes parámetros de entrada:

- `start_url` define una url base del sitio de noticias a escrapear ("https://www.biobiochile.cl/" para este entregable).

- `category_pattern` define un patrón de slug de categorías (por ejemplo, lista/categorias en biobiochile.cl).

- `news_pattern` define patron de slug de links de noticias de la página que se desea escrapear ("/noticias/" en biobiochile.cl).

- `pagination_type` define el tipo de paginación de la página de categorías(loadmore si existe un boton javascript que carga mas noticias dinamicamente, pagination si existe paginación en la página).

- `load_more_selector` en caso de haber un boton javascript que carga más noticias, se necesita el classname o id de dicho boton en  (.fetch-btn en biobiochile.cl).

- `max_clicks` define la cantidad máxima de clicks en botones de "cargar más noticias" o número páginas a cargar en caso de paginación (2 para esta prueba).

## Dependencias

- `requests`: Descargar el HTML de la web
- `BeautifulSoup`: Parseo y búsqueda dentro del HTML
- `urllib.parse.urljoin`: Armar URLs absolutas a partir de rutas relativas.
- `asyncio`:
- `csv`: 
- `time`:
- `json`: Exportar la información estructurada
- `os`:


## Funciones Auxiliares

## Funciones Principales

1) `crawl_categories(site_config)`, el cual obtiene un set de links de categorías reconocidas en la página que se desea escrapear.

2) `crawl_news(site_config, category_url)` el cual navega la página de categoria dada, según configuración ingresada.

## Test Crawler en biobiochile.cl



## Integración



## Manejo de Errores



## Ejemplos

