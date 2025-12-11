from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api_metricas.routers.metrics_router import router as metrics_router
from api_metricas.routers.scheduler_router import router as scheduler_router

app = FastAPI(title="API Métricas Sophia")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Registrar las rutas
app.include_router(metrics_router)
app.include_router(scheduler_router)

@app.get("/")
def root():
    return {"message": "API de métricas funcionando"}
