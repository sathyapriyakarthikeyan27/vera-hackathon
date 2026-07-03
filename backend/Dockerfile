FROM python:3.11-slim

WORKDIR /app

# Install deps first (layer cached separately from source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium for the Playwright render path (gated/SPA sources). Installed to a
# world-readable shared path so the non-root user can launch it. Cached separately from
# source so code changes don't re-download the browser.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium && chmod -R a+rx /ms-playwright

COPY . .

# Create data dir for SQLite
RUN mkdir -p /app/data

# Run as non-root
RUN adduser --disabled-password --no-create-home verauser && \
    chown -R verauser:verauser /app
USER verauser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
