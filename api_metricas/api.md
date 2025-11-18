# Despliegue y Acceso a la API de Métricas Sophia

## 1. Descripción general

La API de Métricas Sophia es un servicio desarrollado con FastAPI que permite acceder a las métricas generadas por los módulos Crawler y Scraper del proyecto.
Estas métricas se almacenan en la carpeta metrics/ en formato JSON y se actualizan automáticamente cada vez que los componentes de recopilación ejecutan su proceso.

La API expone un único endpoint:

GET /api/metrics/

Este endpoint lee los archivos crawler_metrics.json y scraper_metrics.json y entrega su contenido en formato JSON para que la Interfaz de Administrador (grupo 3) los consuma y visualice.

---

## 2. Configuración y Arranque Inicial ⚙️

Antes de ejecutar la API, es fundamental realizar dos pasos para evitar errores de importación y dependencias.

### 2.1. Activar el Entorno Virtual

Debes activar tu entorno virtual (.venv) para asegurar que Python utilice las librerías instaladas (FastAPI, Uvicorn, etc.) y no las del sistema.

* Ubicación del .venv: Según la estructura del proyecto, el entorno virtual se encuentra dentro de la carpeta api_metricas/.

    # Primero navega a la carpeta api_metricas si no estás allí
    # cd api_metricas/ 
    source .venv/bin/activate
    
    (Verás (.venv) al inicio de la línea de comando si la activación es exitosa.)

### 2.2. Posicionarse en el Directorio Correcto (Raíz del Proyecto)

Para que el comando uvicorn api_metricas.main:app funcione, debes estar en el directorio que contiene la carpeta api_metricas (la carpeta media-data-collector).

* Comando: Si acabas de activar el entorno virtual dentro de api_metricas/, usa:

    cd ..

---

## 3. Ejecución del Servidor en Entorno Local

Para iniciar la API localmente en modo desarrollo:

uvicorn api_metricas.main:app --reload

Esto levanta el servidor en:

http://127.0.0.1:8000

Podrás acceder a:

* Swagger UI (documentación interactiva): http://127.0.0.1:8000/docs
* Métricas (JSON): http://127.0.0.1:8000/api/metrics/

Este modo solo es accesible desde tu propio computador (localhost).

---

## 4. Despliegue en Red Local (para acceso desde otros PCs)

Para que otros equipos de la misma red Wi-Fi o LAN puedan acceder a tu API, debes permitir conexiones externas a tu servidor.

### 4.1. Ejecutar FastAPI escuchando todas las interfaces

uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000

### 4.2. Obtener tu IP local

hostname -I

Ejemplo de salida:

192.168.1.45

### 4.3. Acceso desde otro equipo de la red

Cualquier otro PC conectado a la misma red podrá abrir en el navegador:

http://192.168.1.45:8000/docs

y acceder directamente a las métricas en:

http://192.168.1.45:8000/api/metrics/

### 4.4. (Opcional) Permitir tráfico en el puerto 8000

Si el firewall bloquea las conexiones:

sudo ufw allow 8000

---

## 5. Despliegue en Internet (para acceso remoto o demo pública)

FastAPI no publica la API directamente en Internet.
Si se necesita que el equipo acceda desde cualquier lugar, existen dos opciones gratuitas.

### Opción 1: Usar ngrok (rápido y sin configuración)

Ngrok permite exponer tu API local a Internet de forma temporal mediante un túnel seguro HTTPS.
Ideal para demos, pruebas o acceso remoto sin necesidad de configurar puertos o routers.

#### 5.1. Instalar ngrok (método recomendado)

Ejecuta en tu terminal:

sudo apt update
sudo apt install ngrok

Si tu sistema no encuentra el paquete, puedes instalarlo manualmente con:

curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null  && echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main"  | sudo tee /etc/apt/sources.list.d/ngrok.list  && sudo apt update  && sudo apt install ngrok

#### 5.2. Conectar tu cuenta (solo la primera vez)

1. Crea o inicia sesión en https://dashboard.ngrok.com
2. Copia tu authtoken desde el panel.
3. Ejecútalo en tu terminal:

    ngrok config add-authtoken TU_AUTHTOKEN_AQUI

#### 5.3. Ejecutar la API de FastAPI

* Asegúrate de estar en el directorio raíz (media-data-collector) y con el entorno virtual activado.

    uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000

#### 5.4. Abrir el túnel de ngrok

En otra terminal (sin cerrar la anterior):

* Asegúrate de que tu entorno virtual esté activo también en esta segunda terminal.

    ngrok http 8000

Verás una salida similar a:

Forwarding  https://random-id.ngrok-free.dev -> http://localhost:8000

#### 5.5. Acceder desde cualquier lugar

Usa la URL pública mostrada por ngrok (por ejemplo):

https://random-id.ngrok-free.dev

Rutas disponibles:
* /docs → Documentación interactiva (Swagger UI)
* /api/metrics/ → JSON con las métricas

---

### Opción 2: Desplegar en Render (gratuito)

1. Crear una cuenta en https://render.com
2. Conectar el repositorio de GitHub donde esté la API.
3. Crear un nuevo servicio web (“New Web Service”).
4. Configuración recomendada:
    * Runtime: Python
    * Build Command:
        pip install -r requirements.txt
    * Start Command:
        uvicorn api_metricas.main:app --host 0.0.0.0 --port 10000
    * Port: 10000
5. Render desplegará la API y entregará una URL pública, por ejemplo:

    https://api-metricas-sophia.onrender.com

Accesos disponibles:

* https://api-metricas-sophia.onrender.com/docs
* https://api-metricas-sophia.onrender.com/api/metrics/

---

## 6. Cómo Probar la API

Verificar el funcionamiento desde la terminal:

curl http://127.0.0.1:8000/api/metrics/

Para visualizar la respuesta con formato legible:

curl http://127.0.0.1:8000/api/metrics/ | jq

Instalar jq (opcional):

sudo apt install jq

jq no es necesario para usar la API; solo formatea el JSON en la terminal.

---

## 7. Uso por Parte del Equipo de Interfaz

El grupo de interfaz debe realizar solicitudes GET a:

http://<IP_DEL_SERVIDOR>:8000/api/metrics/

### Ejemplo con JavaScript:

fetch("http://192.168.1.45:8000/api/metrics/")
  .then(res => res.json())
  .then(data => {
    console.log("Métricas recibidas:", data);
    // Ejemplo de acceso:
    // data.crawler_metrics.urls_por_minuto
    // data.scraper_metrics.porcentaje_exito
  })
  .catch(err => console.error("Error al obtener métricas:", err));

### Librerías recomendadas para visualización:

* Fetch API (nativa en JS)
* Chart.js o Recharts (para graficar)
* Bootstrap o Tailwind (para los estilos del dashboard)

---

## 8. Resumen Final

| Propósito | Comando / URL | Descripción |
| :--- | :--- | :--- |
| Paso 1: Activación | source .venv/bin/activate | Habilita el entorno virtual con las dependencias. |
| Paso 2: Ejecución Local | uvicorn api_metricas.main:app --reload | Inicia el servidor en modo desarrollo (solo localhost). |
| Acceso en LAN | uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000 | Permite que otros equipos vean la API. |
| URL de documentación | /docs | Interfaz Swagger para pruebas. |
| URL de métricas | /api/metrics/ | JSON con métricas del crawler y scraper. |
| Ver en consola | curl http://127.0.0.1:8000/api/metrics/ | jq | Formato legible del JSON. |
| Desplegar globalmente | ngrok http 8000 o Render.com | Hace accesible la API en Internet. |
