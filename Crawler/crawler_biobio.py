import asyncio
import csv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import json
import os



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

# 🧭 Función para scrapear noticias desde una página con botón "Cargar más"
async def scrape_category_loadmore(page, category_url, load_more_selector, news_pattern, max_clicks=10):
    news_links = set()
    await page.goto(category_url, timeout=60000)
    await page.wait_for_timeout(3000)

    for i in range(max_clicks):
        boton = await page.query_selector(load_more_selector)
        if boton is None:
            break
        try:
            await page.evaluate("(btn) => btn.scrollIntoView()", boton)
            await boton.click(force=True)
            await page.wait_for_timeout(1000)
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

# 🕸️ Función principal
async def crawl_site(site_config):
    start_time = time.time() #inicio medicion tiempo

    start_url = site_config["start_url"]
    category_pattern = site_config["category_pattern"]
    news_pattern = site_config["news_pattern"]
    pagination_type = site_config["pagination_type"]

    all_news = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(start_url, timeout=50000)
        await page.wait_for_timeout(2000)

        # Obtiene categorias
        soup = BeautifulSoup(await page.content(), "html.parser")
        category_links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/"):
                href = urljoin(start_url, href)
            if category_pattern in href:
                category_links.add(href)
        
        print(f"📄 Total categorias encontradas en {start_url}: {len(category_links)}")
        total_categorias = len(category_links)

        # Inicia scrap categorias
        for cat_url in category_links:
            print(f" ➡️ {start_url} → {cat_url}")
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
            all_news.update(cat_news)

        await browser.close()

        # Metricas del crawler
        duracion = time.time() - start_time
        total_urls = len(all_news)
        promedio_por_categoria = total_urls/total_categorias if total_categorias > 0 else 0
        urls_por_minuto = total_urls / (duracion / 60) if duracion > 0 else 0

        os.makedirs("metrics", exist_ok=True)
        with open("metrics/crawler_metrics.json", "w", encoding="utf-8") as f:
            json.dump({
                "sitio": start_url,
                "total_categorias": total_categorias,
                "total_urls_encontradas": total_urls,
                "urls_por_categoria": round(promedio_por_categoria, 3),
                "duracion_segundos": round(duracion, 2),
                "urls_por_minuto": round(urls_por_minuto, 2)
            }, f, ensure_ascii=False, indent=4)

    return all_news

async def main():
    for site, config in SITES.items():
        print(f"\n🌐 CRAWLEANDO SITIO: {site}")

        urls = await crawl_site(config)

        print(f"📰 Total noticias encontradas en {site}: {len(urls)}")

        for n in list(urls)[:10]:  # muestra las primeras 10
            print("  -", n)

        #Guardad links en un csv
        csv_file_path = f"Crawler/{site}.csv"
        with open(csv_file_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for link in list(urls):
                csv_writer.writerow([link])
        
        print(f"Links guardados en {csv_file_path}")


# 🧪 Ejecutar
if __name__ == "__main__":
    asyncio.run(main())