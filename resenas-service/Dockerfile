FROM python:3.12-slim

WORKDIR /app

# 1) Primero las dependencias: Docker cachea esta capa mientras requirements.txt no cambie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Luego el código
COPY app ./app

# Render inyecta la variable PORT; en local usamos 8082
ENV PORT=8082
EXPOSE 8082

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
