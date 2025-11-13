import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import json, csv
import os, sys
import pika


# Timeouts (ms) y waits
GOTO_TIMEOUT_START = 15000       # 15s para la home
GOTO_TIMEOUT_CATEGORY = 15000    # 15s para páginas de categoría
SHORT_WAIT = 500                 # 0.5s para wait_for_timeout
CLICK_WAIT = 500                 # 0.5s tras click

# Diccionario configuración sitios
SITES = {
    "biobiochile": {
        "start_url": "https://www.biobiochile.cl/",     # URL de la página
        "category_pattern": "lista/categorias",         # Slug página para reconcoer categorias
        "news_pattern": ["/noticias/"],                 # Slug página para reconocer links de noticias
        "load_more_selector": ".fetch-btn",             # Classname boton cargar mas links de la página
        "pagination_type": "loadmore",                  # Forma en que se cargan mas links, loadmore asume boton jscript
        "max_clicks": 2                                 # Cantidad máxima de clikcs de este boton en la página
    }
}

SCRAPER_QUEUE = "scraper_queue"
LOG_QUEUE = "log_queue"

# Conectar con RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
# Abrir un canal de conexión con RabbitMQ
crawler_channel = connection.channel()
# declarar el canal
for q in [SCRAPER_QUEUE, LOG_QUEUE]:
    crawler_channel.queue_declare(queue=q, durable=True)
# conjunto global para evitar enviar duplicados
seen_links = set()

def send_link (link, tags):
    message = {
        "url":link,
        "tags":tags,
    }
    # Enviar el mensaje al componente de scrapping
    crawler_channel.basic_publish(
        exchange='',
        routing_key = SCRAPER_QUEUE,
        body = json.dumps(message),
        properties = pika.BasicProperties(
            delivery_mode = 2
        )
    )
    print("Mensaje enviado hacia scraper desde crawler...")

# Función para bloquear recursos al buscar links de noticias desde una página con botón "Cargar más"
async def _block_assets(page):
    '''
    Función para bloquear recursos al buscar links de noticias desde una página con botón "cargar más noticias"
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

    except Exception:
        categoria = slug  # fallback
    
    return categoria


async def scrape_category_loadmore(page, category_url, load_more_selector, news_pattern, max_clicks=10):
    '''
    Crawl de la página de categorías con la modalidad "loadmore", es decir, página de categoría que
    posee un botón de "cargar más noticias".
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
        except Exception:
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
    Crawl de las categorías de noticias de la página
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
            print(f"> Timeout/Err en goto start_url (categories) {start_url}: {e}")
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
    Crawl de los links de noticias de cada categoría
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
            print(f"> Timeout/Err en goto start_url (crawl_news) {start_url}: {e}")
            await browser.close()
            return set()

        # Inicia scrap categorias
        for cat_url in category_links:
            print(f"> {start_url} → {cat_url}")
            if pagination_type == "loadmore":
                cat_news = await scrape_category_loadmore(
                    page,
                    cat_url,
                    site_config["load_more_selector"],
                    news_pattern,
                    site_config["max_clicks"]
                )
            else:
                cat_news = set()


            
            slug = cat_url.rstrip("/").split("/")[-1]

            for link in cat_news:

                categoria = get_category(link, slug)

                news.add((categoria, link))

                # Envia link y categoria a Scrapper si este no ha sido enviado previamente
                if link not in seen_links:
                    send_link(link, categoria)
                    seen_links.add(link)

        await browser.close()

    return news


async def main():

    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
        medio = "biobiochile"
    else:
        medio = sys.argv[1]

    config = SITES[medio]

    print(f"\n🌐 CRAWLEANDO SITIO: {medio}")

    start_time = time.time() #inicio medicion tiempo

    # 
    categorias = await crawl_categories(config)
    print(f">> Total categorias encontradas en {medio}: {len(categorias)}\n")

    total_categorias = len(categorias)
    all_news = set()
    tope = 0
    categorias = list(categorias)

    # Avance procesado en lotes para futura paralelización
    for i in range (0, len(categorias), 10):
        if i + 10 < len(categorias):
            tope = i+10
        else:
            tope = len(categorias)
        news_batch = await crawl_news(config, categorias[i:tope])
        all_news.update(news_batch)
    
    # Metricas del crawler
    duracion = time.time() - start_time
    total_urls = len(all_news)
    promedio_por_categoria = total_urls/total_categorias if total_categorias > 0 else 0
    urls_por_minuto = total_urls / (duracion / 60) if duracion > 0 else 0
    os.makedirs("metrics", exist_ok=True)

    with open("metrics/crawler_metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "sitio": medio,
            "total_categorias": total_categorias,
            "total_urls_encontradas": total_urls,
            "urls_por_categoria": round(promedio_por_categoria, 3),
            "duracion_segundos": round(duracion, 2),
            "urls_por_minuto": round(urls_por_minuto, 2)
        }, f, ensure_ascii=False, indent=4)


    # Guardar links en un csv
    os.makedirs("Crawler", exist_ok=True)
    csv_file_path = f"Crawler/{medio}.csv"
    with open(csv_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for categoria, link in list(all_news):
            csv_writer.writerow([categoria, link])
        
    print(f"Links guardados en {csv_file_path}")


# Ejecutar
if __name__ == "__main__":
    asyncio.run(main())