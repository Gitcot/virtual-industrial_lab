from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import assets, auth, motor_generation, simulation
from app.core.config import settings

app = FastAPI(
    title="Virtual Industrial Lab API",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
)

# CORS restrictif: à ajuster avec les domaines réels avant la mise en production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(simulation.router)
app.include_router(motor_generation.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}
