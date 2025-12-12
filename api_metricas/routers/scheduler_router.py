from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import sys
import os
import signal
import time

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
        
        # Resetear scraper_progress.json usando función con file locking
        sys.path.insert(0, PROJECT_ROOT)
        from scheduler.scheduler_queue_utils import initialize_scraper_progress
        initialize_scraper_progress(request.medio)
        
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
            [python_exec, "-m", "scheduler.main", 
             request.medio, str(request.num_scrapers)],
            env=env,
            cwd=PROJECT_ROOT
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
    
    try:
        
        # Si no tenemos referencia al proceso, buscar por nombre
        scheduler_pid = None
        if scheduler_status and scheduler_status.poll() is None:
            scheduler_pid = scheduler_status.pid
        else:
            # Buscar proceso scheduler.main usando pgrep
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "scheduler.main"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    scheduler_pid = int(result.stdout.strip().split()[0])
                    print(f"Encontrado scheduler corriendo con PID: {scheduler_pid}")
            except (FileNotFoundError, ValueError):
                pass
        
        if not scheduler_pid:
            raise HTTPException(status_code=400, detail="No hay crawler corriendo")
        
        # El nuevo scheduler maneja SIGTERM/SIGINT correctamente
        # Enviar SIGTERM al proceso principal (scheduler)
        print(f"Enviando SIGTERM al scheduler (PID: {scheduler_pid})")
        os.kill(scheduler_pid, signal.SIGTERM)
        
        # Esperar a que termine gracefully (máximo 180 segundos - 3 minutos)
        # El scheduler puede estar esperando que colas se vacíen
        max_wait = 180
        waited = 0
        while waited < max_wait:
            # Verificar si el proceso sigue corriendo
            try:
                os.kill(scheduler_pid, 0)  # Signal 0 solo verifica si existe
                time.sleep(1)
                waited += 1
            except ProcessLookupError:
                # El proceso ya no existe
                print("Scheduler detenido correctamente")
                break
        else:
            # Si llegamos aquí, el proceso no se detuvo en 3 minutos
            print("Scheduler no respondió a SIGTERM en 3 minutos, forzando con SIGKILL")
            try:
                os.kill(scheduler_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Ya terminó
        
        scheduler_status = None
        
        # Limpiar colas de RabbitMQ después de detener
        try:
            import pika
            print("Limpiando colas de RabbitMQ...")
            rabbit_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
            rabbit_ch = rabbit_conn.channel()
            
            queues_to_purge = [
                "scraper_queue",
                "scraping_log_queue",
                "crawler_log_queue",
                "scheduler_log_queue",
                "logging_control_queue",
                "send_data_queue"
            ]
            
            for queue_name in queues_to_purge:
                try:
                    result = rabbit_ch.queue_purge(queue=queue_name)
                    print(f"  - {queue_name}: {result.method.message_count} mensajes eliminados")
                except Exception as e:
                    print(f"  - Error limpiando {queue_name}: {e}")
            
            rabbit_ch.close()
            rabbit_conn.close()
            print("Colas limpiadas correctamente")
        except Exception as e:
            print(f"Advertencia: No se pudieron limpiar las colas: {e}")
        
        return {"status": "stopped", "queues_purged": True}
        
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
