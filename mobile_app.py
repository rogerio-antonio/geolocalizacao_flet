import flet as ft
import time
from confluent_kafka import Producer
import json
import uuid

# Identificador único para este dispositivo
DEVICE_ID = str(uuid.uuid4())

def create kafka_producer():
    return Producer({
        'bootstrap.servers': 'seu-servidor-kafka:9092',
        'client.id': f'mobile-device-{DEVICE_ID}'
    })