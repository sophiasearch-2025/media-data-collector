from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

BASE_DIR = Path(__file__).resolve().parents[2] / "metrics"

@router.get("/", summary="Obtener métricas del sistema",
            operation_id="get_metrics")
def get_metrics():
    """Lee las métricas desde los archivos JSON"""
    try:
        crawler_path = BASE_DIR / "crawler_metrics.json"
        scraper_metrics_path = BASE_DIR / "scraper_metrics.json"
        scraper_progress_path = BASE_DIR / "scraper_progress.json"
        crawler_progress_path = BASE_DIR / "crawler_progress.json"

        result = {}

        if crawler_path.exists():
            with open(crawler_path, "r", encoding="utf-8") as f:
                result["crawler_metrics"] = json.load(f)

        if scraper_metrics_path.exists():
            with open(scraper_metrics_path, "r", encoding="utf-8") as f:
                result["scraper_metrics"] = json.load(f)

        if scraper_progress_path.exists():
            with open(scraper_progress_path, "r", encoding="utf-8") as f:
                result["scraper_progress"] = json.load(f)

        if crawler_progress_path.exists():
            with open(crawler_progress_path, "r", encoding="utf-8") as f:
                result["crawler_progress"] = json.load(f)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo métricas: {str(e)}")
