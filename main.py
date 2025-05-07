import base64
import os
import json
import time
import random
import threading
import uuid
from datetime import datetime
from io import BytesIO
from tkinter import messagebox
import cv2
import face_recognition
import numpy as np
from PIL import Image

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from paho.mqtt.client import Client
from json import dumps, loads

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QMessageBox
)
from datetime import datetime

from database import UserScheduleDB

RESULT_CODES = {
    1: "incorrect protocol version",
    2: "invalid client identifier",
    3: "server unavailable",
    4: "bad username or password",
    5: "not authorised",
}

device_state = {"status": "inactive"}
door_state = "close"
cam_status = "active"
rfid_status = "active"
finger_printer_status = "active"
door_status = "active"


def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)


class ProvisionClient(Client):
    def __init__(self, config, db_handler):
        super().__init__()
        self._host = config["host"]
        self._port = config["port"]
        self._username = "provision"
        self.db_handler = db_handler
        self.on_connect = self.__on_connect
        self.on_message = self.__on_message
        self.__provision_request = {
            "provisionDeviceKey": config["provision_device_key"],
            "provisionDeviceSecret": config["provision_device_secret"],
        }

        self.__provision_request["deviceName"] = "0d:a2:13:3a:31:33"
        self.__provision_request["deviceLabel"] = "12312"
        self.provision_request_topic = config["provision_request_topic"]
        self.provision_response_topic = config["provision_response_topic"]
        self.attribute_topic = config["attribute_topic"]
        self.telemetry_topic = config["telemetry_topic"]
        self.rpc_topic = "v1/devices/me/rpc/request/+"

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[Provisioning client] Connected to ThingsBoard")
            client.subscribe(self.provision_response_topic)
            client.subscribe(self.rpc_topic)
            provision_request = dumps(self.__provision_request)
            client.publish(self.provision_request_topic, provision_request)
        else:
            print(f"[Provisioning client] Cannot connect! Result: {RESULT_CODES.get(rc, 'Unknown error')}")

    def __on_message(self, client, userdata, msg):
        decoded_payload = msg.payload.decode("UTF-8")
        print(f"[Provisioning client] Received: {decoded_payload}")
        decoded_message = loads(decoded_payload)

        if msg.topic.startswith("v1/devices/me/rpc/request/"):
            self.__handle_rpc(client, msg.topic, decoded_message)
            return

        if decoded_message.get("status") == "SUCCESS":
            self.__save_credentials(decoded_message["credentialsValue"])
        else:
            print(f"[Provisioning client] Provisioning failed: {decoded_message.get('errorMsg', 'Unknown error')}")
        self.disconnect()

    def __handle_rpc(self, client, topic, message):
        global device_state
        print(f"[RPC] Received: {message}")

        method = message.get("method")
        params = message.get("params", {})

        print(f"[RPC] Received: {method} {params}")

        if method in ["oneWay", "twoWay"]:
            new_state = params.get("value")
            if new_state in ["active", "inactive"]:
                device_state["status"] = new_state
                print(f"[RPC] Device state changed to: {device_state['status']}")
            if method == "twoWay":
                response_topic = topic.replace("request", "response")
                response_msg = dumps(device_state)
                client.publish(response_topic, response_msg)
        elif method == "getState":
            response_topic = topic.replace("request", "response")
            response_msg = dumps(device_state)
            client.publish(response_topic, response_msg)
        elif method == "userSchedule":
            try:
                self.db_handler.insert_user_schedule(params)
                response_msg = json.dumps({"response": "ok"})
            except Exception as e:
                print(f"[DB Error] Failed to insert schedule: {e}")
                response_msg = json.dumps({"response": "error", "details": str(e)})

            response_topic = topic.replace("request", "response")
            client.publish(response_topic, response_msg)

    def provision(self):
        print("[Provisioning client] Connecting to ThingsBoard...")
        self.__clean_credentials()
        self.connect(self._host, self._port, 60)
        self.loop_forever()

    def get_new_client(self):
        credentials = self.__get_credentials()
        if credentials:
            new_client = Client()
            new_client.username_pw_set(credentials)
            new_client.on_message = self.__on_message
            return new_client
        return None

    @staticmethod
    def __get_credentials():
        try:
            with open("credentials", "r") as cred_file:
                return cred_file.read().strip()
        except FileNotFoundError:
            return None

    @staticmethod
    def __save_credentials(credentials):
        with open("credentials", "w") as cred_file:
            cred_file.write(credentials)

    @staticmethod
    def __clean_credentials():
        if os.path.exists("credentials"):
            os.remove("credentials")


def on_tb_connected(client, userdata, flags, rc):
    if rc == 0:
        print("[ThingsBoard client] Connected with credentials.")
        client.subscribe("v1/devices/me/rpc/request/+")
    else:
        print(f"[ThingsBoard client] Cannot connect! Result: {RESULT_CODES.get(rc, 'Unknown error')}")


def send_telemetry(client, topic):
    """Send sensor data in the background."""
    while True:
        telemetry_data = {
            "status":
                {
                    "timestamp": time.time(),
                    "cam_status": cam_status,
                    "rfid_status": rfid_status,
                    "finger_printer_status": finger_printer_status,
                    "door_status": door_state,
                },
        }
        telemetry_json = dumps(telemetry_data)
        client.publish(topic, telemetry_json)
        print(f"[Telemetry] Sent: {telemetry_json}")
        time.sleep(5)  # Send every 5 seconds


class DoorSimulator(QWidget):
    def __init__(self, client, attribute, telemetry, db_handler):
        super().__init__()
        self.client = client
        self.attribute = attribute
        self.telemetry = telemetry
        self.db_handler = db_handler
        self.camera = cv2.VideoCapture(0)  # Open the webcam
        self.last_match_time = 0  # Initialize to 0 or time.time() if you prefer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera_feed)
        self.timer.start(300)  # Update every 30ms
        self.init_ui()

    def init_ui(self):

        global rfid_status
        global finger_printer_status
        global door_status
        self.setWindowTitle("Door Simulator")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera_label = QLabel("Camera feed will appear here.")
        layout.addWidget(self.camera_label)

        self.door_button = QPushButton("Door: Closed")
        self.door_button.clicked.connect(self.toggle_door)
        layout.addWidget(self.door_button)

        self.cam_button = QPushButton("Camera: Active")
        self.cam_button.clicked.connect(self.toggle_cam)
        layout.addWidget(self.cam_button)

        self.finger_button = QPushButton("Finger Printer: Active")
        self.finger_button.clicked.connect(self.toggle_finger_printer)
        layout.addWidget(self.finger_button)

        self.rfid_button = QPushButton("RFID: Active")
        self.rfid_button.clicked.connect(self.toggle_rfid)
        layout.addWidget(self.rfid_button)

        self.label = QLabel("Enter Identify Number:")
        layout.addWidget(self.label)

        self.identify_input = QLineEdit()
        layout.addWidget(self.identify_input)

        self.check_button = QPushButton("Verify")
        self.check_button.clicked.connect(self.check_identify_number)
        layout.addWidget(self.check_button)

        self.setLayout(layout)

    def update_camera_feed(self):
        list_user = self.db_handler.get_all_user_schedules()

        # Read the frame from the camera
        ret, frame = self.camera.read()
        if ret:
            # Convert the frame to RGB (as face_recognition works with RGB images)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Get face locations and encodings from the camera frame
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            # Iterate over the list of users
            for user in list_user:
                # Decode the base64 face image and convert it to a PIL image
                face_image = Image.open(BytesIO(base64.b64decode(user["face_image"])))
                user_face_encoding = face_recognition.face_encodings(np.array(face_image))

                # Check if there is a match between the user face and the detected faces in the frame
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    try:
                        distance = face_recognition.face_distance(user_face_encoding, face_encoding)
                        confidence = (1 - distance) * 100  # Confidence as percentage

                        current_time = time.time()
                        if confidence > 65:
                            print(f"Face matched with user: {user['username']}")

                            # Optionally draw a box around the matched face
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                            # Update the last match time
                            if current_time - self.last_match_time > 10:
                                timestamp = datetime.now().isoformat()
                                payload = {
                                    "entry_exit_history": {
                                        "timestamp": timestamp,
                                        "user_id": user["user_id"],
                                        "id": str(uuid.uuid4()),
                                    }
                                }
                                self.client.publish(self.telemetry, json.dumps(payload))
                                print(f"[Telemetry] Sent: {json.dumps(payload)}")
                                self.toggle_door()
                                # after 10s do toggle again but not back process
                                QTimer.singleShot(10000, self.toggle_door)

                                self.last_match_time = current_time
                    except Exception as e:
                        print(f"[Exception] {e}")

            # Convert the frame back to a format suitable for PyQt
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.camera_label.setPixmap(pixmap)


    def toggle_door(self):
        global door_state
        if door_state == "open":
            door_state= "close"
            self.door_button.setText("Door: Closed")
        else:
            door_state = "open"
            self.door_button.setText("Door: Opened")

    def toggle_cam(self):
        global cam_status
        if cam_status == "active":
            cam_status= "inactive"
            self.cam_button.setText("Camera: Inactive")
        else:
            cam_status = "active"
            self.cam_button.setText("Camera: Active")

    def toggle_finger_printer(self):
        global finger_printer_status
        if finger_printer_status == "active":
            finger_printer_status = "inactive"
            self.finger_button.setText("Finger Printer: Inactive")
        else:
            finger_printer_status = "active"
            self.finger_button.setText("Finger Printer: Active")

    def toggle_rfid(self):
        global rfid_status
        if rfid_status == "active":
            rfid_status = "inactive"
            self.rfid_button.setText("RFID: Inactive")
        else:
            rfid_status = "active"
            self.rfid_button.setText("RFID: Active")


    def check_identify_number(self):
        identify_number = self.identify_input.text().strip()
        users = self.db_handler.get_user_schedule_by_id(identify_number)

        if users:
            timestamp = datetime.now().isoformat()
            payload = {
                "entry_exit_history": {
                    "timestamp": timestamp,
                    "user_id": users["user_id"],
                    "id":  str(uuid.uuid4()),
                }
            }
            self.client.publish(self.telemetry, json.dumps(payload))
            print(f"[Telemetry] Sent: {json.dumps(payload)}")
            QMessageBox.information(self, "Success", f"User {users['username']} entry recorded.")
            self.toggle_door()
            # after 10s do toggle again but not back process
            QTimer.singleShot(10000, self.toggle_door)

        else:
            QMessageBox.warning(self, "Not Found", "Identify number not found.")


def run_app(client, attribute, telemetry, db_handler):
    app = QApplication(sys.argv)
    window = DoorSimulator(client, attribute, telemetry, db_handler)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    config = load_config()
    db_handler = UserScheduleDB()
    provision_client = ProvisionClient(config, db_handler)
    tb_client = provision_client.get_new_client()

    if tb_client is None:
        provision_client.provision()
        tb_client = provision_client.get_new_client()

    if tb_client:
        tb_client.on_connect = on_tb_connected
        tb_client.connect(config["host"], config["port"], config["mqtt_keepalive"])
        tb_client.loop_start()

        # Start telemetry sending in background
        threading.Thread(target=send_telemetry, args=(tb_client, config["telemetry_topic"]), daemon=True).start()

        # Start the GUI
        # setup_gui(tb_client, config["attribute_topic"], config["telemetry_topic"], db_handler)
        run_app(tb_client, config["attribute_topic"], config["telemetry_topic"], db_handler)
        # Keep the main thread alive to maintain the connection
        while True:
            time.sleep(1)
    else:
        print("Client was not created!")
