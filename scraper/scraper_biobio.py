import json
import os
import sys
from datetime import datetime as dtime
from scraper.scraping_utils import (
    extract, 
    extract_body, 
    extract_images, 
    extract_text_only
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

        fecha = extract(
            soup,
            [
                "div.post-date",
                "div.autor-fecha-container p.fecha",
                "div.nota p.fecha",
                "div.nota-top-content div.top-content-text p.fecha",
            ],
        ) or extract_text_only(
            soup,
            [
                "div.fecha-visitas p.fecha",
            ],
        )
        if validate and not fecha:
            invalid_args.append("fecha")

        titulo = extract(
            soup,
            [
                "h1.post-title",
                "h1.titulo",
                "div.nota-top-content div.top-content-text h1.titular",
            ],
        )
        if validate and not titulo:
            invalid_args.append("titulo")

        autor = extract(
            soup,
            [
                "div.autores-trust-project div.contenedor-datos p.nombres a",
                "div.author div.creditos-nota div.autores span.autor b",
                "div.autor-opinion div.informacion a.nombre",
                "div.autor div.creditos-nota div.autores span.autor b a",
                "div.container-nota-body span.autor b a",
            ],
        )

        desc_autor = extract(
            soup,
            [
                "div.autores-trust-project div.contenedor-datos p.cargo",
                "div.autor-opinion div.informacion p.cargo",
            ],
        )

        abstract = extract(
            soup,
            [
                "div.post-main div.post-content div.post-excerpt p",
                "div.contenido-nota div.post-excerpt p",
            ],
        )

        cuerpo = extract_body(
            soup,
            [
                "div.post-main div.post-content div.container-redes-contenido p, div.post-main div.post-content div.container-redes-contenido h2",
                "div.container-redes-contenido div.contenido-nota h2, div.container-redes-contenido div.contenido-nota p",
                "div.contenido-nota div[class^='banners-contenido-nota-'] h2, div.contenido-nota div[class^='banners-contenido-nota-'] p",
                "div.container-nota-body div.nota-content div.contenido p, div.container-nota-body div.nota-content div.contenido h2",
            ],
        )
        if validate and not cuerpo:
            invalid_args.append("cuerpo")

        multimedia = extract_images(
            soup,
            [
                "div.post-main div.post-image img",
                "div.post-main div.post-content div.container-redes-contenido img",
                "div.imagen",
                "div.contenedor-imagen-titulo div.imagen img",
                "div.nota-top-content img",
            ],
        )

        if validate and len(invalid_args) >= 1:
            return invalid_args

        return {
            "titulo": titulo,
            "fecha": fecha,
            "autor": autor,
            "desc_autor": desc_autor,
            "abstract": abstract,
            "cuerpo": cuerpo,
            "multimedia": multimedia,
            "tipo_multimedia": "imagen",
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
        scraper_results = scrap_news_article(url, validate=True)

        # Si devuelve una lista, detengo el proceso con un error
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


# =====================================================
#                        Testing
# =====================================================


def test():
    test_url = "https://www.biobiochile.cl/noticias/servicios/beneficios/2025/10/23/asi-funciona-el-beneficio-estrudiantil-que-cubre-mas-de-un-millon-de-pesos-del-arancel.shtml"
    noticia = scrap_news_article(test_url)
    if isinstance(noticia, dict):
        print(json.dumps(noticia, indent=3, ensure_ascii=False))


# Links testeados que causaron errores durante el desarrollo
# 1. "https://www.biobiochile.cl/noticias/nacional/chile/2025/10/12/franco-parisi-creo-que-paso-a-segunda-vuelta-con-jara-no-hay-tanto-voto-de-ultraderecha-en-chile.shtml"
# 2. "https://www.biobiochile.cl/noticias/ciencia-y-tecnologia/adelantos/2025/10/10/de-madera-tierra-y-techos-verdes-presentan-mat-la-primera-casa-chilena-sustentable-y-transportable.shtml"
# 3. "https://www.biobiochile.cl/noticias/artes-y-cultura/actualidad-cultural/2025/09/25/11-dias-de-actividades-trae-bienal-de-arquitectura-y-programa-enfocado-en-revitalizacion-de-la-ciudad.shtml"
# 4. "https://www.biobiochile.cl/noticias/servicios/explicado/2024/11/13/los-hombres-lo-desean-mas-que-las-mujeres-5-mitos-sobre-el-sexo-explicado-por-expertos.shtml"
# 5. "https://www.biobiochile.cl/noticias/servicios/toma-nota/2025/03/16/viajar-y-comer-por-chile-los-menus-imperdibles-a-lo-largo-del-pais-segun-nueva-guia-gastronomica.shtml"
# 6. "https://www.biobiochile.cl/noticias/dopamina/2025/10/30/una-humillacion-critican-eliminacion-de-nidyan-fabregat-de-fdb-y-apuntan-contra-vasco-moulian.shtml"
# 7. "https://www.biobiochile.cl/especial/bio-bio-tuercas/noticias/2025/10/31/massa-califica-el-crashgate-como-el-mayor-escandalo-en-la-historia-del-deporte-reclama-titulo-de-f1.shtml"
# 8. "https://www.biobiochile.cl/especial/bbcl-investiga/noticias/entrevistas/2025/11/01/falta-una-izquierda-mas-de-resultados-que-de-eslogan-carlos-cuadrado-ppd-candidato-a-diputado.shtml"
# 9. "https://www.biobiochile.cl/especial/bbcl-investiga/noticias/de-pasillo/2025/10/30/embargan-bienes-de-alvaro-saieh-por-deuda-de-27-millones-de-dolares-con-banco-itau.shtml"
# 10. "https://www.biobiochile.cl/noticias/servicios/beneficios/2025/10/23/asi-funciona-el-beneficio-estrudiantil-que-cubre-mas-de-un-millon-de-pesos-del-arancel.shtml"
