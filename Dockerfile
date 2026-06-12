# Backend FastAPI — development image (uvicorn with --reload)
FROM python:3.12-slim

# Avoid .pyc files and force unbuffered stdout (logs show up immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first so this layer is cached unless requirements change.
# psycopg2-binary, bcrypt and cryptography ship prebuilt wheels, so slim is enough.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source. In dev this is overridden by the bind mount in docker-compose,
# but keeping it lets the image run standalone too.
COPY . .

EXPOSE 8000

# --reload watches the mounted source and restarts on change.
# --proxy-headers + --forwarded-allow-ips: behind ngrok (TLS terminates at the
# tunnel, traffic reaches uvicorn over HTTP), uvicorn must trust X-Forwarded-Proto
# so redirects and absolute URLs are built as https:// instead of http://.
# Without this, the trailing-slash 307 redirect points to http:// → mixed content.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--proxy-headers", "--forwarded-allow-ips", "*"]
