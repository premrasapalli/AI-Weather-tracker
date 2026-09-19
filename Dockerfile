# Use the official Python image as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source
COPY . .

# Non-root user for security hardening
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080

EXPOSE 8080

# Gunicorn with multiple workers + threads
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "3", "--threads", "2", "--timeout", "60", "app:app"]