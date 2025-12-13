# logger

Este módulo implementa un sistema centralizado de logging usando RabbitMQ como bróker de mensajes y Redis como sistema de almacenamiento temporal de logs. De este modo, se desacoplan los procesos de scraping/crawling/scheduling del proceso responsable de registrar logs.

Adicionalmente, este módulo es responsable de consolidar y calcular las métricas finales de la ejecución (tasas de éxito, tiempos, noticias por fecha) una vez que el proceso concluye.

## Formato general de logs:
Cada entrada log registra un atributo "id_logging_process" como identificador de la tanda de logging. 
  * **Para los logs de `scraping_results`, `crawler_errors` y `scheduler_errors`:** este campo es adicional, es decir, es agregado como atributo por el logger después de recoger el mensaje json desde RabbitMQ y antes de anexarlo a la lista de entradas en Redis. El valor es generado al inicio del proceso logger y se mantiene constante hasta su finalización.
  
| Redis key          | Contenido                                |
| ------------------ | ---------------------------------------- |
| `crawler_errors`   | Logs de errores del crawler.             |
| `scheduler_errors` | Logs de errores del scheduler.           |
| `scraping_results` | Resultados individuales de scraping.     |
| `logging_control`  | Señales internas de control del proceso. |

#### logs `scraping_results` en Redis
Registran éxito/error por cada URL scrapeada.
```json
{
  "url": "...",
  "medio": "...",
  "starting_time": "YYYY-MM-DD HH:MM:SS",
  "status": "success" | "error",
  "finishing_time": "YYYY-MM-DD HH:MM:SS",
  "duration_ms": "123.45",
  "error": "" | "detalle del error si lo hubo",
  "fecha_publicacion": "Lunes 10 mayo de 2025",
  "id_logging_process": 1763159118
}
````

#### logs `crawler_errors` en Redis

Registra solo errores del crawler.

```json
{
  "from": "crawler",
  "arg_medio": "...",
  "error_timestamp": "YYYY-MM-DD HH:MM:SS",
  "stage": "etapa donde falló",
  "error_detail": "detalle del error",
  "id_logging_process": 1763159118
}
```

#### logs `scheduler_errors` en Redis

Registra solo errores del scheduler.

```json
{
  "from": "scheduler",
  "arg_medio": "...",
  "error_timestamp": "YYYY-MM-DD HH:MM:SS",
  "stage": "etapa donde falló",
  "error_detail": "detalle del error",
  "id_logging_process": 1763159118
}
```

#### logs `logging_control` en Redis

Registra `start_batch` que indica el inicio de la tanda, `end_batch_received` como señalizador para terminar la tanda y `end_batch_completed` cuando la tanda se concluye y se cierran los canales desde el logger.

```json
{
  "id_logging_process": 12345678,
  "action": "start_batch",
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```

-----

## Componentes .py

| Componente             | Rol                                                                           |
| ---------------------- | ----------------------------------------------------------------------------- |
| **logger/main.py** | Punto de entrada. Inicializa el servicio, maneja señales de sistema y dispara el motor de métricas al cerrar. |
| **logger/logger\_service.py** | Lógica principal del consumidor RabbitMQ. Escucha colas y escribe en Redis. |
| **logger/metrics\_engine.py** | Procesa los logs crudos de Redis y genera el archivo final `scraper_metrics.json`. |
| **logger/logs\_operations.py** | Operaciones de bajo nivel de escritura/lectura/limpieza en Redis.                                   |
| **logger/queue\_sender\_generic\_error.py** | Módulo emisor para logs de errores (usado por Crawler y Scheduler).          |
| **logger/queue\_sender\_logger\_ctrl.py** | Módulo emisor de control (usado por Scheduler). Incluye lógica de reconexión automática.         |
| **logger/queue\_sender\_scraper\_results.py** | Módulo emisor de resultados de scraping (usado por Scrapers).         |

## Flujo de funcionamiento

1.  El proceso logger se inicializa mediante `scheduler`, quien registra un log `start_batch` en `logging_control_queue`.
2.  Durante la ejecución, los componentes (crawler, scheduler, scrapers) envían mensajes JSON a RabbitMQ.
3.  El servicio `logger_service.py` consume 4 colas simultáneamente:
      * `crawler_log_queue`
      * `scheduler_log_queue`
      * `scraping_log_queue`
      * `logging_control_queue`
4.  Por cada mensaje, se asigna el `id_logging_process` y se guarda en **Redis** mediante `logs_operations.py`.
5.  Cuando se recibe la señal `end_batch_received`:
      * El logger espera a que las colas se vacíen completamente.
      * Detiene el consumo de mensajes.
      * Registra `end_batch_completed` (en lista key `logging_control` en Redis).
6.  **Generación de métricas:** Antes de finalizar el proceso (ya sea por flujo natural o por interrupción `SIGINT`), se invoca a `MetricsEngine`.
7.  **Cálculo y corrección:** `MetricsEngine` lee los logs de Redis, los compara con el archivo de progreso local (`scraper_progress.json`) para corregir posibles pérdidas de datos, normaliza fechas y escribe el reporte final en `metrics/scraper_metrics.json`.

## Dependencias

#### Python

  * `redis`
  * `pika`
  * `json`
  * `argparse`

#### Infraestructura

  * **Redis** (Persistencia temporal de logs para cálculo rápido)
  * **RabbitMQ** (Desacople asíncrono de mensajes)

-----

## Módulos de logging

#### Módulo `logger/main.py`

Lanzamiento del proceso: punto de entrada de la lógica.

  * Configura manejadores de señales (`signal.SIGTERM`, `signal.SIGINT`) para asegurar que, si el contenedor o proceso es detenido, se generen las métricas finales antes de morir (`Graceful Shutdown`).
  * Inicializa `LoggerService`.
  * Al terminar la ejecución de `LoggerService`, llama a `MetricsEngine`.

#### Módulo `logger_service.py`

Contiene la lógica de negocio del consumidor:

  * Mantiene la conexión RabbitMQ.
  * Mapea colas de RabbitMQ a listas de Redis (configuradas en `QueueKeyConfig`).
  * Gestiona el tiempo de espera (Idle Timeout) para auto-cerrarse si no hay actividad por 2 minutos tras recibir la señal de fin.

#### Módulo `metrics_engine.py`

Es el cerebro analítico del logger. Se ejecuta al final de la tanda.

  * **Lectura:** Obtiene todos los logs crudos desde la lista `scraping_results` en Redis.
  * **Agrupación:** Separa los logs por medio de prensa.
  * **Corrección de datos:** Lee el archivo `metrics/scraper_progress.json` (generado en tiempo real por los scrapers mediante File Locking). Si el archivo de progreso reporta más noticias procesadas que las encontradas en Redis (posible pérdida de mensajes asíncronos), el motor prioriza los datos del archivo de progreso para garantizar la precisión de los contadores totales.
  * **Normalización de fechas:** Parsea formatos de fecha heterogéneos (ISO 8601, texto en español como "Lunes 10...") para generar el histograma de `publicaciones_por_fecha`.
  * **Salida:** Escribe `metrics/scraper_metrics.json`.

#### Módulo `logs_operations.py`

Abstracción de Redis.

  * `anexar_log`: `LPUSH` de JSON.
  * `get_logs_list`: `LRANGE` para obtener todos los logs (usado por el motor de métricas).
  * `clear_logs_list`: `DEL` para limpieza inicial.

-----

## Módulos emisores

Estos módulos son importados por los otros servicios (Scheduler, Crawler, Scraper) para comunicarse con el Logger.

No tocan directamente a Redis y, por lo tanto, no interactúan con los logs. Usan RabbitMQ para evitar bloquearse entre ellos y para que el logger pueda escucharlos ordenadamente. Cada módulo declara su cola y publica mensajes JSON.

#### Módulo `queue_sender_generic_error.py`
Usado tanto por **crawler** como por **scheduler**. Estos componentes solo registran errores en su ejecución, de haberlos.

##### Colas declaradas/utilizadas:

* `"crawler_log_queue"` para los errores enviados por el crawler
* `"scheduler_log_queue"` para los errores enviados por el scheduler

##### Formato del mensaje:

```json
{
  "from": "crawler" | "scheduler",
  "arg_medio": "...",
  "error_timestamp": "YYYY-MM-DD HH:MM:SS",
  "stage": "etapa donde falló",
  "error_detail": "detalle del error"
}
```

#### Módulo `queue_sender_scraper_results.py`

Emisor de resultados del scraper.

##### Cola:

* `"scraping_log_queue"`

##### Formato:

```json
{
  "url": "...",
  "medio": "...",
  "starting_time": "YYYY-MM-DD HH:MM:SS",
  "status": "success" | "error",
  "finishing_time": "YYYY-MM-DD HH:MM:SS",
  "duration_ms": "123.45",
  "error": "" | "detalle del error si lo hubo"
}
```

#### Módulo `queue_sender_logger_ctrl.py`

Utilizado por el Scheduler para orquestar el inicio y fin.
**Mejora de resiliencia:** Implementa lógica de **reintento con reconexión**. Si al intentar enviar un mensaje de control la conexión con RabbitMQ falla (`AMQPConnectionError`, `StreamLostError`), la función `logging_batch_send`:

1.  Captura la excepción.
2.  Fuerza un reseteo de la conexión mediante `rabbit.reset_connection()`.
3.  Reintenta el envío una vez más.
    Esto evita que el Scheduler falle en operaciones críticas si la conexión RabbitMQ se ha cerrado por inactividad (heartbeat timeout).

##### Cola:

* `"logging_control_queue"`

##### Mensajes posibles:

###### Inicio de tanda:

```json
{
  "id_logging_process": 12345678,
  "action": "start_batch",
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```
El inicio de la tanda hace que el logger limpie las listas Redis de logs previos.

###### Señal de cierre:

```json
{
  "id_logging_process": 12345678,
  "action": "end_batch_received",
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```

Al recibir la señal de cierre, el logger:
* Espera que colas queden vacías
* Para de consumir
* Y registra un último mensaje en Redis

###### Mensaje generado por el logger al final:

```json
{
  "action": "end_batch_completed",
  "id_logging_process": 12345678,
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```
