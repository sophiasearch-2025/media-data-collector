# Como desplegar la plataforma

## Requisitos

[Requisitos](../requirements.txt)

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

En la carpeta `Crawler/` se encuentra el script de recopilación de artículos de noticias y el output de este mismo en formato `csv`. En `scraper/` se encuentra el script de scraping para cada artículo de noticias que el crawler recolecte.

## Despliegue
En la raíz del proyecto se encuentra el script `test_scraper.py`, el cual lee del output del script `crawler_biobio.py` y realiza un scraping para cada artículo que este recolecte.

Si desea realizar un scraping, debe ejecutar `test_scraper.py` de la siguiente forma:
```
python test_scraper.py --desde <int> --hasta <int> --output
```
Donde:
- desde: Indica desde qué línea del archivo `biobiochile.csv` empezar a scrapear.
- hasta: Indica hasta qué línea del archivo `biobiochile.csv` scrapear.
- output: Incluir esta flag si se desea que el output del scraping sea escrito en un archivo `output.json` dentro de la carpeta `scraper/data`

Todos los argumentos son opcionales, si estos no se incluyen se scrapeará todo el archivo csv y los resultados del scraping no se guardarán en memoria.

