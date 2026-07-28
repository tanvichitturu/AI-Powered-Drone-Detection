FROM python:3.11-slim

WORKDIR /app

COPY threat_agent/requirements.txt threat_agent/requirements.txt
COPY prediction_agent/requirements.txt prediction_agent/requirements.txt

RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r threat_agent/requirements.txt -r prediction_agent/requirements.txt

COPY threat_agent/ threat_agent/
COPY prediction_agent/ prediction_agent/

RUN sed -i 's/broker: "localhost"/broker: "mosquitto"/' threat_agent/config.yaml

WORKDIR /app/threat_agent

CMD ["python", "service.py"]
