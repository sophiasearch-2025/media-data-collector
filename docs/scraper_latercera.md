# Scraper latercera.com

El script `scraper_latercera.py` implementa las funciones 
- `update_scraper_metrics()`
- `scrap_news_article()`
- `consume_article()`

Especificadas en [`scraper.md`](scraper.md)


El output del scraper para el medio **La Tercera** es el siguiente:

```python
{
    "url": url,       | Entregados por
    "tags": str,      | el crawler
    "categoria": str,
    "titulo": str,
    "fecha": str,
    "autor": str,
    "abstract": str,
    "cuerpo": str | url,
    "cuerpo_en_vivo": list[dict[str, str]],
    "imagenes": list[dict[str, str]],
    "videos": list[url]
}
```

### Aclaraciones importantes con respecto al output:
- `cuerpo` por lo general será un string común con el respectivo cuerpo de la noticia a excepción del caso en que `categoria = "Videos"`, donde cuerpo tendrá una `url`.
- `cuerpo_en_vivo` será `Null` a excepción que `categoria = "EN VIVO"`. En La Tercera, los artículos de la categoría EN VIVO se van actualizando constantemente con nueva información, donde cada actualización contiene su propia `fecha` y su propio `cuerpo`, por lo que estos están almacenados en una lista con el siguiente formato:
```python
[
    {
        "fecha": <fecha>,
        "cuerpo": <cuerpo>
    },
]
```
- En `imagenes`, se almacenan en una estructura parecida a la de cuerpo en vivo, ya que cada imagen (a diferencia de Biobio Chile) puede o no tener descripción, por lo que la información se guarda en el siguiente formato:
```python
[
    {
        "url": <url-imagen>, 
        "descripcion": <descripcion-imagen> 
    },
]
```

## Funciones auxiliares utilizadas desde `scraping_utils.py`
- `extract()`
- `extract_body()`
- `extract_datetime()`
- `extract_videos()`
- `extract_body_video()`
- `extract_image_with_description()`
- `extract_filtered_body()`
- `extract_minutoaminuto_entries()`


## Tests de scraping dada una URL
Se define una función `test()` para realizar tests de scraping a una URL en específico. Para usarla debe colocar la URL a scrapear en la variable `test_url` y debe ejecutar el script:
```bash
python scraper/scraper_latercera.py
```
A continuación, se imprimirá en la consola el output del scraping realizado.

## Integración
Si se desea integrar la función a otro script dentro del proyecto, se puede importar la función directamente:
```python
import scraper.scraper_latercera as latercera

result = latercera.scrap_news_article(
    "https://www.latercera.com/...", 
    validate = True
)
```