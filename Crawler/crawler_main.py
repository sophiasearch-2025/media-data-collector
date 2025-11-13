from crawler_biobio import *
import pika

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

async def main():

    if len(sys.argv) != 2:
        print("Se debe ejecutar con un solo argumento, y debe ser el nombre del medio.")
    
    medio = sys.argv[1]

    site = SITES[medio]
    config = site.items()

    print(f"\n🌐 CRAWLEANDO SITIO: {site}")

    start_time = time.time() #inicio medicion tiempo

    # 
    categorias = await crawl_categories(config)
    print(f">> Total categorias encontradas en {site}: {len(categorias)}\n")

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
            "sitio": site,
            "total_categorias": total_categorias,
            "total_urls_encontradas": total_urls,
            "urls_por_categoria": round(promedio_por_categoria, 3),
            "duracion_segundos": round(duracion, 2),
            "urls_por_minuto": round(urls_por_minuto, 2)
        }, f, ensure_ascii=False, indent=4)


    # Guardar links en un csv
    os.makedirs("Crawler", exist_ok=True)
    csv_file_path = f"Crawler/{site}.csv"
    with open(csv_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for categoria, link in list(all_news):
            csv_writer.writerow([categoria, link])
        
    print(f"Links guardados en {csv_file_path}")


# Ejecutar
if __name__ == "__main__":
    asyncio.run(main())