FROM python:3.11-slim

WORKDIR /app

# Install deps first (layer cached separately from source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data dir for SQLite
RUN mkdir -p /app/data

# Run as non-root
RUN adduser --disabled-password --no-create-home verauser && \
    chown -R verauser:verauser /app
USER verauser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
