import json
import os
import sys
from datetime import datetime as dtime
from scraper.scraping_utils import extract, extract_body, extract_images, extract_datetime, extract_multiple

import pika
import requests
from bs4 import BeautifulSoup

# Importa scraping_results_send() desde logger/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger.queue_sender_scraper_results import scraping_results_send

SCRAPER_QUEUE = "scraper_queue"
LOG_QUEUE = "scraping_log_queue"
SEND_DATA_QUEUE = "send_data_queue"


def scrap_news_article(url: str, validate: bool = False) -> dict | list:
    """
    Realiza el scraping completo de una noticia individual. Esta función puede devolver
    tanto un diccionario de python como una lista con los elementos de la noticia faltantes,
    dependiendo de los parámetros y el output.
    """
    # Por mientras
    if "video" in url: return { "url": url, "contiene_video": True }

    invalid_args = []

    try:
        # Realizar una request al sitio
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"
        response.raise_for_status()

        # Parsear y extraer respuesta
        soup = BeautifulSoup(response.text, "html.parser")

        fecha = extract_datetime(
            soup,
            [
                "time.article-body__byline__date",
            ],
        )

        if validate and not fecha:
            invalid_args.append("fecha")

        titulo = extract(
            soup,
            [
                "h1.article-head__title",
            ],
        )
        if validate and not titulo:
            invalid_args.append("titulo")

        autor = extract(
            soup,
            [
                "a.article-body__byline__author",
                "span.article-body__byline__authors address"
            ],
        )

        abstract = extract(
            soup,
            [
                "h2.article-head__subtitle",
            ],
        )

        cuerpo = extract_body(
            soup,
            [
                "p.article-body__paragraph",
            ],
        )

        imagenes = extract_images(
            soup,
            [
                "figure.article-body__figure img.global-image",
            ],
        )

        desc_imagenes = extract_multiple(
            soup,
            [
                "span.article-body__figure__caption",
            ],
        )

        if validate and not cuerpo and not imagenes:
            invalid_args.append("cuerpo")

        if validate and len(invalid_args) >= 1:
            return invalid_args

        return {
            "titulo": titulo,
            "fecha": fecha,
            "autor": autor,
            "abstract": abstract,
            "cuerpo": cuerpo,
            "imagenes": imagenes,
            "descripcion_imagenes": desc_imagenes,
        }

    except Exception as e:
        print(f"Error al scrapear la siguiente url:\n{url}\nDetalle: {e}")
        return [e]
    


#---- DEBUG ----#
if __name__ == "__main__":
    test_url = "https://www.latercera.com/sociales/noticia/clientes-de-finning-se-reunen-en-evento-exclusiv0-durante-electric-mine/"
    noticia = scrap_news_article(test_url)
    if isinstance(noticia, dict):
        print(json.dumps(noticia, indent=3, ensure_ascii=False))

# Links testeados que causaron errores durante el desarrollo
# 1. https://www.latercera.com/mundo/noticia/carolin-emcke-el-discurso-del-odio-siempre-enmascara-su-propia-brutalidad/ 
# 2. https://www.latercera.com/sociales/noticia/clientes-de-finning-se-reunen-en-evento-exclusiv0-durante-electric-mine/