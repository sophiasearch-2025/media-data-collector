''' --- ACLARADO ---
El formato json que recibe el sistema de logs y errores (desde scraper al parecer):
    {
        "url": url,
        "medio": medio,
        "starting_time": starting_time, -> (timestamp 'YYYY-MM-DD HH:MM:SS' ?)
        "finishing_time": finishing_time, -> (timestamp 'YYYY-MM-DD HH:MM:SS' ?)
        "duration_ms": duration, -> la diferencia en ms
        "status": status, -> ERROR -o- SUCCESSED
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

'''
Secuencia:

Scheduler se inicia manualmente con un medio el cual es recibido por argumento, este scheduler
invoca distintos modulos del "diagrama de modulos", un crawler, un send_datos, un scrapper, y un
logger_errores, estos excepto el crawler, están a la espera de mensajes en sus respectivas colas, mientras
el crawler es el encargado de ir señalando al scrapper que debe scrapear.

El crawler cuando es invocado con un medio, crawlea este en particular y envia mensajes a la cola 
del scrapper para que este lo pueda procesar. Una vez terminado todos los scrapeos, el crawler
guarda métricas en crawler_metrics.json

El Scrapper escucha constantemente mensajes en su cola, los cuales deben contener:
{
    "url": url_bonita :D
    "tags": tags_exóticas :D
}
con esta información desde la cola, la recibe y screapea esta pagina, cuando hay un error lo manda a log,
pero si lo hace bien, lo manda a log y además tambien manda un mensaje a send_queue con la data del screpeo.

El send_data solo imprime lo que le llega.

'''