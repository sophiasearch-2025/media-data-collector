# Sistema de mensajes mediante RabbitMQ.

Este sistema se encarga de comunicar los distintos módulos del subsistema de recoleción de datos haciendo uso de colas y mensajes persistentes.

El flujo del sistema se compone de cinco módulos principales ```Scheduler, Crawler, Scraper, Logger y Sender``` que se comunican exclusivamente mediante colas de mensajes, permitiendo un procesamiento concurrente y confiable.

El sistema está diseñado para tener colas y mensajes persistentes, así en casos de caídas del servidor o algún reinicio planificado, las colas y mensajes sigan estándo presentes y esta información no se pierda.

## Flujo del programa.

RabbitMQ se utiliza como intermediario para orquestar el flujo de datos, inicialmente cuando se llama a ```Scheduler``` lanza todos los módulos de forma concurrente, así, todos excepto ```Crawler``` quedán a la espera de mensajes en sus respectivas colas y se sigue el siguiente flujo:

- El ```Crawler``` produce mensajes hacia ```scraper_queue``` cuando un link es recopilado, y hacia ```crawler_log_queue``` cuando algo falla

- Los ```Scrapers``` consumen estos enlaces del crawler, extraen la información de la noticia dada y publican el contenido final en ```send_queue```, si la recopilación falla o tiene éxito se comunica a ```scraping_log_queue```.

- Si algo falla inicialmente desde el ```Scheduler```, este manda un mensaje de error directamente a ```scheduler_log_queue```.

- Los ```Loggers``` están atentos a recibir mensajes de "sucess" o "error" por parte de todos los módulos.

- Los ```Sender``` de momento solo imprimen cada mensaje que reciben en su respectiva cola, se plantea organizar con el grupo de base de datos recibir estos datos de la cola.

## Formato de mensajes entre colas.

Los mensajes que se pasan entre módulos mediante las colas son mediante el formato JSON, y estos formatos son los siguientes:

### Crawler

- ```Crawler``` hacia ```Scraper```
```
{
    "url": <Url>
    "tags": <Lista de tags>
}
```

- ```Crawler``` hacia ```Logger```
```
{
    "from": "crawler"
    "arg_medio": Correspondiente al argumento 'medio' crawleado
    "error_timestamp": ("%Y-%m-%d %H:%M:%S")
    "stage": Etapa que falló
    "error_detail": El error que recibe
}
```

### Scraper

- ```Scraper``` hacia ```Sender```
```
{
    "titulo": titulo,
    "fecha": fecha,
    "autor": autor,
    "desc_autor": desc_autor,
    "abstract": abstract,
    "cuerpo": cuerpo,
    "multimedia": multimedia,
    "tipo_multimedia": "imagen",
    "url": url
}
```

- ```Scraper``` hacia ```Logger```
```
{
    "url": url,
    "medio": medio,
    "starting_time": starting_time,
    "finishing_time": finishing_time,
    "duration_ms": duration,
    "status": status,
    "error": error
}
```

### Scheduler

- ```Scheduler``` hacia ```Logger```
```
{
    "from": "scheduler"
    "arg_medio": arg_medio, correspondiente al argumento 'medio' suministrado
    "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    "stage": etapa que falló,
    "error_detail": error_detail,
}
```

## Como ejecutar el sistema

Desde la raíz del repositorio ```media-data-collector```, se debe ejecutar:

```
python -m RabbitMQ.scheduler <medio> <n_scrapers>
```

### Donde:
- ```medio```: El nombre del medio a analizar.
- ```n_scrapers```: Cantidad de scrapers trabajando concurrentemente para analizar todos los links del medio entregados por el crawler.

## Algunas desiciones técnicas tomadas.

### Desición 1.

Las colas y mensajes que son declarados para este sistema se guardarán en disco, así en casos de que se caiga el servidor o un reinicio, estos no se pierdan y cuando vuelva a estar activo el servicio se puedan volver a consumir.


### Desición 2.

Uso de JSON como formato stándar entre procesos ya que en python es simple trabajar con el formato JSON.

Todos los mensajes se serializan con ```.dumb()``` y se envían como ```str```.

### Desición 3.

Se decidió separar los logs en colas independientes para permitir trazabilidad por etapa y evitar mezclar logs de distintos procesos. Se usan ```crawler_log_queue```,  ```scraping_log_queue``` y ```scheduler_log_queue```.

### Desición 4.

Desde scheduler se lanzan distintos procesos, el de crawler, scraping, logging y envío de datos. Estos procesos se lanzan de forma independiente, para no bloquear otros procesos y puedan trabajar concurrentemente.

### Desición 5.

Se optó por colas independientes en véz de una cola global, así se tiene un control más fino de hacia donde está viajando la información, además de que permitirá una mejor escalabilidad a futuro.