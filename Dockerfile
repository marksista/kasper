FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir prometheus-client
COPY microservice.py .
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["python", "microservice.py"]
