import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


def extract(soup: BeautifulSoup, selectors: list[str], default = None) -> str | None:
    '''
    Busca texto dentro de elementos específicos mediante múltiples selectores CSS.
    Retorna el primer texto encontrado o un valor por defecto.
    '''
    
    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = info.get_text(strip = True, separator = " ")
            if txt: 
                return txt
    return default


def extract_text_only(soup: BeautifulSoup, selectors: list[str], default = None) -> str | None:
    '''
    Similar a extract(), pero obtiene solo texto directo, ignorando nodos hijos 
    (útil para fechas o autores anidados).
    '''

    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = " ".join(info.find_all(string = True, recursive = False)).strip()
            if txt:
                return txt
            
    return default


def extract_multimedia(soup: BeautifulSoup, selectors: list, default: str = "") -> list[str]:
    '''
    Busca imágenes o elementos multimedia dentro de los selectores indicados. 
    Reconoce atributos como src, data-src y data-lazy-src, e incluso URLs embebidas en style.
    '''

    images = set()
    for sel in selectors:
        for img in soup.select(sel):
            src = (
                img.get("src") or
                img.get("data-src") or
                img.get("data-lazy-src")
            )

            if not src and img.has_attr("style"):
                match = re.search(r'background-image\s*:\s*url\((.*?)\)', img["style"])
                if match:
                    src = match.group(1).strip(' "\'')

            if src and isinstance(src, str):
                url = urljoin(default, src.strip())
                images.add(url)

    return list(images)


def extract_body(soup: BeautifulSoup, selectors: list, default: str = "") -> str:
    '''
    Recorre selectores de contenido para construir el cuerpo completo del artículo. 
    Devuelve un texto unificado con saltos de línea.
    '''
    
    cuerpo = []
    for sel in selectors:
        for parrafo in soup.select(sel):
            if parrafo:
                txt = parrafo.get_text(strip = True, separator = " ")
                cuerpo.append(txt) if txt else cuerpo.append(default)
    
    if not cuerpo:
        return None
    else:
        return "\n".join(cuerpo)


def scrap_news_article(url: str, tags: list[str], validate: bool = False) -> dict | None:
    '''
    Realiza el scraping completo de una noticia individual. Esta función puede devolver 
    tanto un diccionario de python como un None, dependiendo de los parámetros y el output.
    '''
    
    try:
        # Realizar una request al sitio
        response = requests.get(url, timeout = 10)
        response.encoding = "utf-8"
        response.raise_for_status()

        # Parsear y extraer respuesta
        soup = BeautifulSoup(response.text, "html.parser")

        fecha = (
            extract(soup, [
                "div.post-date",
                "div.autor-fecha-container p.fecha",
                "div.nota p.fecha",
                "div.nota-top-content div.top-content-text p.fecha",
            ])
            or
            extract_text_only(soup, [
                "div.fecha-visitas p.fecha",
            ])
        )
        if validate and not fecha: return None

        titulo = extract(soup, [
            "h1.post-title",
            "h1.titulo",
            "div.nota-top-content div.top-content-text h1.titular",
        ])
        if validate and not titulo: return None

        autor = extract(soup, [
            "div.autores-trust-project div.contenedor-datos p.nombres a",
            "div.author div.creditos-nota div.autores span.autor b",
            "div.autor-opinion div.informacion a.nombre",
            "div.autor div.creditos-nota div.autores span.autor b a",
            "div.container-nota-body span.autor b a",
        ])

        desc_autor = extract(soup, [
            "div.autores-trust-project div.contenedor-datos p.cargo",
            "div.autor-opinion div.informacion p.cargo",
        ])

        abstract = extract(soup, [
            "div.post-main div.post-content div.post-excerpt p",
            "div.contenido-nota div.post-excerpt p"
        ])

        cuerpo = extract_body(soup, [
            "div.post-main div.post-content div.container-redes-contenido p, div.post-main div.post-content div.container-redes-contenido h2",
            "div.container-redes-contenido div.contenido-nota h2, div.container-redes-contenido div.contenido-nota p",
            "div.contenido-nota div[class^='banners-contenido-nota-'] h2, div.contenido-nota div[class^='banners-contenido-nota-'] p",
            "div.container-nota-body div.nota-content div.contenido p, div.container-nota-body div.nota-content div.contenido h2",
        ])
        if validate and not cuerpo: return None

        multimedia = extract_multimedia(soup, [
            "div.post-main div.post-image img",
            "div.post-main div.post-content div.container-redes-contenido img",
            "div.imagen",
            "div.contenedor-imagen-titulo div.imagen img",
            "div.nota-top-content img"
        ])

        return {
            "url": url,
            "titulo": titulo,
            "fecha": fecha,
            "tags": tags,
            "autor": autor,
            "desc_autor": desc_autor,
            "abstract": abstract,
            "cuerpo": cuerpo,
            "multimedia": multimedia,
            "tipo_multimedia": "imagen"
        }

    except Exception as e:
        print(f"Error al scrapear la siguiente url:\n{url}\nDetalle: {e}")
        return None


def main():
    test_url = "https://www.biobiochile.cl/noticias/servicios/beneficios/2025/10/23/asi-funciona-el-beneficio-estrudiantil-que-cubre-mas-de-un-millon-de-pesos-del-arancel.shtml"
    noticia = scrap_news_article(test_url, [])
    if noticia:
        print(json.dumps(noticia, indent = 3, ensure_ascii = False))


# Links testeados que causaron errores durante el desarrollo
# 1. "https://www.biobiochile.cl/noticias/nacional/chile/2025/10/12/franco-parisi-creo-que-paso-a-segunda-vuelta-con-jara-no-hay-tanto-voto-de-ultraderecha-en-chile.shtml"
# 2. "https://www.biobiochile.cl/noticias/ciencia-y-tecnologia/adelantos/2025/10/10/de-madera-tierra-y-techos-verdes-presentan-mat-la-primera-casa-chilena-sustentable-y-transportable.shtml"
# 3. "https://www.biobiochile.cl/noticias/artes-y-cultura/actualidad-cultural/2025/09/25/11-dias-de-actividades-trae-bienal-de-arquitectura-y-programa-enfocado-en-revitalizacion-de-la-ciudad.shtml"
# 4. "https://www.biobiochile.cl/noticias/servicios/explicado/2024/11/13/los-hombres-lo-desean-mas-que-las-mujeres-5-mitos-sobre-el-sexo-explicado-por-expertos.shtml"
# 5. "https://www.biobiochile.cl/noticias/servicios/toma-nota/2025/03/16/viajar-y-comer-por-chile-los-menus-imperdibles-a-lo-largo-del-pais-segun-nueva-guia-gastronomica.shtml"
# 6. "https://www.biobiochile.cl/noticias/dopamina/2025/10/30/una-humillacion-critican-eliminacion-de-nidyan-fabregat-de-fdb-y-apuntan-contra-vasco-moulian.shtml"
# 7. "https://www.biobiochile.cl/especial/bio-bio-tuercas/noticias/2025/10/31/massa-califica-el-crashgate-como-el-mayor-escandalo-en-la-historia-del-deporte-reclama-titulo-de-f1.shtml"
# 8. "https://www.biobiochile.cl/especial/bbcl-investiga/noticias/entrevistas/2025/11/01/falta-una-izquierda-mas-de-resultados-que-de-eslogan-carlos-cuadrado-ppd-candidato-a-diputado.shtml"
# 9. "https://www.biobiochile.cl/especial/bbcl-investiga/noticias/de-pasillo/2025/10/30/embargan-bienes-de-alvaro-saieh-por-deuda-de-27-millones-de-dolares-con-banco-itau.shtml"
# 10. "https://www.biobiochile.cl/noticias/servicios/beneficios/2025/10/23/asi-funciona-el-beneficio-estrudiantil-que-cubre-mas-de-un-millon-de-pesos-del-arancel.shtml"


if __name__ == "__main__":
    main()