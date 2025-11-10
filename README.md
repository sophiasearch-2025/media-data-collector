# media-data-collector


## Propósito

Nuestros subsistema hace la gestión de los links (crawler) y la recolección de la información (scrapper) que contienen es un recolector de datos, centrado en las noticias para su posterior analisis y estudio.
_________________________________________________________________________

## Interacción con otros subsistemas

La orden de ejecución de nuestro sistema vendrá por parte del subsistema de interfaz.
La información será enviada al subsistema de la base de datos.
_________________________________________________________________________

## Documentacion interna
Enlaces a los documentos principales del subsistema:

- [Arquitectura](./arquitectura.md)
- [Decisiones técnicas](./decisiones.md)
- [Requisitos](./requisitos.md)
- [Despliegue](./deploy.md)
- [Diagramas](./diagramas.md)

_________________________________________________________________________

## Estado del subsistema

El subsistema actualmente se encuentra en desarrollo.
El crawler (version inicial) y el scrapper ya se encuentra en un estado es funcional.
Las métricas que servirán para medir el rendimiento del crawler y del scrapper se encuentran definidas y listas para conectarse al resto del desarrollo. Las métricas definidas son las siguientes:
- M1: Porcentaje de URLs procesadas correctamente y "cantidad sobre total" (noticias correctamente scrapeadas/total de enlaces crawleados) 
- M2: Noticias correctamente scrapeadas por minuto
- M3: Enlaces crawleados exitosamente por minuto 
- M4: Tiempo promedio por página scrapeada 
- M5: Promedio de URLs encontradas por cada categoría recorrida 
- M6: Número de enlaces de noticias indentificados por el crawler

_________________________________________________________________________

