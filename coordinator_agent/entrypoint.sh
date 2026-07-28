#!/bin/sh
python mqtt_subscriber.py &
exec python api.py
