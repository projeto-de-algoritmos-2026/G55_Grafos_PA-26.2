# Imagem do SeamCarver: backend FastAPI servindo o frontend estatico.
FROM python:3.9-slim

WORKDIR /app

# Dependencias primeiro, para aproveitar o cache de camadas do Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY assets ./assets
COPY cli.py .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
