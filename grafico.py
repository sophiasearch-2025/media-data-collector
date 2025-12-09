"""
Dashboard interactivo para monitorear el progreso del scraping en tiempo real
Muestra gráficos y métricas actualizadas vía WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Dashboard Scraping - Tiempo Real")

# Conexiones WebSocket activas
active_connections: list[WebSocket] = []

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Leer métricas en tiempo real
            data = {}
            
            # Progreso del crawler
            progress_path = Path("metrics/crawler_progress.json")
            if progress_path.exists():
                with open(progress_path, "r") as f:
                    data["progress"] = json.load(f)
            
            # Métricas finales del crawler
            crawler_path = Path("metrics/crawler_metrics.json")
            if crawler_path.exists():
                with open(crawler_path, "r") as f:
                    data["crawler"] = json.load(f)
            
            # Métricas del scraper
            scraper_path = Path("metrics/scraper_metrics.json")
            if scraper_path.exists():
                with open(scraper_path, "r") as f:
                    data["scraper"] = json.load(f)
            
            # Timestamp actual
            data["timestamp"] = datetime.now().isoformat()
            
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Scraping en Tiempo Real</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto;
        }
        h1 { 
            color: white; 
            margin-bottom: 2rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .status-bar {
            background: rgba(255,255,255,0.95);
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status-badge {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.875rem;
        }
        .status-connected { background: #10b981; color: white; }
        .status-disconnected { background: #ef4444; color: white; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-title {
            font-size: 0.875rem;
            color: #64748b;
            margin-bottom: 0.5rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1e293b;
        }
        .stat-subtitle {
            font-size: 0.875rem;
            color: #94a3b8;
            margin-top: 0.25rem;
        }
        .chart-container {
            background: rgba(255,255,255,0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
        }
        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 1.5rem;
        }
        .progress-section {
            background: rgba(255,255,255,0.95);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .progress-bar-container {
            background: #e2e8f0;
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            margin: 1rem 0;
            position: relative;
        }
        .progress-bar {
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            width: 0%;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.875rem;
        }
        .pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Dashboard de Scraping - Monitoreo en Tiempo Real</h1>
        
        <div class="status-bar">
            <div>
                <strong>Estado de Conexión</strong>
            </div>
            <span class="status-badge status-disconnected" id="connection-status">Desconectado</span>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">🕷️ URLs Encontradas</div>
                <div class="stat-value" id="stat-urls">0</div>
                <div class="stat-subtitle">Por el crawler</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">✅ Artículos Exitosos</div>
                <div class="stat-value" id="stat-success">0</div>
                <div class="stat-subtitle">Scrapeados correctamente</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">❌ Errores</div>
                <div class="stat-value" id="stat-errors">0</div>
                <div class="stat-subtitle">Fallos en scraping</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">⚡ Velocidad</div>
                <div class="stat-value" id="stat-rate">0</div>
                <div class="stat-subtitle">artículos/min</div>
            </div>
        </div>

        <div class="progress-section">
            <h2 class="chart-title">Progreso del Crawler</h2>
            <div>
                <strong id="progress-text">Esperando inicio...</strong>
                <span style="float: right; color: #64748b;" id="progress-percent">0%</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar">0%</div>
            </div>
            <div style="color: #64748b; font-size: 0.875rem;">
                <span id="progress-details">0 de 0 categorías procesadas</span>
            </div>
        </div>

        <div class="chart-container">
            <h2 class="chart-title">📈 Noticias Scrapeadas en Tiempo Real</h2>
            <canvas id="scrapingChart"></canvas>
        </div>

        <div class="chart-container">
            <h2 class="chart-title">📊 Distribución: Éxitos vs Errores</h2>
            <canvas id="pieChart"></canvas>
        </div>
    </div>

    <script>
        // Configuración de gráficos
        const timeLabels = [];
        const successData = [];
        const errorData = [];
        const maxDataPoints = 30;

        // Gráfico de línea temporal
        const lineCtx = document.getElementById('scrapingChart').getContext('2d');
        const lineChart = new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [
                    {
                        label: 'Artículos Exitosos',
                        data: successData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Errores',
                        data: errorData,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                animation: {
                    duration: 750
                }
            }
        });

        // Gráfico de pastel
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        const pieChart = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Exitosos', 'Errores'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right'
                    }
                }
            }
        });

        // WebSocket
        let ws;
        const statusEl = document.getElementById('connection-status');

        function connect() {
            ws = new WebSocket('ws://localhost:8001/ws/realtime');
            
            ws.onopen = () => {
                console.log('✅ Conectado al servidor de métricas');
                statusEl.textContent = 'Conectado';
                statusEl.className = 'status-badge status-connected pulse';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = (error) => {
                console.error('❌ Error en WebSocket:', error);
                statusEl.textContent = 'Error';
                statusEl.className = 'status-badge status-disconnected';
            };
            
            ws.onclose = () => {
                console.log('🔌 Desconectado del servidor');
                statusEl.textContent = 'Reconectando...';
                statusEl.className = 'status-badge status-disconnected pulse';
                setTimeout(connect, 3000);
            };
        }

        function updateDashboard(data) {
            // Actualizar estadísticas
            if (data.progress) {
                document.getElementById('stat-urls').textContent = data.progress.urls_encontradas || 0;
            }
            
            if (data.scraper) {
                const s = data.scraper;
                document.getElementById('stat-success').textContent = s.total_articulos_exitosos || 0;
                document.getElementById('stat-errors').textContent = s.total_articulos_fallidos || 0;
                document.getElementById('stat-rate').textContent = 
                    (s.articulos_por_minuto || 0).toFixed(1);
                
                // Actualizar gráficos
                const time = new Date().toLocaleTimeString();
                timeLabels.push(time);
                successData.push(s.total_articulos_exitosos || 0);
                errorData.push(s.total_articulos_fallidos || 0);
                
                // Mantener solo los últimos N puntos
                if (timeLabels.length > maxDataPoints) {
                    timeLabels.shift();
                    successData.shift();
                    errorData.shift();
                }
                
                lineChart.update('none');
                
                // Actualizar gráfico de pastel
                pieChart.data.datasets[0].data = [
                    s.total_articulos_exitosos || 0,
                    s.total_articulos_fallidos || 0
                ];
                pieChart.update('none');
            }
            
            // Actualizar progreso
            if (data.progress) {
                const p = data.progress;
                const progressBar = document.getElementById('progress-bar');
                const progressPercent = document.getElementById('progress-percent');
                const progressText = document.getElementById('progress-text');
                const progressDetails = document.getElementById('progress-details');
                
                progressBar.style.width = `${p.porcentaje || 0}%`;
                progressBar.textContent = `${p.porcentaje || 0}%`;
                progressPercent.textContent = `${p.porcentaje || 0}%`;
                
                progressDetails.textContent = 
                    `${p.categorias_procesadas || 0} de ${p.total_categorias || 0} categorías procesadas`;
                
                if (p.status === 'completed') {
                    progressText.textContent = '✅ Crawler completado';
                    progressBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
                } else if (p.status === 'running') {
                    progressText.textContent = '⚙️ Crawler en proceso...';
                    progressBar.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
                } else {
                    progressText.textContent = '⏳ Iniciando crawler...';
                }
            }
        }

        // Iniciar conexión
        connect();
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando Dashboard de Scraping en Tiempo Real")
    print("📊 Abre tu navegador en: http://localhost:8001")
    print("💡 Asegúrate de que el crawler esté corriendo para ver datos en tiempo real\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)
