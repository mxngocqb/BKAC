import paho.mqtt.client as mqtt
import json
import time

# MQTT Server Parameters
MQTT_CLIENT_ID = "ESP32_weather"
MQTT_BROKER = "18.142.251.211"
MQTT_PORT = 1883
MQTT_USER = "nyazmorbx0axvf69na0g"
MQTT_PASSWORD = "28rd13yt6uw6nrrz2x7z"

MQTT_RPC_REQUEST_TOPIC = "v1/devices/me/rpc/request/"
MQTT_RPC_RESPONSE_TOPIC = "v1/devices/me/rpc/response/+"

subscribed = False  # Biến kiểm tra đã subscribe hay chưa


# Callback khi kết nối thành công
def on_connect(client, userdata, flags, rc):
    global subscribed
    if rc == 0:
        if not subscribed:
            client.subscribe(MQTT_RPC_RESPONSE_TOPIC)
            print(f" Subscribed to {MQTT_RPC_RESPONSE_TOPIC}")
            subscribed = True  # Đánh dấu đã subscribe

        # Gửi yêu cầu RPC lấy thời gian hiện tại
        request_id = int(time.time())  # Tạo request_id dựa trên timestamp
        request = {
            "method": "getCurrentTime",
            "params": {}
        }
        topic = MQTT_RPC_REQUEST_TOPIC + str(request_id)
        payload = json.dumps(request)

        client.publish(topic, payload)
        print(f" Sent RPC request: Topic: {topic}  Payload: {payload}")
    else:
        print(f" Failed to connect, return code {rc}")


# Callback khi nhận được phản hồi từ MQTT broker
def on_message(client, userdata, msg):
    print(f"📩 Received message on topic: {msg.topic}")
    try:
        response = json.loads(msg.payload.decode())  # Giải mã JSON
        print(f"🔹 Response: {response}")
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON response: {msg.payload.decode()}")


client = mqtt.Client(client_id=MQTT_CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

# Gán callback
client.on_connect = on_connect
client.on_message = on_message

# Kết nối đến MQTT broker
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Vòng lặp lắng nghe sự kiện
client.loop_forever()
