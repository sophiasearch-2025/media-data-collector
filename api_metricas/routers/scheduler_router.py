from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import sys
import os

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

class CrawlerStartRequest(BaseModel):
    medio: str
    num_scrapers: int = 1

# Variable global para mantener referencia al proceso
scheduler_status = None

@router.post("/start")
async def start_scheduler(request: CrawlerStartRequest):
    """Inicia el scheduler para un medio específico"""
    global scheduler_status
    
    # Verificar si scheduler está corriendo
    if scheduler_status and scheduler_status.poll() is None:
        raise HTTPException(status_code=400, detail="Crawler ya está corriendo")
    
    # Verificar si hay procesos de scraper corriendo (protección adicional)
    try:
        result = subprocess.run(
            ["pgrep", "-f", "scraper_biobio.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            raise HTTPException(
                status_code=400, 
                detail="Hay scrapers corriendo. Detén el proceso primero antes de iniciar uno nuevo."
            )
    except FileNotFoundError:
        # pgrep no disponible, continuar
        pass
    
    try:
        import json
        from pathlib import Path
        
        # Resetear métricas antes de iniciar
        metrics_dir = Path(PROJECT_ROOT) / "metrics"
        metrics_dir.mkdir(exist_ok=True)
        
        # Resetear scraper_progress.json (para dashboard en tiempo real)
        scraper_progress = {
            "total_articulos_exitosos": 0,
            "total_articulos_fallidos": 0,
            "duracion_promedio_ms": 0,
            "articulos_por_minuto": 0,
            "ultima_actualizacion": ""
        }
        with open(metrics_dir / "scraper_progress.json", "w", encoding="utf-8") as f:
            json.dump(scraper_progress, f, ensure_ascii=False, indent=2)
        
        # Resetear crawler_progress.json
        crawler_progress = {
            "sitio": request.medio,
            "status": "starting",
            "total_categorias": 0,
            "categorias_procesadas": 0,
            "porcentaje": 0,
            "urls_encontradas": 0
        }
        with open(metrics_dir / "crawler_progress.json", "w", encoding="utf-8") as f:
            json.dump(crawler_progress, f, ensure_ascii=False, indent=2)
        
        python_exec = sys.executable
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        # Iniciar scheduler que maneja crawler + scrapers
        scheduler_status = subprocess.Popen(
            [python_exec, os.path.join(PROJECT_ROOT, "RabbitMQ", "scheduler.py"), 
             request.medio, str(request.num_scrapers)],
            env=env
        )
        
        return {
            "status": "started",
            "medio": request.medio,
            "pid": scheduler_status.pid,
            "num_scrapers": request.num_scrapers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al iniciar crawler: {str(e)}")

@router.post("/stop")
async def stop_scheduler():
    """Detiene el scheduler y todos sus procesos hijos"""
    global scheduler_status
    
    if not scheduler_status or scheduler_status.poll() is not None:
        raise HTTPException(status_code=400, detail="No hay crawler corriendo")
    
    try:
        import signal
        
        # Matar todos los procesos relacionados usando pkill
        subprocess.run(["pkill", "-TERM", "-f", "scheduler.py"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "crawler.py"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "scraper_biobio.py"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "send_data.py"], check=False)
        subprocess.run(["pkill", "-TERM", "-f", "logger.py"], check=False)
        
        # Esperar un poco
        import time
        time.sleep(2)
        
        # Si aún quedan procesos, forzar kill
        subprocess.run(["pkill", "-9", "-f", "scheduler.py"], check=False)
        subprocess.run(["pkill", "-9", "-f", "crawler.py"], check=False)
        subprocess.run(["pkill", "-9", "-f", "scraper_biobio.py"], check=False)
        subprocess.run(["pkill", "-9", "-f", "send_data.py"], check=False)
        subprocess.run(["pkill", "-9", "-f", "logger.py"], check=False)
        
        scheduler_status = None
        return {"status": "stopped"}
        
    except Exception as e:
        scheduler_status = None
        raise HTTPException(status_code=500, detail=f"Error al detener crawler: {str(e)}")

@router.get("/status")
async def get_scheduler_status():
    """Obtiene el estado actual del crawler"""
    global scheduler_status
    
    if not scheduler_status:
        return {"status": "not_started"}
    
    if scheduler_status.poll() is None:
        return {"status": "running", "pid": scheduler_status.pid}
    else:
        return {"status": "stopped", "exit_code": scheduler_status.returncode}
