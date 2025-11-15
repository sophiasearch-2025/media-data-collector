# media-data-collector


## Propósito

Nuestros subsistema está centrado en la gestión de links (crawler) que serán usados para la recolección de las noticias (scraper) de la plataforma Sophia Search. Para el posterior analisis y estudio de la informacion recopilada.
_________________________________________________________________________

## Interacción con otros subsistemas

### user-interface:
La orden de ejecución de nuestro sistema vendrá por parte del subsistema de interfaz.

### data-storage-manager:
La información será enviada al subsistema de la base de datos para ser almacenada.
_________________________________________________________________________

## Documentacion interna
Enlaces a los documentos principales del subsistema:

- [Arquitectura](./arquitectura.md)
- [Decisiones técnicas](./decisiones.md)
- [Requisitos](./requisitos.md)
- [Despliegue](./deploy.md)
- [API](./api.md)
- [Crawler](./crawler_biobio.md)
- [Logger](./logger.md)
- [Scraper](./scraper_biobio.md)

_________________________________________________________________________

## Estado del subsistema

El subsistema actualmente se encuentra en su estado final, a espera de su integración con el resto de subsistemas para su despliegue.
El crawler y el scrapper se encuentran en un estado completo.
El logger almacena información y errores de manera correcta.
La API funciona correctamente, permitiendo el acceso a las metricas. 
Las métricas que servirán para medir el rendimiento del crawler y del scrapper se encuentran definidas y conectadas al resto del subsistema. Las métricas definidas son las siguientes:
- M1: Porcentaje de URLs procesadas correctamente y "cantidad sobre total" (noticias correctamente scrapeadas/total de enlaces crawleados) 
- M2: Noticias correctamente scrapeadas por minuto
- M3: Enlaces crawleados exitosamente por minuto 
- M4: Tiempo promedio por página scrapeada 
- M5: Promedio de URLs encontradas por cada categoría recorrida 
- M6: Número de enlaces de noticias indentificados por el crawler

_________________________________________________________________________

