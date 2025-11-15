## Requisitos funcionales

1. Requisito 1:
El subsistema recopila noticias de un medio de prensa.
2. Requisito 2:
Un script (crawler) recopila los links de las noticias que serán recopiladas.
3. Requisito 3:
Las noticias recopiladas serán almacenadas en una base de datos relacional.
4. Requisito 4:
Los errores existentes e información varia será almacenada en un sistema de logs durante la recopilación.
5. Requisito 5:
Las métricas serán almacenadas en archivos .json.
6. Requisito 6:
No se puede iniciar otra recopilación mientras exista una en curso.
7. Requisito 7:
Se puede detener la recopilación.


## Requisitos no funcionales

1. Requisito 1:
La plataforma dará feedback al usuario con métricas para ver el avance de la recopilación.
2. Requisito 2:
La plataforma cumple con no tener errores guíandose por la estructura ordenada de la pagina de biobiochile.
3. Requisito 3:
El scraper y el crawler son escalables a medios de noticias que se adapten a la estructura del medio biobiochile.