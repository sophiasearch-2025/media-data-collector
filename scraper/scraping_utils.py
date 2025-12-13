from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


def extract(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default = None
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


def extract_multiple(
    soup: BeautifulSoup, 
    selectors: list, 
    default = ""
) -> list:
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

    if elementos:
        return elementos
    
    return default


def extract_text_only(
    soup: BeautifulSoup, 
    selectors: list[str], 
    default = None
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
    default = None
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
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
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

    if images:
        return list(images)
    
    return default


def extract_image_with_description(
    soup: BeautifulSoup, 
    figure_selectors: list, 
    image_selectors: list,
    description_selectors: list,
    default = None
) -> list[dict]:
    '''
    Extrae las imágenes del artículo con sus descripciones y las recolecta en una lista
    con el siguiente formato:

    [
        { "url": <url-imagen>, "descripcion": <descripcion-imagen> },
        ...
    ]
    '''
    
    resultados = []

    for fig_sel in figure_selectors:
        for fig in soup.select(fig_sel):
            
            # Encontrar la imagen dentro del figure
            img = None
            for img_sel in image_selectors:
                img = fig.select_one(img_sel)
                if img:
                    break
            
            if not img:
                continue

            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )
            if not src:
                continue

            # Encontrar la descripción dentro del figure
            desc = None
            for desc_sel in description_selectors:
                desc = fig.select_one(desc_sel)
                if desc:
                    break
            
            desc_text = desc.get_text(strip = True) if desc else None

            # Incluir resultado
            resultados.append({
                "url": src,
                "descripcion": desc_text
            })

    if resultados:
        return resultados
    
    return default


def extract_videos(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> list[str]:
    '''
    Extrae todos los videos que encuentre del artículo y retorna una lista con sus url
    '''

    vids = []

    for sel in selectors:
        for vid in soup.select(sel):
            url = vid.get("src") or vid.get("data-src")
            if not url:
                continue

            if url.startswith("//"):
                url = "https:" + url

            vids.append(url)
    
    if vids:
        return vids
    
    return default


def extract_body_video(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> str:
    '''
    Extrae el video para aquellos artículos que son únicamente un video 
    (Utilizado en la tercera)
    '''
    
    for sel in selectors:
        info = soup.select_one(sel)
        if info:
            vid_url = info["src"]
            if vid_url:
                if vid_url.startswith("//"):
                    vid_url = "https:" + vid_url
                return vid_url

    return default


def extract_body(
    soup: BeautifulSoup, 
    selectors: list, 
    default = None
) -> str:
    """
    Llama a extract_multiple y lo deja en un formato conveniente para un párrafo
    """

    cuerpo = extract_multiple(soup, selectors)
    if cuerpo:
        return "\n".join(cuerpo)
    
    return default


def extract_minutoaminuto_entries(
    soup: BeautifulSoup, 
    fig_selectors: list,
    date_selectors: list,
    body_selectors: list, 
    default = None
) -> list[dict]:
    '''
    Extrae todos los pequeños párrafos que se encuentren dentro de fig_selectors
    '''

    resultado = []

    for fig_sel in fig_selectors:
        for fig in soup.select(fig_sel):

            fecha = None
            for date_sel in date_selectors:
                date_tag = fig.select_one(date_sel)
                if date_tag and date_tag.has_attr("datetime"):
                    fecha = date_tag["datetime"]
                    break
            
            cuerpo_partes = []
            for body_sel in body_selectors:
                for elem in fig.select(body_sel):
                    txt = elem.get_text(strip=True, separator=" ")
                    if txt:
                        cuerpo_partes.append(txt)

            cuerpo = "\n".join(cuerpo_partes) if cuerpo_partes else None

            resultado.append({
                "fecha": fecha,
                "cuerpo": cuerpo
            })

    if resultado:
        return resultado
    
    return default
            

def extract_filtered_body(
    soup: BeautifulSoup, 
    selectors: list, 
    excluded_selectors: list,
    default = None
) -> str:
    '''
    Extrae el cuerpo de la noticia excluyendo los contenidos de ciertos componentes
    incluidos en excluded_selectors
    '''

    elementos = []
    for sel in selectors:
        for parrafo in soup.select(sel):
            if parrafo:
                can_continue = True

                for excl in excluded_selectors:
                    nombre, clase = excl.split(".")
                    if parrafo.find_parent(nombre, class_ = clase):
                        can_continue = False
                        break
                
                if not can_continue:
                    continue

                txt = parrafo.get_text(strip=True, separator=" ")
                if txt:
                    elementos.append(txt)

    if elementos:
        return "\n".join(elementos)
    
    return default
