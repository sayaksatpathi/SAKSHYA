FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ backend/
COPY trust_service/ trust_service/
COPY models/ models/
COPY scripts/ scripts/
COPY .env.example .env.example

# Create storage directories
RUN mkdir -p storage/evidence storage/exports storage/temp

# Expose ports
EXPOSE 8000 8001

# Default command — run the backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
