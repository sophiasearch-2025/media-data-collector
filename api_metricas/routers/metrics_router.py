from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

BASE_DIR = Path(__file__).resolve().parents[2] / "metrics"

class MetricData(BaseModel):
    crawler_metrics: dict
    scraper_metrics: dict

@router.get("/", summary="Obtener métricas del sistema",
                 operation_id="get_metrics")


def get_metrics():
    """Lee las métricas desde los archivos JSON"""
    try:
        crawler_path = BASE_DIR / "crawler_metrics.json"
        scraper_path = BASE_DIR / "scraper_metrics.json"

        with open(crawler_path, "r", encoding="utf-8") as f:
            crawler = json.load(f)

        with open(scraper_path, "r", encoding="utf-8") as f:
            scraper = json.load(f)

        return {
            "crawler_metrics": crawler,
            "scraper_metrics": scraper
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontraron los archivos de métricas")


""" @router.post("/", summary="Recibir métricas desde otro sistema o interfaz")
def post_metrics(data: MetricData):
    #Recibe métricas (por ejemplo, desde el scraper o la interfaz)
    crawler_path = BASE_DIR / "crawler_metrics.json"
    scraper_path = BASE_DIR / "scraper_metrics.json"

    # Guarda los datos en los archivos JSON
    with open(crawler_path, "w", encoding="utf-8") as f:
        json.dump(data.crawler_metrics, f, indent=4, ensure_ascii=False)

    with open(scraper_path, "w", encoding="utf-8") as f:
        json.dump(data.scraper_metrics, f, indent=4, ensure_ascii=False)

    return {"message": "Métricas actualizadas correctamente."} """

#Estas líneas están comentadas para evitar que se sobrescriban las métricas existentes y
# la funcion POST no se utiliza actualmente. (está solo para referencia futura).