FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional): add any you need for scraping (e.g., libxml2/libxslt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    build-essential gcc \
    libxml2-dev libxslt1-dev libffi-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy backend code and requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/backend/requirements.txt

# Copy the rest of the project (backend + built frontend dist if present)
# Copy backend and built frontend
COPY backend /app/backend
COPY dist /app/dist

# Include the catalog CSV used by the scraper to derive targets
COPY ["Dzukou_Pricing_Overview_With_Names - Copy.csv", "/app/"]

# Ensure output directory exists inside the container (mounted via compose for persistence)
RUN mkdir -p /app/product_data

# Expose the port (Render/Heroku will provide PORT env var)
ENV PORT=8000
EXPOSE 8000

CMD ["sh","-lc","uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
