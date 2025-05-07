import time
import json
import random
import threading
import tkinter as tk
import paho.mqtt.client as mqtt

# MQTT Server Parameters
MQTT_CLIENT_ID = "ESP32_weather"
MQTT_BROKER = "18.142.251.211"
MQTT_USER = "nyazmorbx0axvf69na0g"
MQTT_PASSWORD = "28rd13yt6uw6nrrz2x7z"
MQTT_TOPIC = "v1/devices/me/telemetry"
MQTT_RPC_TOPIC = "v1/devices/me/rpc/request/+"
MQTT_ATTRIBUTES_TOPIC = "v1/devices/me/attributes"  # New attributes topic

# Global variable to keep track of the LED state on GPIO19
gpio19_state = False  # Initial state OFF

class MQTTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MQTT LED & Sensor Telemetry")
        self.geometry("400x250")

        # UI Elements
        self.led_label = tk.Label(self, text="LED GPIO19: OFF", font=("Arial", 14))
        self.led_label.pack(pady=10)

        self.sensor_label = tk.Label(self, text="Temperature: -- °C, Humidity: -- %", font=("Arial", 12))
        self.sensor_label.pack(pady=10)

        self.toggle_button = tk.Button(self, text="Toggle LED", font=("Arial", 12), command=self.toggle_led)
        self.toggle_button.pack(pady=10)

        # Variables to store sensor values for UI update
        self.current_temperature = None
        self.current_humidity = None

        # Setup MQTT Client
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        try:
            self.client.connect(MQTT_BROKER, 1883, 60)
        except Exception as e:
            print("MQTT Connection error:", e)

        # Start the MQTT network loop in a separate thread
        self.client.loop_start()

        # Start the telemetry publishing thread
        self.telemetry_thread = threading.Thread(target=self.publish_telemetry, daemon=True)
        self.telemetry_thread.start()

        # Begin periodic UI updates
        self.update_ui()

    # MQTT Callbacks
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(MQTT_RPC_TOPIC)
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        global gpio19_state
        print(f"Received RPC Message: {msg.topic} -> {msg.payload.decode()}")
        try:
            data = json.loads(msg.payload.decode())
            method = data.get("method")
            params = data.get("params", {})

            if method == "setState":
                device_id = params.get("id")
                value = params.get("value")
                if device_id == 1:
                    gpio19_state = bool(value)
                    print(f"GPIO19 {'ON' if gpio19_state else 'OFF'}")
            elif method == "getState":
                response_topic = msg.topic.replace("request", "response")
                response_msg = json.dumps(gpio19_state).encode("utf-8")
                client.publish(response_topic, response_msg)
                print(f"Sent getState Response: {response_msg}")
        except Exception as e:
            print(f"Error processing RPC: {e}")

    def toggle_led(self):
        global gpio19_state
        # Toggle the LED state
        gpio19_state = not gpio19_state
        print("Toggled LED to", "ON" if gpio19_state else "OFF")

        # Publish the new LED state as telemetry
        # telemetry_data = json.dumps({"led_state": gpio19_state})
        # self.client.publish(MQTT_TOPIC, telemetry_data)
        # print("Published telemetry:", telemetry_data)

        # Additionally, send the LED state as a device attribute
        attributes_data = json.dumps({"GPIO19": gpio19_state})
        self.client.publish(MQTT_ATTRIBUTES_TOPIC, attributes_data)
        print("Published attributes:", attributes_data)

    def publish_telemetry(self):
        # This function simulates DHT22 sensor readings and publishes them every 5 seconds
        while True:
            temperature = round(random.uniform(20.0, 30.0), 1)  # Simulated temperature (°C)
            humidity = round(random.uniform(30.0, 70.0), 1)     # Simulated humidity (%)
            telemetry_payload = json.dumps({
                "temp": temperature,
                "humidity": humidity
            })
            self.client.publish(MQTT_TOPIC, telemetry_payload)
            print("Published telemetry:", telemetry_payload)

            # Store sensor values for UI update
            self.current_temperature = temperature
            self.current_humidity = humidity

            time.sleep(5)

    def update_ui(self):
        # Update LED state label
        self.led_label.config(text=f"LED GPIO19: {'ON' if gpio19_state else 'OFF'}")
        # Update sensor telemetry label if available
        if self.current_temperature is not None and self.current_humidity is not None:
            self.sensor_label.config(
                text=f"Temperature: {self.current_temperature} °C, Humidity: {self.current_humidity} %")
        # Schedule the next UI update after 1 second
        self.after(1000, self.update_ui)

    def on_closing(self):
        # Cleanup MQTT and close the UI properly
        self.client.loop_stop()
        self.client.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = MQTTApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
