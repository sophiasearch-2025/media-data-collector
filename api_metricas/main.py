from fastapi import FastAPI
from api_metricas.routers.metrics_router import router as metrics_router

app = FastAPI(title="API Métricas Sophia")

# Registrar las rutas
app.include_router(metrics_router)

@app.get("/")
def root():
    return {"message": "API de métricas funcionando"}
