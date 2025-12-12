# README — API de Métricas Sophia

## 1. Descripción general

La API de Métricas Sophia es un servicio desarrollado con FastAPI que expone las métricas generadas por los módulos Crawler y Scraper del proyecto Sophia Search.

Los datos se almacenan en archivos JSON dentro de la carpeta:

metrics/
    crawler_metrics.json
    scraper_metrics.json

La API entrega estos datos para que la Interfaz de Administrador pueda visualizarlos y analizarlos.

La API expone los siguientes endpoints:

**Métricas:**
- GET /api/metrics/

**Control del Scheduler:**
- POST /scheduler/start
- POST /scheduler/stop
- GET /scheduler/status

---

## 2. Estructura del proyecto

media-data-collector/
│
├── api_metricas/
│   ├── main.py
│   └── routers/
│       └── metrics_router.py
│
├── metrics/
│   ├── crawler_metrics.json
│   ├── scraper_metrics.json
│   └── crawler_progress.json
│
├── Crawler/
├── scraper/
├── utils/
├── logger/
├── docs/
├── requirements.txt
└── docker-compose.yml

---

## 3. Ejecución local de la API

### 3.1. Crear entorno virtual

python3 -m venv venv
source venv/bin/activate

### 3.2. Instalar dependencias

pip install -r requirements.txt

### 3.3. Ejecutar FastAPI

uvicorn api_metricas.main:app --reload

Accesos:

- Documentación Swagger: http://127.0.0.1:8000/docs
- Métricas: http://127.0.0.1:8000/api/metrics/

---

## 4. Despliegue en el servidor del proyecto

### 4.1. Acceder al servidor

ssh root@172.105.21.15

### 4.2. Clonar repositorio

git clone https://github.com/sophiasearch-2025/media-data-collector.git
cd media-data-collector

### 4.3. Instalar dependencias

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### 4.4. Ejecutar API de producción

./venv/bin/uvicorn api_metricas.main:app --host 0.0.0.0 --port 8080

Acceso público:

- Documentación: http://172.105.21.15:8080/docs
- Métricas: http://172.105.21.15:8080/api/metrics/

---

## 5. Endpoints disponibles

### 5.1. GET /api/metrics/

Obtiene las métricas en tiempo real del crawler y scrapers.

**Respuesta ejemplo:**

```json
{
  "crawler_progress": {
    "sitio": "biobiochile",
    "status": "completed",
    "total_categorias": 78,
    "categorias_procesadas": 78,
    "porcentaje": 100,
    "urls_encontradas": 450
  },
  "scraper_progress": {
    "biobiochile": {
      "total_articulos_exitosos": 450,
      "total_articulos_fallidos": 0,
      "duracion_promedio_ms": 1234.56,
      "articulos_por_minuto": 65.2,
      "ultima_actualizacion": "2025-12-12 15:30:45",
      "start_time": "2025-12-12 15:25:00"
    }
  },
  "scraper_metrics": {
    "biobiochile": {
      "total_logs": 450,
      "articulos_exitosos": 450,
      "articulos_fallidos": 0,
      "fecha_inicio": "Jueves 12 diciembre de 2025",
      "fecha_termino": "Jueves 12 diciembre de 2025"
    }
  }
}
```

### 5.2. POST /scheduler/start

Inicia el proceso completo de scraping (crawler + scrapers + logger) para un medio específico.

**Request body:**

```json
{
  "medio": "biobiochile",
  "num_scrapers": 4
}
```

**Parámetros:**
- `medio` (string, requerido): `"biobiochile"` o `"latercera"`
- `num_scrapers` (int, opcional): Número de scrapers paralelos (default: 1, recomendado: 4)

**Respuesta exitosa (200):**

```json
{
  "status": "started",
  "medio": "biobiochile",
  "pid": 12345,
  "num_scrapers": 4
}
```

**Errores:**
- 400: Si ya hay un crawler corriendo
- 500: Error al iniciar el proceso

### 5.3. POST /scheduler/stop

Detiene el scheduler y todos sus procesos hijos (crawler, scrapers, logger).
Envía SIGTERM para cierre graceful y limpia las colas de RabbitMQ.

**Request body:** Ninguno

**Respuesta exitosa (200):**

```json
{
  "status": "stopped",
  "queues_purged": true
}
```

**Errores:**
- 400: Si no hay crawler corriendo
- 500: Error al detener el proceso

### 5.4. GET /scheduler/status

Obtiene el estado actual del scheduler.

**Respuesta exitosa (200):**

```json
{
  "status": "running",
  "pid": 12345
}
```

**Posibles estados:**
- `"not_started"`: No se ha iniciado ningún scheduler
- `"running"`: Scheduler actualmente ejecutándose
- `"stopped"`: Scheduler detenido (incluye exit_code)

---

## 6. Pruebas desde consola

### Obtener métricas

curl http://127.0.0.1:8000/api/metrics/

Con formato:

curl http://127.0.0.1:8000/api/metrics/ | jq

### Iniciar scraping

curl -X POST http://127.0.0.1:8000/scheduler/start \
  -H "Content-Type: application/json" \
  -d '{"medio": "biobiochile", "num_scrapers": 4}'

### Detener scraping

curl -X POST http://127.0.0.1:8000/scheduler/stop

### Ver estado

curl http://127.0.0.1:8000/scheduler/status

---

## 7. Uso desde frontend

### Obtener métricas

```javascript
fetch("http://172.105.21.15:8080/api/metrics/")
  .then(res => res.json())
  .then(data => {
      console.log(data);
  });
```

### Iniciar scraping

```javascript
fetch("http://172.105.21.15:8080/scheduler/start", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    medio: "biobiochile",
    num_scrapers: 4
  })
})
  .then(res => res.json())
  .then(data => console.log("Scheduler iniciado:", data))
  .catch(err => console.error("Error:", err));
```

### Detener scraping

```javascript
fetch("http://172.105.21.15:8080/scheduler/stop", {
  method: "POST"
})
  .then(res => res.json())
  .then(data => console.log("Scheduler detenido:", data))
  .catch(err => console.error("Error:", err));
```

### Verificar estado

```javascript
fetch("http://172.105.21.15:8080/scheduler/status")
  .then(res => res.json())
  .then(data => console.log("Estado:", data.status));
```

---

## 8. Dashboard en tiempo real

Para visualizar las métricas en tiempo real con gráficos interactivos:

```bash
python grafico.py
```

El dashboard se conecta vía WebSocket a `/api/metrics/` y actualiza automáticamente:
- Progreso del crawler (barra de progreso)
- Artículos scrapeados exitosamente
- Errores en el scraping
- Velocidad de procesamiento (artículos/minuto)
- Gráfico de progreso en tiempo real

Acceso: http://localhost:8000 (se abre automáticamente en el navegador)

---

## 9. Limitaciones

- No incluye autenticación.
- Depende de los archivos JSON generados por otros módulos.
- El scheduler solo puede ejecutar un medio a la vez.

---

## 10. Resumen rápido

| Acción | Comando |
|--------|---------|
| Iniciar API local | `uvicorn api_metricas.main:app --reload` |
| Iniciar API en servidor | `./venv/bin/uvicorn api_metricas.main:app --host 0.0.0.0 --port 8080` |
| Iniciar scraping | `curl -X POST http://localhost:8000/scheduler/start -H "Content-Type: application/json" -d '{"medio": "biobiochile", "num_scrapers": 4}'` |
| Detener scraping | `curl -X POST http://localhost:8000/scheduler/stop` |
| Ver estado | `curl http://localhost:8000/scheduler/status` |
| Ver métricas | `curl http://localhost:8000/api/metrics/` |
| Dashboard visual | `python grafico.py` |
| Documentación interactiva | http://localhost:8000/docs |

### Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/metrics/` | Obtiene métricas en tiempo real |
| POST | `/scheduler/start` | Inicia el scraping |
| POST | `/scheduler/stop` | Detiene el scraping |
| GET | `/scheduler/status` | Estado del scheduler |

### Medios soportados

- `biobiochile`: BioBio Chile
- `latercera`: La Tercera
