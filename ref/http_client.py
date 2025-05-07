import json
import random
import time

import requests

with open("../config.json", "r") as file:
    config = json.load(file)

THINGSBOARD_HOST = config["host"]
HTTP_PORT = config["http_port"]
CREDENTIALS_FILE = config["credentials_file"]
DEVICE_NAME = config["device_name"]

print(f"Host: {THINGSBOARD_HOST}")
print(f"Port: {HTTP_PORT}")
print(f"Credentials File: {CREDENTIALS_FILE}")
print(f"Device Name: {DEVICE_NAME}")

with open(CREDENTIALS_FILE, "r") as cred_file:
    ACCESS_TOKEN = cred_file.read().strip()

# URL để gửi telemetry (thêm HTTP_PORT)
url = f"http://{THINGSBOARD_HOST}:{HTTP_PORT}/api/v1/{ACCESS_TOKEN}/telemetry"

data = {"timestamp": time.time(), "values": {
    "temperature": round(random.uniform(20.0, 30.0), 2),
    "humidity": round(random.uniform(40.0, 60.0), 2),
    "status": "active"
}}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("Telemetry data sent successfully!")
else:
    print(f"Failed to send telemetry data: {response.text}")
