FROM python:3.13-slim

WORKDIR /app

# Dependencias del proyecto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto al contenedor
COPY . .

# Puerto de FastAPI
EXPOSE 8000

# Arrancar el servidor web de la API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]