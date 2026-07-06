FROM python:3.12-slim

WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /service/app

CMD [ "python", "-m", "app" ]