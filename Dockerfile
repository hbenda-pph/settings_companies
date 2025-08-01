FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app 