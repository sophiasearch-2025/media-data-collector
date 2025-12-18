# Dashboard de Scraping en Tiempo Real

## 1. Descripción general

`grafico.py` es un dashboard interactivo desarrollado con FastAPI y Chart.js que permite monitorear el progreso del scraping en tiempo real mediante WebSocket.

**Características principales:**
- Visualización gráfica del progreso en tiempo real
- Actualización automática cada segundo vía WebSocket
- Gráfico histórico de artículos scrapeados
- Métricas en vivo: velocidad, errores, progreso del crawler
- Interfaz responsive y moderna

---

## 2. Arquitectura

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│                 │◄──────────────────────────►│                 │
│   Dashboard     │    Actualización cada 1s   │  grafico.py     │
│  (Navegador)    │                            │  (FastAPI)      │
│                 │                            │                 │
└─────────────────┘                            └────────┬────────┘
                                                        │
                                                        │ Lee cada 1s
                                                        │
                                                        ▼
                                               ┌─────────────────────┐
                                               │  metrics/           │
                                               │  ├─ crawler_progress│
                                               │  ├─ scraper_progress│
                                               │  └─ scraper_metrics │
                                               └─────────────────────┘
```

**Flujo de datos:**
1. Dashboard establece conexión WebSocket con el servidor
2. Servidor lee archivos JSON de métricas cada segundo
3. Servidor envía datos actualizados al navegador
4. Dashboard actualiza gráficos y estadísticas automáticamente

---

## 3. Instalación

### 3.1. Dependencias

Las dependencias ya están incluidas en `requirements.txt`:

```txt
fastapi
uvicorn[standard]
```

No requiere instalaciones adicionales, ya que Chart.js se carga desde CDN.

### 3.2. Verificar instalación

```bash
source .venv/bin/activate
pip list | grep fastapi
```

---

## 4. Ejecución

### 4.1. Iniciar el dashboard

**Método 1: Ejecución directa**

```bash
python grafico.py
```

**Método 2: Con uvicorn (producción)**

```bash
uvicorn grafico:app --host 0.0.0.0 --port 8001 --reload
```

### 4.2. Acceder al dashboard

Abrir en el navegador:
- **Local:** http://localhost:8001
- **Red local:** http://[IP_DEL_SERVIDOR]:8001

El dashboard se abre automáticamente en el navegador por defecto.

---

## 5. Interfaz y componentes

### 5.1. Barra de estado

Muestra el estado de la conexión WebSocket:
- 🟢 **Conectado** - Recibiendo actualizaciones en tiempo real
- 🔴 **Desconectado** - Sin conexión con el servidor

### 5.2. Tarjetas de estadísticas

**Sitio Actual**
- Medio siendo scrapeado (BioBio Chile / La Tercera)
- Estado actual del proceso

**URLs Encontradas**
- Total de URLs descubiertas por el crawler
- Muestra "Por el crawler" como subtítulo

**Artículos Exitosos**
- Número de artículos scrapeados correctamente
- Subtítulo: "Scrapeados correctamente"

**Errores**
- Cantidad de fallos en el scraping
- Subtítulo: "Fallos en scraping"

**Velocidad**
- Artículos procesados por minuto
- Subtítulo: "artículos/min"

### 5.3. Progreso del Crawler

Barra de progreso visual que muestra:
- Porcentaje de categorías procesadas
- Estado: "Crawler en proceso..." o "Crawler completado"
- Categorías procesadas de total (Ej: "26 de 78 categorías procesadas")

### 5.4. Gráfico de progreso

Gráfico de líneas en tiempo real con:
- **Línea verde:** Artículos exitosos (área rellena)
- **Línea roja:** Errores
- **Eje X:** Timestamps con formato HH:MM:SS
- **Eje Y:** Cantidad de artículos

**Características:**
- Se actualiza automáticamente cada segundo
- Muestra últimos 100 puntos de datos
- Animaciones suaves
- Legends interactivas (click para ocultar/mostrar)

---

## 6. Archivos de métricas leídos

El dashboard consume los siguientes archivos JSON:

### 6.1. `crawler_progress.json`

Progreso del crawler en tiempo real.

```json
{
  "sitio": "biobiochile",
  "status": "in_progress",
  "total_categorias": 78,
  "categorias_procesadas": 26,
  "porcentaje": 33.3,
  "urls_encontradas": 450
}
```

### 6.2. `scraper_progress.json`

Progreso de los scrapers por medio (estructura per-medio).

```json
{
  "biobiochile": {
    "total_articulos_exitosos": 268,
    "total_articulos_fallidos": 0,
    "duracion_promedio_ms": 989.85,
    "articulos_por_minuto": 65.24,
    "ultima_actualizacion": "2025-12-12 15:12:39",
    "start_time": "2025-12-12 15:08:33"
  }
}
```

### 6.3. `scraper_metrics.json`

Métricas finales generadas por el logger al terminar.

```json
{
  "biobiochile": {
    "total_logs": 450,
    "articulos_exitosos": 450,
    "articulos_fallidos": 0,
    "fecha_inicio": "Jueves 12 diciembre de 2025",
    "fecha_termino": "Jueves 12 diciembre de 2025"
  }
}
```

---

## 7. Configuración

### 7.1. Puerto del servidor

Por defecto usa el puerto **8001** para no conflictuar con la API principal (puerto 8000).

**Cambiar puerto:**

```python
# En grafico.py, línea final
uvicorn.run(app, host="0.0.0.0", port=8001)  # Cambiar 8001
```

### 7.2. Intervalo de actualización

Por defecto actualiza cada **1 segundo**.

**Cambiar intervalo:**

```python
# En grafico.py, función websocket_endpoint
await asyncio.sleep(1)  # Cambiar a 0.5 para actualizar cada 500ms
```

### 7.3. File locking en lectura

El dashboard usa file locking con `fcntl.LOCK_SH` (shared lock) para leer archivos de forma segura mientras los scrapers escriben.

Ver [api_metricas/routers/metrics_router.py](../api_metricas/routers/metrics_router.py) para la implementación.

---

## 8. Uso conjunto con la API

### Escenario típico:

1. **Terminal 1:** Iniciar API de métricas
   ```bash
   uvicorn api_metricas.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Terminal 2:** Iniciar dashboard
   ```bash
   python grafico.py
   ```

3. **Terminal 3:** Iniciar scraping via API
   ```bash
   curl -X POST http://localhost:8000/scheduler/start \
     -H "Content-Type: application/json" \
     -d '{"medio": "biobiochile", "num_scrapers": 4}'
   ```

4. **Navegador:** Ver progreso en tiempo real
   - Dashboard: http://localhost:8001
   - API docs: http://localhost:8000/docs

---

## 9. Solución de problemas

### 9.1. Dashboard muestra "Desconectado"

**Causa:** El servidor FastAPI de grafico.py no está corriendo.

**Solución:**
```bash
python grafico.py
```

### 9.2. No se actualizan los datos

**Causa:** Los archivos JSON no existen o están vacíos.

**Solución:**
1. Verificar que el scraping esté corriendo
2. Revisar que existan los archivos en `metrics/`
3. Verificar permisos de lectura

```bash
ls -la metrics/
cat metrics/scraper_progress.json
```

### 9.3. Error de puerto ocupado

**Causa:** El puerto 8001 ya está en uso.

**Solución:**
```bash
# Ver qué proceso usa el puerto
lsof -i :8001

# Matar el proceso
kill -9 [PID]

# O cambiar el puerto en grafico.py
```

### 9.4. Gráfico no se dibuja

**Causa:** Chart.js no cargó desde el CDN.

**Solución:**
1. Verificar conexión a internet
2. Abrir consola del navegador (F12) para ver errores
3. Recargar la página (Ctrl+R)

---

## 10. Características avanzadas

### 10.1. Detección de medio actual

El dashboard detecta automáticamente el medio que se está scrapeando:

```javascript
// Prioridad:
// 1. Desde crawler_progress.json (field "sitio")
// 2. Desde scraper_progress.json (primera clave disponible)
const medioActivo = data.progress?.sitio || 
                    Object.keys(data.scraper || {})[0] || 
                    'N/A';
```

### 10.2. Manejo de archivos corruptos

Incluye try-catch para JSON inválido durante escritura simultánea:

```python
try:
    with open(scraper_progress_path, "r") as f:
        content = f.read()
        if content.strip():
            data["scraper"] = json.loads(content)
except (json.JSONDecodeError, IOError):
    pass  # Skip si el archivo está siendo escrito
```

### 10.3. Animaciones suaves

- Transiciones CSS para cambios de valores
- Chart.js con animación activada
- Pulse animation para indicadores en tiempo real

---

## 11. Resumen rápido

| Acción | Comando |
|--------|---------|
| Iniciar dashboard | `python grafico.py` |
| URL del dashboard | http://localhost:8001 |
| Cambiar puerto | Editar línea final de `grafico.py` |
| Ver logs del servidor | Terminal donde se ejecutó `python grafico.py` |
| Detener dashboard | `Ctrl+C` en la terminal |

### Checklist antes de usar el dashboard

- ✅ API de métricas corriendo en puerto 8000
- ✅ Scraping iniciado (via API o manualmente)
- ✅ Archivos en `metrics/` siendo actualizados
- ✅ Dashboard corriendo en puerto 8001
- ✅ Navegador abierto en http://localhost:8001

---

## 12. Tecnologías utilizadas

- **Backend:** FastAPI + WebSocket
- **Frontend:** HTML5 + JavaScript vanilla
- **Gráficos:** Chart.js 4.4.0
- **Estilos:** CSS3 con gradientes y animaciones
- **Comunicación:** WebSocket para updates en tiempo real
- **File I/O:** Python pathlib + json

