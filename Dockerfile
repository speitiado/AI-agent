FROM python:3.11-slim

WORKDIR /app

# Instalar Poetry
RUN pip install --no-cache-dir poetry

# --- INICIO DE LA CORRECCIÓN ---
# Configurar Poetry para que cree el .venv dentro de /app
RUN poetry config virtualenvs.in-project true
# --- FIN DE LA CORRECCIÓN ---

# Copiar archivos de Poetry primero (mejor cache de capas)
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias (ahora se crearán en /app/.venv)
RUN poetry install --no-root
RUN apt-get update && apt-get install -y git


# Copiar el código
COPY . .

CMD ["poetry", "run", "python", "agente.py"]



