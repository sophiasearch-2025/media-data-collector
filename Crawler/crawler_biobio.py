import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from crawler_sender import *


# Timeouts (ms) y waits
GOTO_TIMEOUT_START = 15000       # 15s para la home
GOTO_TIMEOUT_CATEGORY = 15000    # 15s para páginas de categoría
SHORT_WAIT = 500                 # 0.5s para wait_for_timeout
CLICK_WAIT = 500                 # 0.5s tras click

seen_links = set()

# Función para bloquear recursos al buscar links de noticias desde una página con botón "Cargar más"
async def _block_assets(page):
    '''
    Función para bloquear recursos al buscar links de noticias
    desde una página con botón "cargar más noticias"
    '''
    async def handler(route):
        req = route.request
        if req.resource_type in ("image", "stylesheet", "font", "media"):
            await route.abort()
        else:
            await route.continue_()
    await page.route("**/*", handler)

def get_category(link, slug):
    '''
    Función que extrae las categorías del enlace de las noticias
    '''
    try:
        categoria = slug # valor por defecto

        # extrae la parte relevante después de /especial/ o /noticias/
        if "/especial/" in link:
            path = link.split("/especial/", 1)[1]
        elif "/noticias/" in link:
            path = link.split("/noticias/", 1)[1]
        else:
            path = None

        if path:
            parts = [p for p in path.split("/") if p]  # filtra vacíos
            categorias_parts = []
            for part in parts:
                # detener si encontramos un año (4 dígitos)
                if part.isdigit() and len(part) == 4:
                    break
                categorias_parts.append(part)
                if len(categorias_parts) == 3:  # máximo 3 niveles
                    break

            # si el primer segmento es "biobiochile" lo descartamos
            if categorias_parts and categorias_parts[0].lower() == "biobiochile":
                categorias_parts = categorias_parts[1:]

            # quitar segmento redundante "noticias" (ej. bbcl-investiga/noticias/articulos -> bbcl-investiga/articulos)
            if len(categorias_parts) >= 2 and categorias_parts[1].lower() == "noticias":
                categorias_parts.pop(1)

            # caso especial: noticias-patrocinadas -> usar solo 'noticias-patrocinadas'
            if categorias_parts and categorias_parts[0].lower() == "noticias-patrocinadas":
                categoria = "noticias-patrocinadas"

            elif categorias_parts:
                categoria = "/".join(categorias_parts)

            else:
                categoria = slug

    except Exception as e:
        send_error(link, e, f"Error al obtener tags de categorías de {link}")
        categoria = slug  # fallback
    
    return categoria


async def scrape_category_loadmore(page, category_url, load_more_selector, news_pattern, max_clicks=10):
    '''
    Crawl de la página de categorías con la modalidad "loadmore", es decir,
    página de categoría que posee un botón de "cargar más noticias".
    '''
    news_links = set()
    try:
        await page.goto(category_url, timeout=GOTO_TIMEOUT_CATEGORY, wait_until="domcontentloaded")
        await page.wait_for_timeout(SHORT_WAIT)
    except Exception as e:
        print(f"> Timeout/Error en goto category {category_url}: {e}")
        return news_links

    for i in range(max_clicks):
        boton = await page.query_selector(load_more_selector)
        if boton is None:
            break
        try:
            await page.evaluate("(btn) => btn.scrollIntoView()", boton)
            await boton.click(force=True)
            await page.wait_for_timeout(CLICK_WAIT)
        except Exception as e:
            send_error(category_url, e, f"Error al cargar más noticias en {category_url}")
            break

    soup = BeautifulSoup(await page.content(), "html.parser")
    for a_tag in soup.find_all("a", href=True):
        link = a_tag["href"]
        if link.startswith("/"):
            link = urljoin(category_url, link)
        if any(p in link for p in news_pattern):
            news_links.add(link)

    return news_links


async def crawl_categories(site_config):
    '''
    Función que Crawl de las categorías de noticias de la página,
    entrega set de links de categorías encontradas
    '''
    start_url = site_config["start_url"]
    category_pattern = site_config["category_pattern"]

    category_links = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await _block_assets(page)
        try:
            await page.goto(start_url, timeout=GOTO_TIMEOUT_START, wait_until="domcontentloaded")
            await page.wait_for_timeout(SHORT_WAIT)
        except Exception as e:
            send_error(start_url, e, f"Error de 'Timeout' crawl links categorías: {start_url}")
            await browser.close()
            return set()

        # Obtiene categorias
        soup = BeautifulSoup(await page.content(), "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/"):
                href = urljoin(start_url, href)
            if category_pattern in href:
                category_links.add(href)

        await browser.close()
            
    return category_links


async def crawl_news(site_config, category_links):
    '''
    Crawl de los links de noticias de cada categoría,
    entrega set de tuplas de links de noticias y sus tags de
    categorías encontradas.
    '''
    start_url = site_config["start_url"]
    news_pattern = site_config["news_pattern"]
    pagination_type = site_config["pagination_type"]

    news = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await _block_assets(page)
        try:
            await page.goto(start_url, timeout=GOTO_TIMEOUT_START, wait_until="domcontentloaded")
            await page.wait_for_timeout(SHORT_WAIT)
        except Exception as e:
            send_error(start_url, e, f"Error de 'Timeout' crawl links noticias: {start_url}")
            await browser.close()
            return set()

        # Inicia scrap categorias
        for cat_url in category_links:
            print(f"> {start_url} → {cat_url}")
            if pagination_type == "loadmore":
                # Busqueda de links de noticias por cada categoria
                cat_news = await scrape_category_loadmore(
                    page,
                    cat_url,
                    site_config["load_more_selector"],
                    news_pattern,
                    site_config["max_clicks"]
                )
            else:
                # Futura Busqueda links en paginación
                cat_news = set()

            slug = cat_url.rstrip("/").split("/")[-1]

            for link in cat_news:
                # Link encontrado se le obtiene sus tags de categorías
                categoria = get_category(link, slug)
                # Link y sus categorías son añadidos al conjunto de noticias encontradas
                news.add((categoria, link))
                # Envia link y categoria a Scrapper si este no ha sido enviado previamente
                if link not in seen_links:
                    send_link(link, categoria)
                    seen_links.add(link)

        await browser.close()

    return news