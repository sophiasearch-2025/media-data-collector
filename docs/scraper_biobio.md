# Scraper biobiochile.cl

El script `scraper_biobio.py` implementa las funciones 
- `update_scraper_metrics()`
- `scrap_news_article()`
- `consume_article()`

Especificadas en [`scraper.md`](scraper.md)


El output del scraper para el medio **Biobio Chile** es el siguiente:

```python
{
    "url": url,       | Entregados por
    "tags": str,      | el crawler
    "titulo": str,
    "fecha": str,
    "autor": str,
    "desc_autor": str,
    "abstract": str,
    "cuerpo": str,
    "multimedia": list[url],
    "tipo_multimedia": str
}
```

*NOTA: El campo multimedia para el medio Biobio Chile, solo entrega imágenes, por lo que en un futuro, por conveniencia, se podría cambiar el nombre acorde.*

## Funciones auxiliares utilizadas desde `scraping_utils.py`
- `extract()`
- `extract_text_only()`
- `extract_images()`
- `extract_body()`


## Tests de scraping dada una URL
Se define una función `test()` para realizar tests de scraping a una URL en específico. Para usarla debe colocar la URL a scrapear en la variable `test_url` y debe ejecutar el script:
```bash
python scraper/scraper_biobio.py
```
A continuación, se imprimirá en la consola el output del scraping realizado.

## Integración
Si se desea integrar la función a otro script dentro del proyecto, se puede importar la función directamente:
```python
import scraper.scraper_biobio as biobio

result = biobio.scrap_news_article(
    "https://www.biobiochile.cl/...", 
    validate = True
)
```