import requests                     # Descargar HTML
import json                         # Parsear info
from bs4 import BeautifulSoup       # Parsear HTML y extraer datos
from urllib.parse import urljoin    # Transformar urls de imágenes


def extract(soup: BeautifulSoup, selectors: list[str], default = None) -> str | None:
    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = info.get_text(strip = True)
            if txt: 
                return txt
    return default


def extract_multimedia(soup: BeautifulSoup, selectors: list, default: str = "") -> list[str]:

    images = set()
    for sel in selectors:
        for img in soup.select(sel):
            src = (
                img.get("src") or
                img.get("data-src") or
                img.get("data-lazy-src")
            )
            if src and isinstance(src, str):
                url = urljoin(default, src.strip())
                images.add(url)

    return list(images)


def scrap_news_article(url: str, validate: bool = False) -> dict | None:
    try:
        # Realizar una request al sitio
        response = requests.get(url, timeout = 10)
        response.encoding = "utf-8"
        response.raise_for_status()

        # Parsear y extraer respuesta
        soup = BeautifulSoup(response.text, "html.parser")

        fecha = extract(soup, [
            "div.post-date",
            "div.autor-fecha-container p.fecha"
        ])
        if validate and not fecha: return None

        titulo = extract(soup, [
            "h1.post-title",
            "h1.titulo"
        ])
        if validate and not titulo: return None

        autor = extract(soup, [
            "div.autores-trust-project div.contenedor-datos p.nombres a",
            "div.author div.creditos-nota div.autores span.autor b",
            "div.autor-opinion div.informacion a.nombre",
        ])
        if validate and not autor: return None

        desc_autor = extract(soup, [
            "div.autores-trust-project div.contenedor-datos p.cargo",
            "div.autor-opinion div.informacion p.cargo"
        ])

        abstract = extract(soup, [
            "div.post-main div.post-content div.post-excerpt p",
        ])

        # **Mover a su función propia para poder realizar validaciones
        cuerpo = (
            "\n".join([
                p.get_text(strip = True) 
                for p in soup.select("div.post-main div.post-content div.container-redes-contenido p")
                if p.get_text(strip = True)
            ])
        )
        if validate and not cuerpo: return None

        multimedia = extract_multimedia(soup, [
            "div.post-main div.post-image img",
            "div.post-main div.post-content div.container-redes-contenido img"
        ])
        if validate and not multimedia: return None

        return {
            "url": url,
            "titulo": titulo,
            "fecha": fecha,
            "autor": autor,
            "desc_autor": desc_autor,
            "abstract": abstract,
            "cuerpo": cuerpo,
            "multimedia": multimedia
        }

    except Exception as e:
        print(f"Error al scrapear la siguiente url:\n{url}\nDetalle: {e}")
        return None


def main():
    test_url = "https://www.biobiochile.cl/noticias/dopamina/2025/10/30/una-humillacion-critican-eliminacion-de-nidyan-fabregat-de-fdb-y-apuntan-contra-vasco-moulian.shtml"
    noticia = scrap_news_article(test_url)
    if noticia:
        print(json.dumps(noticia, indent = 3, ensure_ascii = False))


# Links ya testeados
# 1. "https://www.biobiochile.cl/noticias/nacional/chile/2025/10/12/franco-parisi-creo-que-paso-a-segunda-vuelta-con-jara-no-hay-tanto-voto-de-ultraderecha-en-chile.shtml"
# 2. "https://www.biobiochile.cl/noticias/ciencia-y-tecnologia/adelantos/2025/10/10/de-madera-tierra-y-techos-verdes-presentan-mat-la-primera-casa-chilena-sustentable-y-transportable.shtml"
# 3. "https://www.biobiochile.cl/noticias/artes-y-cultura/actualidad-cultural/2025/09/25/11-dias-de-actividades-trae-bienal-de-arquitectura-y-programa-enfocado-en-revitalizacion-de-la-ciudad.shtml"
# 4. "https://www.biobiochile.cl/noticias/servicios/explicado/2024/11/13/los-hombres-lo-desean-mas-que-las-mujeres-5-mitos-sobre-el-sexo-explicado-por-expertos.shtml"
# 5. "https://www.biobiochile.cl/noticias/servicios/toma-nota/2025/03/16/viajar-y-comer-por-chile-los-menus-imperdibles-a-lo-largo-del-pais-segun-nueva-guia-gastronomica.shtml"

if __name__ == "__main__":
    main()