"""
resenas-service: microservicio de reseñas de libros (Python + FastAPI).

Responsabilidad única: guardar y consultar reseñas.
No sabe nada de los libros más allá de su id (libroId).
Expone salud y métricas en las mismas rutas que Helidon (/observe/...)
para que todos los servicios compartan el mismo "contrato de observabilidad".
"""
import os
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

SERVICE_NAME = "resenas-service"
STARTED_AT = time.time()

app = FastAPI(
    title="Reseñas Service",
    description="Microservicio de reseñas - Programación Integrativa UTPL",
    version="1.0.0",
)

# ---------------------------------------------------------------- modelo y datos
class ResenaIn(BaseModel):
    libroId: int = Field(..., gt=0, examples=[1])
    autor: str = Field(..., min_length=2, examples=["María"])
    calificacion: int = Field(..., ge=1, le=5, examples=[5])
    comentario: str = Field("", max_length=500, examples=["Imprescindible."])


class Resena(ResenaIn):
    id: int


# "Base de datos" en memoria: cada microservicio es dueño de sus datos.
RESENAS: dict[int, Resena] = {
    1: Resena(id=1, libroId=1, autor="Ana", calificacion=5, comentario="Retrato crudo y necesario de la sierra ecuatoriana."),
    2: Resena(id=2, libroId=1, autor="Luis", calificacion=4, comentario="Duro de leer, pero imprescindible."),
    3: Resena(id=3, libroId=2, autor="Carla", calificacion=5, comentario="Macondo nunca se olvida."),
    4: Resena(id=4, libroId=3, autor="Diego", calificacion=4, comentario="Breve e inquietante."),
}
_next_id = 5

# ---------------------------------------------------------------- métricas
HTTP_REQUESTS = Counter(
    "http_requests_total", "Peticiones HTTP recibidas", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "Duración de las peticiones HTTP", ["method", "path"]
)
RESENAS_CREADAS = Counter("resenas_creadas_total", "Reseñas creadas desde el arranque")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "desconocida"  # /resenas/{id}, no /resenas/7
    if not path.startswith("/observe"):
        HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
        HTTP_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    response.headers["X-Service"] = SERVICE_NAME
    return response


# ---------------------------------------------------------------- API de negocio
@app.get("/", tags=["info"])
def info():
    return {"servicio": SERVICE_NAME, "lenguaje": "Python + FastAPI", "docs": "/docs"}


@app.get("/resenas", response_model=list[Resena], tags=["reseñas"])
def listar(libroId: int | None = None):
    """Lista todas las reseñas, o solo las de un libro con ?libroId=1"""
    datos = list(RESENAS.values())
    if libroId is not None:
        datos = [r for r in datos if r.libroId == libroId]
    return datos


@app.get("/resenas/{resena_id}", response_model=Resena, tags=["reseñas"])
def obtener(resena_id: int):
    if resena_id not in RESENAS:
        raise HTTPException(status_code=404, detail=f"Reseña {resena_id} no existe")
    return RESENAS[resena_id]


@app.post("/resenas", response_model=Resena, status_code=201, tags=["reseñas"])
def crear(nueva: ResenaIn):
    global _next_id
    resena = Resena(id=_next_id, **nueva.model_dump())
    RESENAS[resena.id] = resena
    _next_id += 1
    RESENAS_CREADAS.inc()
    return resena


# ---------------------------------------------------------------- observabilidad
@app.get("/observe/health", tags=["observabilidad"])
@app.get("/observe/health/live", tags=["observabilidad"])
def liveness():
    """Liveness: ¿el proceso está vivo? (Kubernetes lo reinicia si falla)"""
    return {"status": "UP", "servicio": SERVICE_NAME,
            "uptimeSegundos": round(time.time() - STARTED_AT)}


@app.get("/observe/health/ready", tags=["observabilidad"])
def readiness(response: Response):
    """Readiness: ¿puede atender tráfico? (Kubernetes deja de enviarle tráfico si falla)"""
    listo = os.getenv("FORZAR_NO_LISTO", "false").lower() != "true"
    if not listo:
        response.status_code = 503
    return {"status": "UP" if listo else "DOWN",
            "checks": [{"name": "datos-en-memoria", "status": "UP" if listo else "DOWN",
                        "data": {"resenas": len(RESENAS)}}]}


@app.get("/observe/metrics", tags=["observabilidad"])
def metrics():
    """Métricas en formato Prometheus (texto plano)."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
