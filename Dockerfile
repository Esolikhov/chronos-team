FROM python:3.12-slim
WORKDIR /service
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    groupadd --system chronos && useradd --system --gid chronos chronos
COPY app/ ./app/
RUN mkdir -p /service/data && chown chronos:chronos /service/data
USER chronos
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
