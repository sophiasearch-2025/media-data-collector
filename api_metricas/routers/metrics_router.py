from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
import os

# Bloqueo de archivos multiplataforma
if os.name == "nt":  # Windows
    import msvcrt
    def file_lock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def file_unlock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:  # Linux/Unix/MacOS
    import fcntl
    def file_lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock para lectura
    def file_unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

BASE_DIR = Path(__file__).resolve().parents[2] / "metrics"

def _read_json_with_lock(filepath: Path):
    """Lee archivo JSON con file locking"""
    if not filepath.exists():
        return None
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                file_lock(f)
                try:
                    data = json.load(f)
                finally:
                    file_unlock(f)
                return data
        except (IOError, OSError, json.JSONDecodeError) as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(0.1)
                continue
            raise e


@router.get("/", summary="Obtener métricas del sistema",
            operation_id="get_metrics")
def get_metrics():
    """Lee las métricas desde los archivos JSON con file locking"""
    try:
        crawler_path = BASE_DIR / "crawler_metrics.json"
        scraper_metrics_path = BASE_DIR / "scraper_metrics.json"
        scraper_progress_path = BASE_DIR / "scraper_progress.json"
        crawler_progress_path = BASE_DIR / "crawler_progress.json"

        result = {}

        crawler_data = _read_json_with_lock(crawler_path)
        if crawler_data:
            result["crawler_metrics"] = crawler_data

        scraper_metrics_data = _read_json_with_lock(scraper_metrics_path)
        if scraper_metrics_data:
            result["scraper_metrics"] = scraper_metrics_data

        scraper_progress_data = _read_json_with_lock(scraper_progress_path)
        if scraper_progress_data:
            result["scraper_progress"] = scraper_progress_data

        crawler_progress_data = _read_json_with_lock(crawler_progress_path)
        if crawler_progress_data:
            result["crawler_progress"] = crawler_progress_data

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo métricas: {str(e)}")
