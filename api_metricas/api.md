# Despliegue y Acceso a la API de Métricas Sophia

## 1. Descripción general

La **API de Métricas Sophia** es un servicio desarrollado con **FastAPI** que permite acceder a las métricas generadas por los módulos **Crawler** y **Scraper** del proyecto.  
Estas métricas se almacenan en la carpeta `metrics/` en formato JSON y se actualizan automáticamente cada vez que los componentes de recopilación ejecutan su proceso.

La API expone un único endpoint:

```
GET /api/metrics/
```

Este endpoint lee los archivos `crawler_metrics.json` y `scraper_metrics.json` y entrega su contenido en formato JSON para que la **Interfaz de Administrador (grupo 3)** los consuma y visualice.

---

## 2. Ejecución del servidor en entorno local

Para iniciar la API localmente en modo desarrollo:

```bash
uvicorn api_metricas.main:app --reload
```

Esto levanta el servidor en:

```
http://127.0.0.1:8000
```

Podrás acceder a:

- **Swagger UI (documentación interactiva):** http://127.0.0.1:8000/docs  
- **Métricas (JSON):** http://127.0..1:8000/api/metrics/

Este modo solo es accesible desde tu propio computador (localhost).

---

## 3. Despliegue en red local (para acceso desde otros PCs)

Para que otros equipos de la misma red Wi-Fi o LAN puedan acceder a tu API, debes permitir conexiones externas a tu servidor.

### 3.1. Ejecutar FastAPI escuchando todas las interfaces

```bash
uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000
```

### 3.2. Obtener tu IP local

```bash
hostname -I
```

Ejemplo de salida:

```
192.168.1.45
```

### 3.3. Acceso desde otro equipo de la red

Cualquier otro PC conectado a la misma red podrá abrir en el navegador:

```
http://192.168.1.45:8000/docs
```

y acceder directamente a las métricas en:

```
http://192.168.1.45:8000/api/metrics/
```

### 3.4. (Opcional) Permitir tráfico en el puerto 8000

Si el firewall bloquea las conexiones:

```bash
sudo ufw allow 8000
```

---

## 4. Despliegue en Internet (para acceso remoto o demo pública)

FastAPI no publica la API directamente en Internet.  
Si se necesita que el equipo acceda desde cualquier lugar, existen dos opciones gratuitas.

### Opción 1: Usar ngrok (rápido y sin configuración)

Ngrok permite exponer tu API local a Internet de forma temporal mediante un túnel seguro HTTPS.  
Ideal para **demos, pruebas o acceso remoto** sin necesidad de configurar puertos o routers.

#### 1. Instalar ngrok (método recomendado)

Ejecuta en tu terminal:

```bash
sudo apt update
sudo apt install ngrok
```

Si tu sistema no encuentra el paquete, puedes instalarlo manualmente con:

```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc   | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null   && echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main"   | sudo tee /etc/apt/sources.list.d/ngrok.list   && sudo apt update   && sudo apt install ngrok
```

#### 2. Conectar tu cuenta (solo la primera vez)

1. Crea o inicia sesión en [https://dashboard.ngrok.com](https://dashboard.ngrok.com)  
2. Copia tu **authtoken** desde el panel.  
3. Ejecútalo en tu terminal:

```bash
ngrok config add-authtoken TU_AUTHTOKEN_AQUI
```

#### 3. Ejecutar la API de FastAPI

```bash
uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000
```

#### 4. Abrir el túnel de ngrok

En otra terminal (sin cerrar la anterior):

```bash
ngrok http 8000
```

Verás una salida similar a:

```
Forwarding  https://random-id.ngrok-free.dev -> http://localhost:8000
```

#### 5. Acceder desde cualquier lugar

Usa la URL pública mostrada por ngrok (por ejemplo):

```
https://random-id.ngrok-free.dev
```

**Rutas disponibles:**
- `/docs` → Documentación interactiva (Swagger UI)  
- `/api/metrics/` → JSON con las métricas  

#### Consideraciones importantes

- La URL generada por ngrok es temporal y cambia cada vez que reinicias ngrok.  
- Si cierras la terminal de ngrok o apagas el equipo, el túnel se cierra.  
- Si necesitas una URL fija o persistente, puedes:
  - Usar el plan Pro de ngrok, o  
  - Desplegar la API en Render (ver siguiente sección).

#### Consejo práctico (automatización)

Puedes crear un script simple para levantar automáticamente la API y ngrok juntos:

```bash
#!/bin/bash
uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000 &
sleep 3
ngrok http 8000
```

Guárdalo como `deploy_ngrok.sh`, luego dale permisos de ejecución:

```bash
chmod +x deploy_ngrok.sh
```

Y ejecútalo así:

```bash
./deploy_ngrok.sh
```

Esto levantará tu API y el túnel de ngrok automáticamente.

---

### Opción 2: Desplegar en Render (gratuito)

1. Crear una cuenta en [https://render.com](https://render.com)  
2. Conectar el repositorio de GitHub donde esté la API.  
3. Crear un nuevo servicio web (“New Web Service”).  
4. Configuración recomendada:
   - **Runtime:** Python  
   - **Build Command:**  
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**  
     ```bash
     uvicorn api_metricas.main:app --host 0.0.0.0 --port 10000
     ```
   - **Port:** 10000
5. Render desplegará la API y entregará una URL pública, por ejemplo:

```
https://api-metricas-sophia.onrender.com
```

Accesos disponibles:

- https://api-metricas-sophia.onrender.com/docs  
- https://api-metricas-sophia.onrender.com/api/metrics/

---

## 5. Cómo probar la API

Verificar el funcionamiento desde la terminal:

```bash
curl http://127.0.0.1:8000/api/metrics/
```

Para visualizar la respuesta con formato legible:

```bash
curl http://127.0.0.1:8000/api/metrics/ | jq
```

Instalar `jq` (opcional):

```bash
sudo apt install jq
```

`jq` no es necesario para usar la API; solo formatea el JSON en la terminal.

---

## 6. Uso por parte del equipo de Interfaz

El grupo de interfaz debe realizar solicitudes `GET` a:

```
http://<IP_DEL_SERVIDOR>:8000/api/metrics/
```

### Ejemplo con JavaScript:

```js
fetch("http://192.168.1.45:8000/api/metrics/")
  .then(res => res.json())
  .then(data => {
    console.log("Métricas recibidas:", data);
    // Ejemplo de acceso:
    // data.crawler_metrics.urls_por_minuto
    // data.scraper_metrics.porcentaje_exito
  })
  .catch(err => console.error("Error al obtener métricas:", err));
```

### Librerías recomendadas para visualización:

- Fetch API (nativa en JS)
- Chart.js o Recharts (para graficar)
- Bootstrap o Tailwind (para los estilos del dashboard)

---

## 7. Resumen final

| Propósito | Comando / URL | Descripción |
|------------|----------------|--------------|
| Iniciar localmente | `uvicorn api_metricas.main:app --reload` | Acceso solo desde el equipo local |
| Acceso en LAN | `uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000` | Permite que otros equipos vean la API |
| URL de documentación | `/docs` | Interfaz Swagger para pruebas |
| URL de métricas | `/api/metrics/` | JSON con métricas del crawler y scraper |
| Ver en consola | `curl http://127.0.0.1:8000/api/metrics/ | jq` | Formato legible del JSON |
| Desplegar globalmente | `ngrok http 8000` o Render.com | Hace accesible la API en Internet |
