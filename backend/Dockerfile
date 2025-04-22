FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl postgresql-client gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

#COPY requirements/dev.txt /app/
#COPY requirements/test.txt /app/
COPY requirements/prod.txt /app/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r prod.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]