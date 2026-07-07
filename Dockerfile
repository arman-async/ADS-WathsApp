FROM python:3.13-slim

WORKDIR /service
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt --verbose
COPY app/ /service/app

CMD [ "python", "-m", "app" ]