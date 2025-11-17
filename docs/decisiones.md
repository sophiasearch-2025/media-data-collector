# Decisiones técnicas

- ## Crawler:
1. Se escogió el medio [biobiochile](https://www.biobiochile.cl) por encima de otras páginas principalmente porque no tiene una subscripcion para tente acceso a sus noticias, además que la pagina sigue una estructura constante en la formulación de sus noticias.

2. Como se escogió la forma de crawlear la pagina se decidió por la accesibilidad que presentaba la pagina mediante la cual seguía un orden y categorización en los links de las noticias, facilitando así el acceso a la busqueda masiva de noticias. Como otra opción se había propuesto buscar por niveles desde la pagina principal, esto podría considerarse como opción para otras páginas.

___________________________________________
- ## Scraper:
1. Se decidió modularizar el codigo para que sea más sencillo debugear el scrapeo de las noticias si presenta problemas buscando algun componente de la noticia.
´´´
extract, extract_text_only, extract_multimedia y extract_body
´´´

2. Se diseñó el scheduler para recibir parámetros dinámicos, permitiendo ejecutar el sistema. En particular, el scheduler debe recibir ```<medio>``` y ```<cantidad de scrapers>``` respectivamente.

3. El crawler se llamará desde el scheduler, y se llama con un parámetro el cual es el medio a crawlear. Por cada noticia que encuentra manda el link y sus tags hacia el scraper mediante la cola ```scraper_queue``` con el siguiente formato:
```
{
    "url": <url> -> (str)
    "tags": [<tags>] -> (list<str>)    
}
```
4. El scraper consumirá los mensajes de la cola ```scraper_queue```, y por cada mensaje consumido enviará un mensaje a la cola ```scraping_log_queue```, adicionalmente si el mensaje es consumido con éxito se enviará un mensaje a la cola ```send_queue```, la cual es donde termina el flujo de mensajes.

5. Las colas y mensajes que son declarados para este sistema se guardarán en disco, así en casos de que se caiga el servidor o un reinicio, estos no se pierdan y cuando vuelva a estar activo el servicio se puedan volver a consumir.

6. Se decidió que momentaneamente, el formato de los datos finales del scraping se enviaran al módulo <envío de datos> de la siguiente forma:

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

7. Uso de JSON como formato stándar entre procesos ya que en python es simple trabajar con el formato JSON.

Todos los mensajes se serializan con ```.dumb()``` y se envían como ```str```.

8. Se decidió separar los logs en colas independientes para permitir trazabilidad por etapa y evitar mezclar logs de distintos procesos. Se usan ```crawler_log_queue```,  ```scraping_log_queue``` y ```scheduler_log_queue```.

9. Desde scheduler se lanzan distintos procesos, el de crawler, scraping, logging y envío de datos. Estos procesos se lanzan de forma independiente, para no bloquear otros procesos y puedan trabajar concurrentemente.

10. Se optó por colas independientes en véz de una cola global, así se tiene un control más fino de hacia donde está viajando la información, además de que permitirá una mejor escalabilidad a futuro.

11. Los formatos JSON para las distintas colas que consume el logger son:

- ### Scheduler
```
{
    "from": "scheduler"
    "arg_medio": arg_medio, correspondiente al argumento 'medio' suministrado
    "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    "stage": etapa que falló,
    "error_detail": error_detail,
}
```
- ### Crawler
```
{
    "from": "crawler"
    "arg_medio": arg_medio, correspondiente al argumento 'medio' suministrado
    "error_timestamp": error_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    "stage": etapa que falló,
    "error_detail": error_detail,
}
```
- ### Scraper
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


___________________________________________
- ## Logs (data y errores):
1. Se decidió usar redis para el almacenamiento de la información y los errores, ya que no es necesario que los logs sean almacenados permanentemente.

2. Se dicidió modularizar los metodos de conexión que usa el componente logger.

___________________________________________
- ## Métricas:
1. Se tomó la decisión de que para acceder a la información de las métricas se usará una API, en este caso se optó por usar FastAPI por comodidad.

2. Almacenar las métricas en archivos json, ya que es un formato fácil de entender para humanos y software.

3. Dividir las métricas en dos archivos (crawler_metrics y scraper_metrics) para modularizar el código.

4. Que cada vez que se ejecute el crawler y scraper, se sobreescriban las métricas anteriores, ya que si se quisiera llevar registro, eso debe ir en la base de datos.

___________________________________________
- ## Documentación:
1. Se consideró que al tener que ejecutar más de un archivo que se tendrá que ejecutar y desplegar, que cada uno tenga su propia documentación con información específica de cada archivo explicando a detalle dudas que puedan existir sobre el despliegue de dichos archivos. De igual forma fueron adjuntados toda la documentación en [README.md](./README.md)