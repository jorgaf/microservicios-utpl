# Guía: desplegar los 3 microservicios en Render

Esta guía despliega en [render.com](https://render.com) (plan gratuito) los tres servicios del repositorio:

| Servicio en Render | Carpeta | Tecnología | Puerto |
| --- | --- | --- | --- |
| `libros-service` | `libros-service-h27/` | Java 27 + Helidon 27 | 8081 |
| `resenas-service` | `resenas-service/` | Python 3.12 + FastAPI | 8082 |
| `gateway` | `gateway/` | Python 3.12 + FastAPI | 8080 |

Los tres se despliegan como **Web Service de tipo Docker**: Render construye la imagen con el
`Dockerfile` de cada carpeta, igual que `docker build` en local.

---

## 0. Requisitos

- Una cuenta en GitHub y otra en Render (puedes entrar a Render con tu cuenta de GitHub).
- El repositorio `microservicios-utpl` subido a GitHub. Puede ser público o privado.
- Opcional, pero recomendado: comprobar que todo funciona en local antes de subirlo:

  ```bash
  docker compose up --build
  curl http://localhost:8080/api/estado
  ```

### Subir el proyecto a GitHub (si aún no está)

```bash
cd microservicios-utpl
git init
git add .
git commit -m "Microservicios: libros (Helidon 27), reseñas y gateway"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/microservicios-utpl.git
git push -u origin main
```

> El `.gitignore` ya excluye `target/`, `__pycache__/` y `.venv/`. Render compila desde el código
> fuente, así que no hace falta subir el JAR.

---

## 1. Opción A (recomendada): Blueprint con `render.yaml`

El archivo `render.yaml` de la raíz describe los tres servicios. Render los crea todos de una vez.

1. En Render: **New → Blueprint**.
2. Conecta tu cuenta de GitHub, si te lo pide, y elige el repositorio `microservicios-utpl`.
3. Render lee `render.yaml` y muestra los tres servicios: `libros-service`, `resenas-service` y `gateway`.
4. Te pedirá dos variables marcadas con `sync: false`: **`LIBROS_URL`** y **`RESENAS_URL`**.
   Todavía no conoces esas URLs, así que escribe un valor temporal, por ejemplo `http://pendiente`.
5. Pulsa **Apply / Deploy Blueprint** y espera.
   - `resenas-service` y `gateway` tardan 1-3 min.
   - `libros-service` tarda más (5-10 min la primera vez), porque Maven descarga las dependencias
     y compila con Java 27.
6. Cuando los tres estén en **Live**, sigue con el [paso 3](#3-conectar-el-gateway-con-los-otros-dos-servicios).

Lo que ya trae configurado `render.yaml`:

| Servicio | `rootDir` | Health check | Variables |
| --- | --- | --- | --- |
| libros-service | `libros-service-h27` | `/observe/health` | `PORT=8081`, `SERVER_PORT=8081` |
| resenas-service | `resenas-service` | `/observe/health` | `PORT=8082` |
| gateway | `gateway` | `/observe/health` | `PORT=8080`, `LIBROS_URL`, `RESENAS_URL`, `TIMEOUT_SECONDS=60` |

---

## 2. Opción B: crear cada servicio a mano

Úsala si prefieres mostrar en clase cada paso, o si el Blueprint da problemas.
Repite estos pasos **tres veces**, una por servicio, en este orden: libros, reseñas y gateway.

1. **New → Web Service** → elige el repositorio `microservicios-utpl`.
2. Completa el formulario con los valores de esta tabla:

   | Campo | libros-service | resenas-service | gateway |
   | --- | --- | --- | --- |
   | Name | `libros-service` | `resenas-service` | `gateway` |
   | Language / Runtime | Docker | Docker | Docker |
   | Branch | `main` | `main` | `main` |
   | Root Directory | `libros-service-h27` | `resenas-service` | `gateway` |
   | Dockerfile Path | `./Dockerfile` | `./Dockerfile` | `./Dockerfile` |
   | Instance Type | Free | Free | Free |

3. En **Environment Variables** agrega:

   - libros-service: `PORT=8081` y `SERVER_PORT=8081`
   - resenas-service: `PORT=8082`
   - gateway: `PORT=8080`, `TIMEOUT_SECONDS=60`, `LIBROS_URL` y `RESENAS_URL` (ver el paso 3)

4. En **Advanced → Health Check Path** escribe `/observe/health`.
5. Pulsa **Deploy Web Service** y espera a que el estado sea **Live**.

¿Por qué dos variables de puerto en libros? Render envía el tráfico al puerto indicado en `PORT`.
Helidon no lee `PORT`: lee `server.port` de `application.yaml`, y la variable de entorno `SERVER_PORT`
lo sobrescribe. Los servicios Python leen `PORT` directamente en su `Dockerfile`.

---

## 3. Conectar el gateway con los otros dos servicios

En Render, los servicios gratuitos se comunican por sus **URLs públicas** (`https://...onrender.com`).

1. Abre `libros-service` en el panel de Render y copia su URL, por ejemplo
   `https://libros-service-ab12.onrender.com`.
2. Haz lo mismo con `resenas-service`.
3. Abre `gateway` → **Environment** y edita las variables:

   ```text
   LIBROS_URL  = https://libros-service-ab12.onrender.com
   RESENAS_URL = https://resenas-service-cd34.onrender.com
   ```

   Sin `/` al final. Si se te escapa, el gateway lo quita de todos modos.
4. Guarda los cambios. Render vuelve a desplegar el gateway (1-2 min).

---

## 4. Verificar el despliegue

Reemplaza las URLs por las tuyas:

```bash
LIBROS=https://libros-service-ab12.onrender.com
RESENAS=https://resenas-service-cd34.onrender.com
GATEWAY=https://gateway-ef56.onrender.com

curl $LIBROS/libros/1                   # Huasipungo
curl $LIBROS/observe/health             # 204 o UP
curl $RESENAS/resenas?libroId=1
curl $GATEWAY/api/estado                # libros y reseñas: UP
curl $GATEWAY/api/libros/1/detalle      # libro + reseñas + promedio
```

La documentación Swagger de reseñas queda en `$RESENAS/docs`.

### Configurar Bruno

Edita `bruno/microservicios-utpl/environments/Render.bru` con tus URLs:

```text
vars {
  librosUrl: https://libros-service-ab12.onrender.com
  resenasUrl: https://resenas-service-cd34.onrender.com
  gatewayUrl: https://gateway-ef56.onrender.com
}
```

Luego, en Bruno, elige el entorno **Render** y ejecuta las carpetas 1, 2 y 3.
Desde la terminal: `bru run --env Render`.

---

## 5. Antes de la clase: el plan gratuito duerme

- Un servicio gratuito **se duerme tras ~15 min sin tráfico**. La primera petición lo despierta y
  tarda unos 30-60 s. El de Java suele tardar un poco más.
- **5-10 minutos antes de la clase**, despierta los tres servicios: ejecuta en Bruno las carpetas 1-3,
  o lanza los `curl` del paso 4.
- El gateway tiene `TIMEOUT_SECONDS=60` justamente para esperar a que un servicio dormido despierte.
- Los datos están **en memoria**: cada vez que un servicio se reinicia o se duerme, los libros y las
  reseñas vuelven a los valores iniciales. Para una demo es una ventaja: siempre se empieza igual.

---

## 6. Experimento de fallo en Render (carpeta 4 de Bruno)

En local se hace con `docker compose stop resenas`. En Render:

1. Abre `resenas-service` → **Settings** → **Suspend Service**.
2. Ejecuta en Bruno la carpeta **4 experimento de fallo**:
   - `/api/libros/1/detalle` → 200 con `"degradado": true`
   - `/api/estado` → reseñas DOWN
   - `/api/resenas` → 503
3. Vuelve a activarlo con **Resume Service** y espera a que esté **Live**.

---

## 7. Actualizar el código

Cada `git push` a `main` vuelve a desplegar automáticamente los servicios afectados (*Auto-Deploy*).
Para forzar un despliegue: abre el servicio → **Manual Deploy → Deploy latest commit**.

---

## 8. Problemas frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| El build de libros falla con `manifest unknown` en la imagen de Maven | Imagen base inexistente | El `Dockerfile` debe usar `maven:3.10-eclipse-temurin-27`. `3.9` no existe para Java 27 |
| Error de compilación en `Config.global(...)` o en `Metrics.globalRegistry()` | Código de Helidon 4.x compilado con Helidon 27 | Revisa que `rootDir` sea `libros-service-h27` y que el código sea el de esa carpeta |
| El deploy queda en *In progress* y termina en *Failed: health check* | El puerto donde escucha el servicio no coincide con `PORT` | libros: `PORT` y `SERVER_PORT` deben tener el mismo valor. Python: solo `PORT` |
| `/api/estado` muestra libros o reseñas DOWN, pero cada servicio responde bien por separado | `LIBROS_URL` o `RESENAS_URL` mal escritas en el gateway | Revisa que usen `https://`, no lleven ruta y correspondan al servicio correcto |
| La primera petición tarda ~1 min o el gateway responde 504 | El servicio estaba dormido | Espera y repite. Despierta los servicios antes de la clase |
| Bruno falla todo en el entorno Render | Siguen las URLs `...-CAMBIAR...` | Edita `environments/Render.bru` (ver el paso 4) |

---

## Resumen

```text
GitHub (repo)
   │  push
   ▼
Render ── New → Blueprint (render.yaml)
   ├── libros-service   (Docker, libros-service-h27, Java 27)  → https://libros-service-xxxx.onrender.com
   ├── resenas-service  (Docker, Python)                       → https://resenas-service-xxxx.onrender.com
   └── gateway          (Docker, Python)                       → https://gateway-xxxx.onrender.com
         LIBROS_URL / RESENAS_URL = URLs públicas de los dos de arriba
```
