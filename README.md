# Microservicios en la práctica — Programación Integrativa (UTPL)

Mini biblioteca con dos microservicios en lenguajes distintos y un API Gateway.

```
                 ┌──────────────────────────┐
  Bruno  ──────▶ │  gateway  :8080 (Python) │
                 │  enruta + agrega         │
                 └─────┬──────────────┬─────┘
                       │              │
          ┌────────────▼───┐   ┌──────▼─────────────┐
          │ libros-service │   │ resenas-service    │
          │ :8081 Java     │   │ :8082 Python       │
          │ Helidon        │   │ FastAPI            │
          └────────────────┘   └────────────────────┘
```

| Carpeta | Qué es |
| --- | --- |
| `libros-service-h27/` | Catálogo de libros. Java 27 + **Helidon 27** |
| `resenas-service/` | Reseñas. Python 3.12 + FastAPI |
| `gateway/` | API Gateway: enrutamiento + agregación + tolerancia a fallos |
| `bruno/microservicios-utpl/` | Colección de Bruno con 22 peticiones y 44 tests |
| `docker-compose.yml` | Levanta todo en local |
| `render.yaml` | Blueprint para desplegar los 3 servicios en Render |
| `docs/k8s-libros.yaml` | Ejemplo de Deployment con liveness/readiness probes |
| `docs/despliegue-render.md` | Guía paso a paso para desplegar en Render |

## Arranque rápido

```bash
docker compose up --build        # primera vez: 3-5 min (Maven descarga dependencias)
```

Luego, en Bruno: **Open Collection** → `bruno/microservicios-utpl` → entorno **Local** → ejecutar carpetas 1, 2, 3.
Para la carpeta 4: `docker compose stop resenas`, ejecutarla, y `docker compose start resenas`.

Sin Docker:

```bash
cd libros-service-h27 && mvn package && java -jar target/libros-service.jar
cd resenas-service && pip install -r requirements.txt && uvicorn app.main:app --port 8082
cd gateway && pip install -r requirements.txt && uvicorn app.main:app --port 8080
```

## Endpoints

| Servicio | Endpoint | Descripción |
| --- | --- | --- |
| libros | `GET/POST /libros`, `GET /libros/{id}` | CRUD básico |
| reseñas | `GET/POST /resenas`, `GET /resenas?libroId=1` | CRUD básico; Swagger en `/docs` |
| gateway | `/api/libros/**`, `/api/resenas/**` | Enrutamiento |
| gateway | `GET /api/libros/{id}/detalle` | Agregación (libro + reseñas + promedio) |
| gateway | `GET /api/estado` | Salud de cada servicio |
| todos | `/observe/health`, `/observe/health/live`, `/observe/health/ready` | Salud |
| todos | `/observe/metrics` | Métricas Prometheus |

Los tres servicios usan las mismas rutas de observabilidad que Helidon (`/observe/...`): un
"contrato" común que Kubernetes, Prometheus o el gateway pueden consumir sin importar el lenguaje.

## Despliegue en Render

Guía paso a paso: [`docs/despliegue-render.md`](docs/despliegue-render.md).

## Nota sobre Helidon 27

`libros-service-h27/` está verificado con **Helidon 27.0.0 + Java 27** (compila, arranca, pasa los
endpoints y construye la imagen Docker). Si vienes de Helidon 4.x, cambiaron tres llamadas:

| Para… | Helidon 4.5 | Helidon 27 |
| --- | --- | --- |
| Config global | `Config.global(config)` | `Services.set(Config.class, config)` |
| Registro de métricas | `Metrics.globalRegistry()` | `Services.get(MeterRegistry.class)` |
| Crear un contador | `Counter.builder(...)` | `MetricsFactory.getInstance().counterBuilder(...)` |

La imagen de compilación es `maven:3.10-eclipse-temurin-27` (no existe `maven:3.9-...-27`).

## Guion sugerido (60 min)

| Min | Bloque | Material |
| --- | --- | --- |
| 0–5 | ¿Qué es un microservicio? Monolito vs. micro | Diagrama de arriba |
| 5–20 | Parte 1: `libros-service` en Helidon → `docker build` → `docker run` → probar | `libros-service-h27/`, carpeta Bruno 1 |
| 20–30 | Parte 2: reseñas en Python, cada servicio por separado: datos, salud, métricas | carpeta Bruno 2, `/docs` |
| 30–40 | Gateway: enrutamiento + agregación; experimento de fallo | carpetas Bruno 3 y 4 |
| 40–45 | Puente a Kubernetes: probes y réplicas | `docs/k8s-libros.yaml` |
| 45–55 | Práctica de los estudiantes contra Render | Guía del estudiante |
| 55–60 | Cierre: gRPC y mensajería como siguiente paso; preguntas | — |

Plan B: imágenes ya construidas (`docker build` antes de la clase) y video corto de cada paso.

## Bruno y los tests de Postman

Bruno importa colecciones de Postman (**Import Collection → Postman**) y traduce automáticamente la
mayoría de los scripts `pm.*` (`pm.test`, `pm.expect`, `pm.response.json()`…). Lo que no traduce queda
comentado para revisarlo a mano. Esta colección ya está escrita en el formato nativo de Bruno:

```js
test("responde 200", function() {
  expect(res.getStatus()).to.equal(200);
});
```

Desde la terminal: `npm i -g @usebruno/cli` y luego, dentro de `bruno/microservicios-utpl`,
`bru run --env Local` (útil para CI).
