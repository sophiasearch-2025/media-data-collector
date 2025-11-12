import pika, json
from datetime import datetime as dtime

PLANNER_QUEUE = "planner_queue"
SCRAPER_QUEUE = "scraper_queue"
ERROR_QUEUE   = "error_queue"

# --- bloque para la conexion global de RabbitMQ ---
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
planner_channel = connection.channel()

# --- declaración de colas ---
for q in [PLANNER_QUEUE, SCRAPER_QUEUE, ERROR_QUEUE]:
    planner_channel.queue_declare(queue=q, durable=True)
''' IMPORTANTE: "durable=True" hace que las colas se guarden en disco, osea,
                las colas vuelven estar disponibles automaticamente luego
                de un reinicio. '''

def callback(ch, method, properties, body):
    starting_time = dtime.now().timestamp()
    message = {
        "url"
        "tags"
        "metricas"
    }
    try:
        message = json.loads(body)

        # --- si no existe algún comando, mandamos error ---
        if "cmd" not in message:
            error_msg = {}
            planner_channel.basic_publish(
                exchange='',
                routing_key=ERROR_QUEUE,
                body=json.dumps(error_msg), # --- mensaje en formato JSON ---
                properties=pika.BasicProperties(
                    delivery_mode=2
                )
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        query = message["cmd"]
        # --- distintos comandos ---
        if query=="scrape!":
            try:
                # --- creamos el mensaje -- 
                scraper_msg = {
                    "url": message["url"],
                    "tag": message["tag"]
                }
                # --- publicación del mensaje ---
                planner_channel.basic_publish(
                    exchange='',
                    routing_key=SCRAPER_QUEUE,
                    body=json.dumps(scraper_msg), # mensaje en formato JSON
                    properties=pika.BasicProperties(
                        delivery_mode=2
                    )
                )
                ''' "delivery_mode=2" hace que el mensaje se guarde en
                    disco, osea, los mensajes también se guarden en disco. '''
            except Exception as e:
                print("NOTIFICAR QUE EL SCRAPPER FALLO A LA COLA DE ERRORES")

        # --- se borra el mensaje de la cola ---
        ch.basic_ack(delivery_tag=method.delivery_tag)

    # --- el planner falló, notificar a la cola de errores ---
    except Exception as e:
        finishing_time = dtime.now().timestamp()
        error_msg = {
            "url": message["url"],
            "medio": message["medio"],
            "starting_time": starting_time,
            "finishing_time": finishing_time,
            "duration_ms": int((finishing_time-starting_time)*1000),
            "status": "FAILED",
            "error": str(e)
        }
        planner_channel.basic_publish(
            exchange='',
            routing_key=ERROR_QUEUE,
            body=json.dumps(error_msg), # --- mensaje en formato JSON ---
            properties=pika.BasicProperties(
                delivery_mode=2
            )
        )

# --- el planner consume los mensajes de su cola ---
planner_channel.basic_qos(prefetch_count=1)
planner_channel.basic_consume(queue=PLANNER_QUEUE, on_message_callback=callback)
planner_channel.start_consuming()

#''' (verificar quien me da esta data, y que data me entregará)
#Se asume que el planner recibe un json con el siguiente formato:
#    {
#        "cmd": comando a ejecutar
#        "medio": el medio de la pág. a screapear
#        "url": url de la pág. a scrapear
#        "tag": tag de la noticia a screapear (cmd = "scrape!")
#    }
#'''

''' --- ACLARADO ---
El formato json que recibe el sistema de logs y errores (desde scraper al parecer):
    {
        "url": url,
        "medio": medio,
        "starting_time": starting_time, -> (timestamp 'YYYY-MM-DD HH:MM:SS' ?)
        "finishing_time": finishing_time, -> (timestamp 'YYYY-MM-DD HH:MM:SS' ?)
        "duration_ms": duration, -> la diferencia en ms
        "status": status, -> FAILED -o- SUCCESSED
        "error": error, -> devovler el mensaje de error en caso de tenerlo
    }
'''

''' HAY QUE DIFERENCIAR EL ERROR DEL PLANIFER Y DEL SCRAPPER '''

''' ACLARACIONES CON PROFE
"es mejor que..."
1. El Scheduler crea un worker o workers del tipo Crawler (1 por medio).
2. Estos crawler, pueden mandar mensajes a scrappers para analizar los links enviados
    por estos.
3. Evitar el conector de redes sociales de momento
4. El planner es llamado, no a travéz de mensajes. Se ejecuta de momento con valores
    definidos de prueba, estos valores puede ser solamente el medio:
        {
            "medio": str
        } (el crawler debe poder ser capaz de identificar el medio y crawlearlo,
            para luego mandar los mensaje a scrapper para el scrap de cada uno)
5. La idea es que el Scheduler genere workers cada que este es llamado, 
    que controle todo.
6. El sistema de rabbit no es necesario que esté completo, almenos para esta entrega.
7. Las colas y mensajes se pueden mantener en disco, pero hay que tomar una desición.
8. Con crear se refiere a: el Scheduler crea procesos de crawler, y un crawler crea
    procesos de scrapper (o procesos diferentes, que simplemente queden 
    escuchando sus respectivas colas)
9. Scheduler NO notifica a "envio de datos", solamente a log de errores, y si
    algún scrap funciona bien, se notifica a travéz de un mensaje desde el scrapper 
    directamente.
'''