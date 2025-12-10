import json
import os
import sys
from datetime import datetime as dtime
from scraper.scraping_utils import (
    extract, 
    extract_body, 
    extract_datetime, 
    extract_videos, 
    extract_body_video,
    extract_image_with_description,
    extract_filtered_body,
    extract_minutoaminuto_entries
)

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

    invalid_args = []

    try:
        # Realizar una request al sitio
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"
        response.raise_for_status()

        # Parsear y extraer respuesta
        soup = BeautifulSoup(response.text, "html.parser")

        categoria = extract(soup, ["span.article-head__section__name", "span.article-head__section__name a.base-link"])

        fecha = extract_datetime(
            soup,
            [
                "time.article-body__byline__date",
            ],
        )

        if validate and not fecha and categoria.lower().strip() != "en vivo":
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

        cuerpo = None
        if categoria.lower().strip() == "en vivo":
            cuerpo = extract_filtered_body(
                soup,
                [ "p.article-body__paragraph, h2.article-body__heading-h2" ],
                [ "div.liveblog-entry" ]
            )
        elif categoria.strip().lower() == "videos":
            cuerpo = extract_body_video(
                soup,
                [
                    "div.article-body__raw-html iframe"
                ],
            )
        else:
            cuerpo = extract_body(
                soup,
                [
                    "p.article-body__paragraph, h2.article-body__heading-h2",
                ],
            )

        entries = None
        if categoria.lower().strip() == "en vivo":
            entries = extract_minutoaminuto_entries(
                soup,
                [ "div.liveblog-entry" ],
                [ "time.liveblog-entry__date" ],
                [ "div.liveblog-entry__content h2, div.liveblog-entry__content p" ]
            )

        imagenes = extract_image_with_description(
            soup,
            [ "figure.article-body__figure" ],
            [ "img.global-image" ],
            [ "span.article-body__figure__caption" ],
        )
    
        videos = extract_videos(
            soup,
            [
                "div.article-body__oembed iframe",
                "div.article-body__oembed-youtube iframe",
                "div.article-body__raw-html iframe"
            ],
        )

        if validate and not cuerpo and not imagenes:
            invalid_args.append("cuerpo")

        if validate and len(invalid_args) >= 1:
            return invalid_args

        return {
            "categoria": categoria,
            "titulo": titulo,
            "fecha": fecha,
            "autor": autor,
            "abstract": abstract,
            "cuerpo": cuerpo,
            "cuerpo_en_vivo": entries,
            "imagenes": imagenes,
            "videos": videos
        }

    except Exception as e:
        print(f"Error al scrapear la siguiente url:\n{url}\nDetalle: {e}")
        return [e]
    

def consume_article(ch, method, properties, body):
    """
    Función llamada por RabbitMQ cada vez que le llegue un artículo extraido
    por el crawler para scrapear.
    """

    starting_time = dtime.now()
    try:
        # Cargar el mensaje recibido por RabbitMQ y extraer la URL
        mensaje = json.loads(body)
        url = mensaje["url"]
        print(f"Mensaje recibido en scraper.")

        # Scrapear la URL
        scraper_results = scrap_news_article(url, validate = True)

        if not isinstance(scraper_results, dict):
            raise Exception(f"Error en el scraping: { (f'Faltaron los siguientes parámetros críticos: {scraper_results}' if isinstance(scraper_results, list) else scraper_results) }")

        finishing_time = dtime.now()

        # --- mensaje para logs ---
        # Envío desde scraping_resuls_send()
        scraping_results_send(
            url,
            mensaje["medio"] if ("medio" in mensaje) else "",
            starting_time,
            "success",
            finishing_time,
            None,
            scraper_results.get("fecha", None),
        )
        print("Mensaje enviado hacia logs desde scraper...")

        # --- mensaje para send_data ---
        send_data_msg = scraper_results
        send_data_msg["url"] = url

        # --- publicar mensaje hacia send_data ---
        scraper_channel.basic_publish(
            exchange="",
            routing_key=SEND_DATA_QUEUE,
            body=json.dumps(send_data_msg),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        print("Mensaje enviado hacia send_data desde scraper...")

    except Exception as e:
        print(f"Error al scrapear:\n {e}")
        finishing_time = dtime.now()
        # Envío desde scraping_results_send
        scraping_results_send(
            url,
            mensaje["medio"] if ("medio" in mensaje) else "",
            starting_time,
            "error",
            finishing_time,
            str(e),
        )
    
    # --- acknowledge ---
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    global scraper_channel

    # Conectar con RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))

    # Abrir un canal de conexión con RabbitMQ
    scraper_channel = connection.channel()

    # Definir las colas a escuchar
    for q in [SCRAPER_QUEUE, LOG_QUEUE, SEND_DATA_QUEUE]:
        scraper_channel.queue_declare(queue=q, durable=True)


    scraper_channel.basic_consume(
        queue=SCRAPER_QUEUE, on_message_callback=consume_article
    )
    scraper_channel.start_consuming()


if __name__ == "__main__":
    main()


#---- DEBUG ----#
def test():
    test_url = "https://www.latercera.com/politica/noticia/exministro-diego-pardow-enfrenta-acusacion-constitucional-en-el-senado/"
    noticia = scrap_news_article(test_url)
    if isinstance(noticia, dict):
        print(json.dumps(noticia, indent=3, ensure_ascii=False))


# Links testeados que causaron errores durante el desarrollo
# 1. https://www.latercera.com/mundo/noticia/carolin-emcke-el-discurso-del-odio-siempre-enmascara-su-propia-brutalidad/ 
# 2. https://www.latercera.com/sociales/noticia/clientes-de-finning-se-reunen-en-evento-exclusiv0-durante-electric-mine/
# 3. https://www.latercera.com/videos/noticia/desde-la-redaccion-24-de-noviembre-los-reparos-de-beatriz-sanchez-a-un-eventual-gobierno-de-jose-antonio-kast/
# 4. https://www.latercera.com/politica/noticia/exministro-diego-pardow-enfrenta-acusacion-constitucional-en-el-senado/
# 5. https://www.latercera.com/culto/noticia/gepe-mi-inseguridad-dejo-de-ser-destructiva-y-hoy-la-traduje-en-una-sensacion-de-vertigo/
# 6. https://www.latercera.com/el-deportivo/noticia/en-vivo-sevilla-de-alexis-sanchez-enfrenta-al-espanyol-para-meterse-en-puestos-de-clasificacion-a-copas-internacionales/