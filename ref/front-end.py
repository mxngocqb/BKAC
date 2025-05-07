import tkinter as tk
from tkinter import messagebox
import requests
import json

# Thay thế bằng thông tin của bạn
THINGSBOARD_HOST = "http://18.142.251.211:8080"
jwt_token = None

def login():
    global jwt_token
    username = entry_username.get()
    password = entry_password.get()
    url_login = f"{THINGSBOARD_HOST}/api/auth/login"
    headers = {"Content-Type": "application/json"}
    data = {"username": username, "password": password}

    response = requests.post(url_login, json=data, headers=headers)
    if response.status_code == 200:
        jwt_token = response.json().get("token")
        messagebox.showinfo("Đăng nhập thành công", "JWT Token đã được lưu!")
    else:
        messagebox.showerror("Lỗi", f"Lỗi khi đăng nhập: {response.text}")

def get_devices():
    if not jwt_token:
        messagebox.showerror("Lỗi", "Bạn cần đăng nhập trước!")
        return
    url = f"{THINGSBOARD_HOST}/api/tenant/devices?pageSize=10&page=0"
    headers = {"X-Authorization": f"Bearer {jwt_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        devices = response.json().get("data", [])
        device_list.delete(0, tk.END)
        for device in devices:
            device_list.insert(tk.END, f"{device['name']} - ID: {device['id']['id']}")
    else:
        messagebox.showerror("Lỗi", f"Lỗi lấy danh sách thiết bị: {response.status_code}")

def get_device_id():
    global device_id_tmp
    device_name = entry_device_name.get()
    url = f"{THINGSBOARD_HOST}/api/tenant/devices?deviceName={device_name}"
    headers = {"X-Authorization": f"Bearer {jwt_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        device_id_tmp = response.json()["id"]["id"]
        label_device_id.config(text=f"Device ID: {device_id_tmp}")
    else:
        messagebox.showerror("Lỗi", "Không tìm thấy thiết bị!")

def send_rpc(method, rpc_type, params):
    if not jwt_token or not device_id_tmp:
        messagebox.showerror("Lỗi", "Hãy đăng nhập và chọn thiết bị trước!")
        return
    url_rpc = f"{THINGSBOARD_HOST}/api/rpc/{rpc_type}/{device_id_tmp}"
    headers = {"X-Authorization": f"Bearer {jwt_token}"}
    rpc_payload = {"method": method, "params": params}
    response = requests.post(url_rpc, headers=headers, json=rpc_payload)
    if response.status_code == 200:
        messagebox.showinfo("Thành công", "RPC gửi thành công!")
    else:
        messagebox.showerror("Lỗi", f"Lỗi gửi RPC: {response.text}")

# Tạo giao diện
root = tk.Tk()
root.title("ThingsBoard MQTT UI")
root.geometry("600x500")

# Cấu hình lưới để mở rộng cột
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

# Login
tk.Label(root, text="Username:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
entry_username = tk.Entry(root)
entry_username.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

tk.Label(root, text="Password:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
entry_password = tk.Entry(root, show="*")
entry_password.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

tk.Button(root, text="Đăng nhập", command=login, width=20).grid(row=2, column=0, columnspan=2, pady=10)

# Lấy danh sách thiết bị
tk.Button(root, text="Lấy danh sách thiết bị", command=get_devices, width=20).grid(row=3, column=0, columnspan=2, pady=10)
device_list = tk.Listbox(root, width=50)
device_list.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

# Nhập tên thiết bị để lấy ID
tk.Label(root, text="Tên thiết bị:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
entry_device_name = tk.Entry(root)
entry_device_name.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

tk.Button(root, text="Lấy ID", command=get_device_id, width=20).grid(row=6, column=0, columnspan=2, pady=10)
label_device_id = tk.Label(root, text="Device ID: ")
label_device_id.grid(row=7, column=0, columnspan=2, padx=10, pady=5)

# Gửi RPC
rpc_states = {}  # Dictionary để lưu trạng thái

rpc_states = {}  # Dictionary để lưu trạng thái

rpc_states = {}  # Dictionary để lưu trạng thái

def create_rpc_buttons(row):
    if row not in rpc_states:
        rpc_states[row] = False  # Mặc định là "inactive"

    def toggle_rpc_state():
        rpc_states[row] = not rpc_states[row]
        value = "active" if rpc_states[row] else "inactive"
        data = {"id": row, "value": value}  # Tạo object JSON hợp lệ
        send_rpc("oneWay", "oneway", data)

    def toggle_rpc_state_two_way():
        rpc_states[row] = not rpc_states[row]
        value = "active" if rpc_states[row] else "inactive"
        data = {"id": row, "value": value}  # Tạo object JSON hợp lệ
        send_rpc("twoWay", "twoway", data)

    tk.Button(root, text=f"RPC One-Way: {row}", command=toggle_rpc_state).grid(row=row, column=0)
    tk.Button(root, text=f"RPC Two-Way: {row}", command=toggle_rpc_state_two_way).grid(row=row, column=1)

# Tạo nút từ hàng 8 trở đi
for i in range(1):  # Có thể thay số 5 bằng số hàng động
    create_rpc_buttons(8 + i)

root.mainloop()
