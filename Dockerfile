FROM python:3.11

WORKDIR /app

# Installer les outils de build de base au cas où
RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force l'installation explicite de pronotepy pour éviter tout oubli
RUN pip install --no-cache-dir pronotepy

COPY . .

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]
