from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


def extract(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default=None
) -> str | None:
    """
    Busca texto dentro de elementos específicos mediante múltiples selectores CSS.
    Retorna el primer texto encontrado o un valor por defecto.
    """

    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = info.get_text(strip=True, separator=" ")
            if txt:
                return txt
    return default


def extract_text_only(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default=None
) -> str | None:
    
    """
    Similar a extract(), pero obtiene solo texto directo, ignorando nodos hijos
    (útil para fechas o autores anidados).
    """

    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = " ".join(info.find_all(string=True, recursive=False)).strip()
            if txt:
                return txt

    return default


def extract_datetime(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default=None
) -> str | None:
    
    """
    Misma funcionalidad que extract(), con la diferencia de que devuelve la propiedad "datetime"
    en vez del texto del elemento.
    """

    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            txt = info["datetime"]
            if txt:
                return txt

    return default


def extract_images(
    soup: BeautifulSoup, selectors: list, default: str = ""
) -> list[str]:
    """
    Busca imágenes o elementos multimedia dentro de los selectores indicados.
    Reconoce atributos como src, data-src y data-lazy-src, e incluso URLs embebidas en style.
    """

    images = set()
    for sel in selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")

            if not src and img.has_attr("style"):
                match = re.search(r"background-image\s*:\s*url\((.*?)\)", img["style"])
                if match:
                    src = match.group(1).strip(" \"'")

            if src and isinstance(src, str):
                url = urljoin(default, src.strip())
                images.add(url)

    return list(images)


def extract_body(soup: BeautifulSoup, selectors: list, default: str = "") -> str:
    """
    Llama a extract_multiple y lo deja en un formato conveniente para un párrafo
    """

    cuerpo = extract_multiple(soup, selectors)
    if cuerpo:
        return "\n".join(cuerpo)
    return None
    

def extract_multiple(soup: BeautifulSoup, selectors: list, default: str = "") -> str:
    """
    Recorre selectores de contenido para construir una lista con los múltiples
    elementos que encuentre.
    """

    elementos = []
    for sel in selectors:
        for parrafo in soup.select(sel):
            if parrafo:
                txt = parrafo.get_text(strip=True, separator=" ")
                elementos.append(txt) if txt else elementos.append(default)

    if not elementos:
        return None
    else:
        return elementos
