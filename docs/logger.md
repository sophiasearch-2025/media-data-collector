# logger

Este módulo implementa un sistema centralizado de logging usando RabbitMQ como bróker de mensajes y Redis como sistema de almacenamiento temporal de logs. De este modo, se desacoplan los procesos de scraping/crawling/scheduling del proceso responsable de registrar logs.

---

# Componentes .py

| Componente             | Rol                                                                           |
| ---------------------- | ----------------------------------------------------------------------------- |
| **logger.py**          | Proceso principal que escucha mensajes desde RabbitMQ y los escribe en Redis. |
| **logs_operations.py** | Operaciones de escritura/limpieza en Redis.                                   |
| **queue_sender_generic_error.py**  | Módulo con funciones que envían logs de errores al proceso logger,  para los servicios crawler y scheduler.          |
| **queue_sender_logger_ctrl.py**  | Módulo utilizado por scheduler para controlar (iniciar y señalizar término) del proceso logger. Este control también es loggeado.         |
| **queue_sender_scraper_results.py**  | Módulo utilizado por el scraper para enviar al logger los logs de éxito/error de cada URL scrapeada.         |

---

# Flujo de funcionamiento

1. El proceso logger se inicializa con el scheduler, quien registra un log `start_batch` en `logging_control_queue` por medio de `queue_sender_logger_ctrl`.
2. Mientras se ejecuta el sistema, un componente (crawler o scheduler) captura un error propio, o bien, el scraper scrapea una URL específica con éxito/error.
3. Envía un mensaje al logger mediante alguno de:
  * `queue_sender_generic_error.py`
  * `queue_sender_scraper_results.py`
4. RabbitMQ encola estos mensajes en su cola correspondiente.
5. El proceso `logger.py` está consumiendo las colas:
  * `crawler_log_queue`
  * `scheduler_log_queue`
  * `scraping_log_queue`
  * `logging_control_queue`
6. Por cada mensaje:
  * Se asigna id_logging_process
  * Se guarda el log en Redis mediante `logs_operations.py`
7. Cuando se recibe la señal `end_batch_received` en `logging_control_queue`, el logger:
  * Espera que las colas queden vacías
  * Deja de consumir colas.
  * Registra `end_batch_completed` en la misma cola `logging_control_queue`.
  * Se cierra ordenadamente.
  
--- 
  
# Dependencias

### Python

* `redis`
* `pika`
* `json`
* `argparse`

### Módulos internos del repositorio

* `utils.rabbitmq_utils`
* `utils.redis_utils`

### Infraestructura

* **Redis** (para guardar logs)
* **RabbitMQ** (para comunicación asíncrona)

---

# Módulos de logging

Estos módulos del proceso involucran la manipulación de las entradas logs almacenadas temporalmente en Redis, en función de lo que se consume desde las colas de RabbitMQ.

---

## Módulo `logger.py`

Es el **proceso principal de logging**. Hace lo siguiente:
* Abre conexión a RabbitMQ.
* Declara y consume 4 colas:
  * `crawler_log_queue`
  * `scheduler_log_queue`
  * `scraping_log_queue`
  * `logging_control_queue`
* Para cada cola existe un callback que:
  * Parseará el JSON
  * Insertará en Redis mediante `logs_operations.anexar_log(...)`
  * Hará `basic_ack` (indica a RabbitMQ que el mensaje se consumió con éxito para que abandone la cola)
* Mantiene estado interno:
  ```python
  state = {"terminating": False}
  ```
* Cuando escucha `{"action": "end_batch_received"}`:
  * Marca `terminating = True`
  * Espera que las colas estén vacías
  * Llama a `stop_consuming()`
  * Inserta `end_batch_completed` en Redis a la lista logging_control
  * Cierra la conexión

---

## Módulo `logs_operations.py`

Módulo "abstraído" para realizar operaciones sobre las listas de logs en Redis.

### Funciones:

#### `anexar_log(log_data, list_name)`
* Realiza sobre Redis:
  ```
  LPUSH list_name json.dumps(log_data)
  ```
* Maneja errores de Redis.

#### `clear_logs_list(list_name)`
* Ejecuta `DEL list_name` para limpiar listas al iniciar un batch.

### Listas en Redis:
Donde las listas almacenadas en Redis son las siguientes:

| Lista Redis        | Contenido                                |
| ------------------ | ---------------------------------------- |
| `crawler_errors`   | Logs de errores del crawler.             |
| `scheduler_errors` | Logs de errores del scheduler.           |
| `scraping_results` | Resultados individuales de scraping.     |
| `logging_control`  | Señales internas de control del proceso. |

---

# Módulos emisores

No tocan directamente a Redis y, por lo tanto, no interactúan con los logs. Usan RabbitMQ para evitar bloquearse entre ellos y para que el logger pueda escucharlos ordenadamente. Cada módulo declara su cola y publica mensajes JSON.

---

## Módulo `queue_sender_generic_error.py`
Usado tanto por **crawler** como por **scheduler**. Estos componentes solo registran errores en su ejecución, de haberlos.

### Colas declaradas/utilizadas:

* `"crawler_log_queue"` para los errores enviados por el crawler
* `"scheduler_log_queue"` para los errores enviados por el scheduler

### Formato del mensaje:

```json
{
  "from": "crawler" | "scheduler",
  "arg_medio": "...",
  "error_timestamp": "YYYY-MM-DD HH:MM:SS",
  "stage": "etapa donde falló",
  "error_detail": "detalle del error"
}
```

---

## Módulo `queue_sender_scraper_results.py`

Emisor de resultados del scraper.

### Cola:

* `"scraping_log_queue"`

### Formato:

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

---

## Módulo `queue_sender_logger_ctrl.py`

Se usa para coordinar la vida del proceso `logger`.

### Cola:

* `"logging_control_queue"`

### Mensajes posibles:

#### Inicio de tanda:

```json
{
  "id_logging_process": 12345678,
  "action": "start_batch",
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```
El inicio de la tanda hace que el logger limpie las listas Redis de logs previos.

#### Señal de cierre:

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

#### Mensaje generado por el logger al final:

```json
{
  "action": "end_batch_completed",
  "id_logging_process": 12345678,
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```

---

# Ciclo de vida de una tanda o batch de logging

1. `start_batch`
  * Se limpian los logs previos en Redis.
2. Se ejecutan scheduler/crawler/scraper
  * Mandan logs a RabbitMQ.
3. El logger recibe y guarda todo en Redis.
4. Scheduler emite `end_batch_received` tras esperar el crawler
  * El logger espera a que llegue todo para dejar de consumir
5. Colas vacías
  * El logger deja de consumir y guarda `end_batch_completed` en Redis.
6. El logger se cierra.
