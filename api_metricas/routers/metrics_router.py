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
        scraper_path = BASE_DIR / "scraper_metrics.json"
        progress_path = BASE_DIR / "crawler_progress.json"

        with open(crawler_path, "r", encoding="utf-8") as f:
            crawler = json.load(f)

        with open(scraper_path, "r", encoding="utf-8") as f:
            scraper = json.load(f)

        with open(progress_path, "r", encoding="utf-8") as f:
            progress = json.load(f)

        return {
            "crawler_metrics": crawler,
            "scraper_metrics": scraper,
            "crawler_progress": progress
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontraron los archivos de métricas")
