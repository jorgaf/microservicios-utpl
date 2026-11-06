"""
gateway: API Gateway (Python + FastAPI + httpx).

Patrón API Gateway con dos responsabilidades:
  1. ENRUTAMIENTO: un único punto de entrada; reenvía /api/libros/** y /api/resenas/**
     al microservicio dueño de cada recurso.
  2. AGREGACIÓN: /api/libros/{id}/detalle consulta a AMBOS servicios y une la respuesta.
     Si reseñas no responde, devuelve el libro igual, marcado como "degradado".

El gateway no tiene lógica de negocio ni datos propios.
"""
import asyncio
import os
import time

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

SERVICE_NAME = "gateway"
LIBROS_URL = os.getenv("LIBROS_URL", "http://localhost:8081").rstrip("/")
RESENAS_URL = os.getenv("RESENAS_URL", "http://localhost:8082").rstrip("/")
# En Render (plan gratuito) un servicio dormido tarda en despertar: sube este valor allí.
TIMEOUT = float(os.getenv("TIMEOUT_SECONDS", "5"))

app = FastAPI(title="API Gateway", version="1.0.0",
              description="Punto de entrada único - Programación Integrativa UTPL")
client = httpx.AsyncClient(timeout=TIMEOUT)

UPSTREAM_CALLS = Counter("gateway_upstream_calls_total", "Llamadas a microservicios",
                         ["servicio", "resultado"])
DEGRADADAS = Counter("gateway_respuestas_degradadas_total",
                     "Respuestas agregadas entregadas sin todos los datos")


async def llamar(servicio: str, method: str, url: str, **kwargs) -> httpx.Response:
    try:
        r = await client.request(method, url, **kwargs)
        UPSTREAM_CALLS.labels(servicio, "ok" if r.status_code < 500 else "error").inc()
        return r
    except httpx.HTTPError:
        UPSTREAM_CALLS.labels(servicio, "no_disponible").inc()
        raise


def respuesta_de(r: httpx.Response) -> Response:
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"),
                    headers={"X-Upstream": r.headers.get("x-service", "?")})


def no_disponible(servicio: str) -> JSONResponse:
    return JSONResponse(status_code=503,
                        content={"error": f"{servicio} no está disponible", "servicio": servicio})


# ---------------------------------------------------------------- 2) AGREGACIÓN
# Se declara ANTES del enrutamiento genérico para que tenga prioridad.
@app.get("/api/libros/{libro_id}/detalle", tags=["agregación"])
async def detalle_libro(libro_id: int):
    """Une el libro (Java) con sus reseñas (Python) en una sola respuesta."""
    libro_req = llamar("libros", "GET", f"{LIBROS_URL}/libros/{libro_id}")
    resenas_req = llamar("resenas", "GET", f"{RESENAS_URL}/resenas", params={"libroId": libro_id})
    # Las dos llamadas se hacen EN PARALELO
    libro_res, resenas_res = await asyncio.gather(libro_req, resenas_req, return_exceptions=True)

    if isinstance(libro_res, Exception):
        return no_disponible("libros-service")
    if libro_res.status_code != 200:
        return respuesta_de(libro_res)  # p. ej. 404 si el libro no existe

    detalle = {"libro": libro_res.json(), "resenas": [], "degradado": False}
    if isinstance(resenas_res, Exception) or resenas_res.status_code != 200:
        detalle["degradado"] = True
        detalle["aviso"] = "resenas-service no respondió; se muestran datos parciales"
        DEGRADADAS.inc()
    else:
        resenas = resenas_res.json()
        detalle["resenas"] = resenas
        if resenas:
            detalle["promedio"] = round(sum(r["calificacion"] for r in resenas) / len(resenas), 2)
    return detalle


# ---------------------------------------------------------------- 1) ENRUTAMIENTO
async def reenviar(servicio: str, base: str, recurso: str, resto: str, request: Request):
    url = f"{base}/{recurso}" + (f"/{resto}" if resto else "")
    try:
        r = await llamar(servicio, request.method, url,
                         params=request.query_params,
                         content=await request.body(),
                         headers={"content-type": request.headers.get("content-type", "application/json")})
    except httpx.HTTPError:
        return no_disponible(f"{servicio}-service")
    return respuesta_de(r)


@app.api_route("/api/libros", methods=["GET", "POST"], tags=["enrutamiento"])
@app.api_route("/api/libros/{resto:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["enrutamiento"])
async def ruta_libros(request: Request, resto: str = ""):
    return await reenviar("libros", LIBROS_URL, "libros", resto, request)


@app.api_route("/api/resenas", methods=["GET", "POST"], tags=["enrutamiento"])
@app.api_route("/api/resenas/{resto:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["enrutamiento"])
async def ruta_resenas(request: Request, resto: str = ""):
    return await reenviar("resenas", RESENAS_URL, "resenas", resto, request)


# ---------------------------------------------------------------- estado y observabilidad
@app.get("/", tags=["info"])
def info():
    return {"servicio": SERVICE_NAME, "rutas": ["/api/libros", "/api/resenas",
            "/api/libros/{id}/detalle", "/api/estado"],
            "upstreams": {"libros": LIBROS_URL, "resenas": RESENAS_URL}}


@app.get("/api/estado", tags=["observabilidad"])
async def estado():
    """Consulta la salud de cada microservicio (útil para la demo de fallo)."""
    async def salud(nombre, base):
        t0 = time.perf_counter()
        try:
            r = await client.get(f"{base}/observe/health")
            ok = r.is_success          # cualquier 2xx (Helidon puede responder 204)
        except httpx.HTTPError:
            ok = False
        return nombre, {"status": "UP" if ok else "DOWN",
                        "ms": round((time.perf_counter() - t0) * 1000)}
    resultados = dict(await asyncio.gather(salud("libros-service", LIBROS_URL),
                                           salud("resenas-service", RESENAS_URL)))
    return {"gateway": "UP", "servicios": resultados}


@app.get("/observe/health", tags=["observabilidad"])
@app.get("/observe/health/live", tags=["observabilidad"])
@app.get("/observe/health/ready", tags=["observabilidad"])
def health():
    return {"status": "UP", "servicio": SERVICE_NAME}


@app.get("/observe/metrics", tags=["observabilidad"])
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
