## Dentro de las decisiones técnicas que se tomaron para el desarrollo del subsistema estas fueron las más importantes:

- ## Crawler:
1. Se escogió el medio [biobiochile](https://www.biobiochile.cl) por encima de otras páginas principalmente porque no tiene una subscripcion para tente acceso a sus noticias, además que la pagina sigue una estructura constante en la formulación de sus noticias.
2. Como se escogió la forma de crawlear la pagina se decidió por la accesibilidad que presentaba la pagina mediante la cual seguía un orden y categorización en los links de las noticias, facilitando así el acceso a la busqueda masiva de noticias. Como otra opción se había propuesto buscar por niveles desde la pagina principal, esto podría considerarse como opción para otras páginas.

___________________________________________
- ## Scrapper:
1. Se decidió modularizar el codigo para que sea más sencillo debugear el scrapeo de las noticias si presenta problemas buscando algun componente de la noticia.
´´´
extract, extract_text_only, extract_multimedia y extract_body
´´´

___________________________________________
- ## Logs (data y errores):
1. Se decidió usar redis para el almacenamiento de la información y los errores, ya que no es necesario que los logs sean almacenados permanentemente.
2. Se dicidió modularizar los metodos de conexión que usa el componente logger.

___________________________________________
- ## Métricas:
1. Se tomó la decisión de que para acceder a la información de las métricas se usara una API, en este caso se optó por usar FastAPI por comodidad.
2. Almacenar las métricas en archivos json, ya que es un formato fácil de entender para humanos y software.
3. Dividir las métricas en dos archivos (crawler_metrics y scraper_metrics) para modularizar el código.
4. Que cada vez que se ejecute el crawler y scraper, se sobreescriban las métricas anteriores, ya que si se quisiera llevar registro, eso debe ir en la base de datos.

___________________________________________
- ## Documentación:
1. Se consideró que al tener que ejecutar más de un archivo que se tendrá que ejecutar y desplegar, que cada uno tenga su propia documentación con información específica de cada archivo explicando a detalle dudas que puedan existir sobre el despliegue de dichos archivos. De igual forma fueron adjuntados toda la documentación en [README.md](./docs/README.md)