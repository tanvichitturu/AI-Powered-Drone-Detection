FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY detection_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY detection_agent/ .

RUN sed -i 's/broker: localhost/broker: mosquitto/' config.yaml

EXPOSE 8002

CMD ["python", "service.py"]
