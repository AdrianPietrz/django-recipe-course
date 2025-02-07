FROM python:3.9
LABEL maintainer="ADRIAN"

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /tmp/requirements.txt
COPY ./app /app
WORKDIR /app
EXPOSE 8000

RUN python -m venv /py && \
    pip install --upgrade pip && \
    apt-get update && \
    apt-get update && \
    apt-get install --no-install-recommends -y \
      postgresql-client \
      build-essential \
      libpq-dev \
      musl-dev && \
    pip install -r /tmp/requirements.txt && \
    apt-get purge -y build-essential libpq-dev musl-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp