from Crawler.crawler_loadmore import *
import asyncio, json, csv
import time, os, sys

# Diccionario configuración sitios
SITES = {
    "biobiochile": {
        "start_url": "https://www.biobiochile.cl/",     # URL de la página
        "category_pattern": "lista/categorias",         # Slug página para reconcoer categorias
        "news_pattern": ["/noticias/"],                 # Slug página para reconocer links de noticias
        "load_more_selector": ".fetch-btn",             # Classname boton cargar mas links de la página
        "pagination_type": "loadmore",                  # Forma en que se cargan mas links, loadmore asume boton jscript
        "max_clicks": 2                                 # Cantidad máxima de clikcs de este boton en la página
    },
    "latercera": {
        "start_url":"https://www.latercera.com/",
        "category_pattern": "canal",         # Slug página para reconcoer categorias
        "news_pattern": ["/noticia/"],                 # Slug página para reconocer links de noticias
        "load_more_selector": ".result-list__see-more",             # Classname boton cargar mas links de la página
        "pagination_type": "loadmore",                  # Forma en que se cargan mas links, loadmore asume boton jscript
        "max_clicks": 2 
    }
}

async def main():

    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
    else:
        medio = sys.argv[1]
        try:
            config = SITES[medio]
        except Exception as e:
            send_error(medio, e, "Medio no encontrado en configuraciónes de sitios")
            return

    print(f"\n🌐 CRAWLEANDO SITIO: {medio}")

    start_time = time.time() #inicio medicion tiempo

    # Pasar el medio a crawler_biobio para que lo use en send_link
    sys.modules['crawler_biobio'].medio = medio

    # Crawl links de categorías en el sitio
    categorias = await crawl_categories(config)
    print(f">> Total categorias encontradas en {medio}: {len(categorias)}\n")

    total_categorias = len(categorias)
    all_news = set()
    categorias = list(categorias)

    news_batch = await crawl_news(config, categorias)
    all_news.update(news_batch)
    
    # Metricas del crawler
    duracion = time.time() - start_time
    total_urls = len(all_news)
    promedio_por_categoria = total_urls/total_categorias if total_categorias > 0 else 0
    urls_por_minuto = total_urls / (duracion / 60) if duracion > 0 else 0
    os.makedirs("metrics", exist_ok=True)

    # Leer métricas existentes o crear diccionario vacío
    metrics_file = "metrics/crawler_metrics.json"
    existing_metrics = {}
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                existing_metrics = json.load(f)
        except Exception:
            existing_metrics = {}

    # Actualizar solo las métricas del sitio actual
    existing_metrics[medio] = {
        "total_categorias": total_categorias,
        "total_urls_encontradas": total_urls,
        "urls_por_categoria": round(promedio_por_categoria, 3),
        "duracion_segundos": round(duracion, 2),
        "urls_por_minuto": round(urls_por_minuto, 2)
    }

    # Guardar Métricas en archivo json
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(existing_metrics, f, ensure_ascii=False, indent=4)


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