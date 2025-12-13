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
- [Crawler](./crawler_biobio.md)
- [Scraper](./scraper_biobio.md)
- [RabbitMQ](../RabbitMQ/rabbit_mq.md)
- [Logger](./logger.md)
- [Scheduler](./scheduler.md)
- [API](../api_metricas/api.md)

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

## Distribución de las carpetas
```
├── .env                                    #Variables de entorno locales
├── .gitignore                              #Exclusiones de control de versiones
├── docker-compose.yml                      #Orquestación de servicios (RabbitMQ, API, etc.)
├── rabbitmq.conf                           #Configuración del broker RabbitMQ
├── requirements.txt                        #Dependencias del proyecto (pip)
├── test_scraper.py                         #Prueba rápida del scraper usando el CSV
│
├── api_metricas/                           #API (FastAPI) para exponer métricas
│   ├── api.md                              #Documentación de la API
│   ├── main.py                             #Punto de entrada de la API FastAPI
│   ├── __init__.py                         #Indicador de paquete Python
│   └── routers/
│       └── metrics_router.py               #Endpoints para consultar métricas
│
├── Crawler/                                #Crawling: recolección inicial de URLs
│   ├── biobiochile.csv                     #Listado de URLs descubiertas
│   ├── crawler.py                          #Lógica base reutilizable del crawler
│   ├── crawler_biobio.py                   #Crawler específico para BioBioChile
│   └── crawler_sender.py                   #Envío de resultados del crawler a RabbitMQ
│
├── docs/                                   #Documentación técnica del subsistema
│   ├── arquitectura.md                     #Vista general de componentes
│   ├── crawler_biobio.md                   #Detalles del crawler BioBioChile
│   ├── decisiones.md                       #Decisiones técnicas justificadas
│   ├── deploy.md                           #Guía de despliegue
│   ├── logger.md                           #Uso del sistema de logging
│   ├── rabbit_mq.md                        #Guía de mensajería con RabbitMQ
│   ├── requisitos.md                       #Requisitos funcionales y no funcionales
│   ├── scraper_biobio.md                   #Detalles del scraper BioBioChile
│   ├── README.md                           #Índice y guía de esta documentación
│   └── diagramas/                          #Diagramas de arquitectura y procesos
│       ├── casos_de_usos.png               #Diagrama de casos de uso
│       ├── diagrama_componentes.png        #Diagrama de componentes
│       ├── vista_fisica.png                #Vista física (infraestructura)
│       └── vista_procesos.png              #Vista de procesos
│
├── logger/                                 #Módulos de logging y publicación en colas
│   ├── logger.py                           #Configuración central de logging
│   ├── logs_operations.py                  #Operaciones/utilidades sobre logs
│   ├── queue_sender_generic_error.py       #Publica errores genéricos en RabbitMQ
│   ├── queue_sender_logger_ctrl.py         #Eventos de control del logger a RabbitMQ
│   └── queue_sender_scraper_results.py     #Publica resultados del scraper
│
├── metrics/                                #Métricas generadas en tiempo de ejecución
│   ├── crawler_metrics.json                #Métricas del proceso de crawling
│   └── scraper_metrics.json                #Métricas del proceso de scraping
│
├── RabbitMQ/                               #Utilidades de mensajería y scheduling
│   ├── pseudo_crawler.py                   #Generador de eventos/pruebas de flujo
│   ├── scheduler.py                        #Programación de tareas del sistema
│   └── send_data.py                        #Envío de datos a colas RabbitMQ
│
├── scraper/                                #Scraper de artículos/noticias
│   ├── scraper_biobio.py                   #Extracción de contenido desde URLs BioBio
│   └── data/
│       └── output.json                     #Salida de ejemplo del scraping (JSON)
│
└── utils/                                  #Utilidades y helpers compartidos
	├── environ_var.py                      #Carga/gestión de variables de entorno
	├── rabbitmq_utils.py                   #Helpers para conexión/colas de RabbitMQ
	├── redis_utils.py                      #Helpers para Redis
	└── __init__.py                         #Indicador de paquete Python
```
