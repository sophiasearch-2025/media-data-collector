# README — API de Métricas Sophia

## 1. Descripción general

La API de Métricas Sophia es un servicio desarrollado con FastAPI que expone las métricas generadas por los módulos Crawler y Scraper del proyecto Sophia Search.

Los datos se almacenan en archivos JSON dentro de la carpeta:

metrics/
    crawler_metrics.json
    scraper_metrics.json

La API entrega estos datos para que la Interfaz de Administrador pueda visualizarlos y analizarlos.

La API expone un único endpoint:

GET /api/metrics/

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

## 5. Pruebas desde consola

curl http://127.0.0.1:8000/api/metrics/

Con formato:

curl http://127.0.0.1:8000/api/metrics/ | jq

---

## 6. Uso desde frontend

fetch("http://172.105.21.15:8080/api/metrics/")
  .then(res => res.json())
  .then(data => {
      console.log(data);
  });

---

## 7. Limitaciones

- Solo expone un endpoint GET.
- No incluye autenticación.
- Depende de los archivos JSON generados por otros módulos.

---

## 8. Resumen rápido

| Acción | Comando |
|--------|---------|
| Iniciar API local | uvicorn api_metricas.main:app --reload |
| Iniciar API en servidor | ./venv/bin/uvicorn api_metricas.main:app --host 0.0.0.0 --port 8080 |
| Documentación | /docs |
| Métricas | /api/metrics/ |
