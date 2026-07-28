FROM python:3.11-slim

WORKDIR /app

COPY coordinator_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY coordinator_agent/ .

RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
