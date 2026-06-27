import json
import paho.mqtt.client as mqtt
import requests

# FastAPI endpoint to forward alerts to
API_URL = "http://localhost:8000/alerts"

BROKER = "localhost"
PORT = 1883
TOPIC = "drone/threat_alerts"

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT] Connected with result code {reason_code}")
    client.subscribe(TOPIC)
    print(f"[MQTT] Subscribed to topic: {TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] Received alert: {payload}")
        
        # Forward to FastAPI Coordinator
        # Expecting a list of alerts
        alerts = payload if isinstance(payload, list) else [payload]
        
        response = requests.post(API_URL, json=alerts)
        
        if response.status_code == 200:
            print(f"[MQTT] Alert forwarded to Coordinator successfully")
            print(f"[MQTT] Coordinator response: {response.json()}")
        else:
            print(f"[MQTT] Failed to forward alert: {response.status_code}")
    
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")

def start_subscriber():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"[MQTT] Connecting to broker at {BROKER}:{PORT}...")
    client.connect(BROKER, PORT, 60)
    
    print("[MQTT] Listening for threat alerts...")
    client.loop_forever()

if __name__ == "__main__":
    start_subscriber()