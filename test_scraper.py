import csv
import json
import argparse
from sys import exit
from scraper.scraper_biobio import scrap_news_article
import time
import os

DIRECCION_CRAWLER = "Crawler/biobiochile.csv" # Cambiar antes de ejecutar
DIRECCION_OUTPUT = "scraper/data/output.json"

def main(desde: int = 1, hasta: int = None, output: bool = False):

    # Extraer la información del crawler
    try:
        with open(DIRECCION_CRAWLER, "r", newline = "", encoding = "utf-8") as f:
            reader = csv.reader(f)
            lista_url = [linea for linea in reader if linea]
    
    except Exception as e:
        print(f"Error de ejecución.\n-> {e}\nHint: Ejecutar el crawler primero y asegurarse que la dirección del mismo sea correcta.")
        exit(1)

    # Definir el archivo para escribir el output del scraping
    if output:
        output_file = open(DIRECCION_OUTPUT, 'w', encoding = "utf-8")
        output_file.write("[\n")
        first = True

    # Scrapear por cada URL obtenida por el crawler
    start_time = time.time()
    total = len(lista_url)
    exitos = 0
    fallos = 0

    for index, articulo in enumerate(lista_url, start = 1):
        if index < desde:
            print(f"Saltando url n° {index}")
            continue

        if hasta and index > hasta:
            break 

        try:
            url = articulo[0]
            tags = []   # por ahora no hay tags
            #t, url = articulo
            #tags = t.split("/")
            doc = scrap_news_article(url, tags, validate = True)

            if (isinstance(doc, dict)):
                exitos += 1
                print(f"Url {index} scrapeada exitosamente")
                if output:
                    if not first: output_file.write(",\n")
                    json.dump(doc, output_file , ensure_ascii = False, indent = 4)
                    first = False
            else:
                fallos += 1
                print(f"Error al scrapear la url n° {index}") 
                break

        except Exception as e:
            print(f"Error inesperado al scrapear\n-> {e}")
            break

    #Metricas del scraping    
    duracion = time.time() - start_time
    porcentaje = (exitos / total) * 100 if total > 0 else 0
    noticias_por_minuto = exitos / (duracion / 60) if duracion > 0 else 0
    tiempo_promedio = duracion / exitos if exitos > 0 else 0

    os.makedirs("metrics", exist_ok=True)
    with open("metrics/scraper_metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_urls_procesadas": total,
            "scrape_exitosos": exitos,
            "scrape_fallidos": fallos,
            "porcentaje_exito": round(porcentaje, 2),
            "duracion_segundos": round(duracion, 2),
            "noticias_por_minuto": round(noticias_por_minuto, 3),
            "tiempo_promedio_scrape": round(tiempo_promedio, 3)
        }, f, ensure_ascii=False, indent=4)


    # Cerrar el archivo del output
    if output:
        output_file.write("\n]")
        output_file.close()


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description = "Ejecución:\n\tpython.exe test_scraper.py --desde <int> --hasta <int>")
    parser.add_argument("--desde", type = int, default = None, help = "Desde qué línea del archivo .csv se comienza a scrappear")
    parser.add_argument("--hasta", type = int, default = None, help = "Hasta qué línea del archivo .csv se scrappea")
    parser.add_argument("--output", action = "store_true", help = "Incluir esta flag si se desea que el output del scraping sea escrito en un archivo output.json dentro de la carpeta scraper/data")

    args = parser.parse_args()

    desde = args.desde if args.desde else 1
    hasta = args.hasta if args.hasta else None
    output = args.output

    #print(f"desde: {desde}\nhasta: {hasta}\noutput: {output}")
    main(desde = desde, hasta = hasta, output = output)

'''
Enviar 3 tipos de mensajes:
- Mensajes de éxito cuando se logró scrappear un medio
- Mensajes de falla cuando no se logró scrappear un medio
- Datos scrappeados
'''