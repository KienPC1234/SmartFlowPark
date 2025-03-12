import sys
import os
import json
import threading
import random
import string
import base64
import cv2
import numpy as np
import time
from flask import Flask, request, jsonify
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget, QDialog, QCheckBox, QMessageBox, QFileDialog, QListWidgetItem, QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
import secrets

# ---------------- Random Generator ----------------
class RandomGenerator:
    @staticmethod
    def generate_key(length=16):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    @staticmethod
    def generate_name(length=8):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# ---------------- Global variables cho Flask API ----------------
connected_clients = {}
default_key = RandomGenerator.generate_key(16)
default_name = RandomGenerator.generate_name(8)
client_id = f"{default_key}_{default_name}"
# Ban đầu với thông tin mặc định, thêm các trường last_request và delay
connected_clients[client_id] = {
    'key': default_key,
    'name': default_name,
    'people_count': 0,
    'image': None,
    "last_request": None,
    "delay": 0
}

# ---------------- Settings Manager ----------------
class SettingsManager:
    def __init__(self, filename="setting.json"):
        self.filename = filename
        self.data = {"server": {"ip": "127.0.0.1", "port": 8080}, "accounts": [], "zones": []}
        self.load()
    def load(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.save()
        else:
            self.save()
    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)
    def add_account(self, account):
        self.data["accounts"].append(account)
        self.save()
    def update_account(self, index, account):
        self.data["accounts"][index] = account
        self.save()
    def add_zone(self, zone):
        self.data["zones"].append(zone)
        self.save()
    def update_zone(self, index, zone):
        self.data["zones"][index] = zone
        self.save()

# ---------------- Monitor Manager ----------------
class MonitorManager:
    def __init__(self, filename="giamsat.json"):
        self.filename = filename
        self.data = {"monitors": []}
        self.load()
    def load(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.save()
        else:
            self.save()
    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)
    def add_monitor(self, monitor):
        self.data["monitors"].append(monitor)
        self.save()
    def update_monitor(self, index, monitor):
        self.data["monitors"][index] = monitor
        self.save()

# ---------------- Flask Server ----------------
class FlaskServer:
    def __init__(self, settings_manager, monitor_manager):
        self.settings_manager = settings_manager
        self.monitor_manager = monitor_manager
        self.app = Flask(__name__)
        self.tokens = {}  # Lưu token: {token: {"username": "...", "permissions": [...], "expiry": timestamp}}
        self.register_routes()

    def _is_valid_client(self, key, name):
        """Kiểm tra xem key và name có hợp lệ (tồn tại trong monitor_manager) không."""
        print(f"[DEBUG] Checking key={key}, name={name} against monitors: {self.monitor_manager.data.get('monitors', [])}")
        for monitor in self.monitor_manager.data.get("monitors", []):
            monitor_key = monitor.get("key")
            monitor_name = monitor.get("name")
            if monitor_key == key and monitor_name == name:
                print(f"[DEBUG] Found valid client: key={key}, name={name}")
                return True
        print(f"[DEBUG] No match found for key={key}, name={name}")
        return False

    def _check_auth(self, token, required_permission=None):
        """Kiểm tra token và quyền truy cập."""
        if token not in self.tokens:
            return False, "Invalid or expired token"
        user_info = self.tokens[token]
        # Kiểm tra thời hạn token (8 giờ = 28800 giây)
        if time.time() > user_info["expiry"]:
            del self.tokens[token]  # Xóa token hết hạn
            return False, "Token has expired"
        if required_permission and required_permission not in user_info["permissions"]:
            return False, f"Permission '{required_permission}' required"
        return True, user_info["username"]

    def register_routes(self):
        @self.app.route('/login', methods=['POST'])
        def login():
            data = request.get_json(silent=True)
            if not data or "username" not in data or "password" not in data:
                return jsonify({"status": "ERROR", "message": "Username and password required"}), 400
            
            username = data["username"]
            password = data["password"]
            for account in self.settings_manager.data["accounts"]:
                if account["username"] == username and account["password"] == password:
                    token = secrets.token_hex(16)
                    self.tokens[token] = {
                        "username": username,
                        "permissions": account.get("permissions", []),
                        "expiry": time.time() + 28800  # 8 giờ sau
                    }
                    print(f"[INFO] User {username} logged in, token={token}, expires at {self.tokens[token]['expiry']}")
                    return jsonify({"status": "OK", "token": token}), 200
            
            print(f"[ERROR] Login failed for username={username}")
            return jsonify({"status": "ERROR", "message": "Invalid credentials"}), 401

        @self.app.route('/app', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def manage_app():
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"status": "ERROR", "message": "Authorization token required"}), 401
            
            is_valid, message = self._check_auth(token)
            if not is_valid:
                return jsonify({"status": "ERROR", "message": message}), 403
            
            data_type = request.args.get('type')
            if not data_type or data_type not in ['monitors', 'zones', 'accounts']:
                return jsonify({"status": "ERROR", "message": "Invalid type parameter"}), 400
            
            required_permission = 'monitor' if data_type == 'monitors' else 'zone' if data_type == 'zones' else 'home'
            is_valid, message = self._check_auth(token, required_permission)
            if not is_valid:
                return jsonify({"status": "ERROR", "message": message}), 403

            if request.method == 'GET':
                now = time.time()
                THRESHOLD = 15.0
                if data_type == 'monitors':
                    real_time_monitors = []
                    for monitor in self.monitor_manager.data["monitors"]:
                        client_id = f"{monitor.get('key', '')}_{monitor.get('name', '')}"
                        client = connected_clients.get(client_id, {})
                        status = "OK" if client and (now - client.get("last_request", 0)) <= THRESHOLD else "ERROR"
                        real_time_monitor = {
                            "name": monitor.get("name", ""),
                            "key": monitor.get("key", ""),
                            "people_count": client.get("people_count", 0) if status == "OK" else 0,
                            "image": client.get("image", None) if status == "OK" else "",
                            "status": status,
                            "delay": client.get("delay", 0) if status == "OK" else 0
                        }
                        real_time_monitors.append(real_time_monitor)
                    return jsonify({"status": "OK", "data": real_time_monitors}), 200
                elif data_type == 'zones':
                    real_time_zones = []
                    for zone in self.settings_manager.data["zones"]:
                        counts = []
                        for mname in zone.get("monitors", []):
                            for monitor in self.monitor_manager.data.get("monitors", []):
                                if monitor["name"] == mname:
                                    client_id = f"{monitor['key']}_{monitor['name']}"
                                    client = connected_clients.get(client_id)
                                    if client and (now - client.get("last_request", 0)) <= THRESHOLD:
                                        counts.append(client.get("people_count", 0))
                                    break
                        people_count = 0
                        if counts:
                            mode = zone.get("mode", "max")
                            if mode == "max":
                                people_count = max(counts)
                            elif mode == "min":
                                people_count = min(counts)
                            elif mode == "avg":
                                people_count = int(round(sum(counts) / len(counts)))
                        real_time_zone = {
                            "name": zone.get("name", ""),
                            "mode": zone.get("mode", "max"),
                            "monitors": zone.get("monitors", []),
                            "people_count": people_count
                        }
                        real_time_zones.append(real_time_zone)
                    return jsonify({"status": "OK", "data": real_time_zones}), 200
                elif data_type == 'accounts':
                    return jsonify({"status": "OK", "data": self.settings_manager.data["accounts"]}), 200

            elif request.method == 'POST':
                data = request.get_json(silent=True)
                if not data:
                    return jsonify({"status": "ERROR", "message": "Invalid data"}), 400
                if data_type == 'monitors':
                    self.monitor_manager.add_monitor(data)
                    return jsonify({"status": "OK", "message": "Monitor added"}), 201
                elif data_type == 'zones':
                    self.settings_manager.add_zone(data)
                    return jsonify({"status": "OK", "message": "Zone added"}), 201
                elif data_type == 'accounts':
                    self.settings_manager.add_account(data)
                    return jsonify({"status": "OK", "message": "Account added"}), 201

            elif request.method == 'PUT':
                data = request.get_json(silent=True)
                if not data or 'index' not in data:
                    return jsonify({"status": "ERROR", "message": "Invalid data or missing index"}), 400
                index = data.pop('index')
                if data_type == 'monitors':
                    self.monitor_manager.update_monitor(index, data)
                    return jsonify({"status": "OK", "message": "Monitor updated"}), 200
                elif data_type == 'zones':
                    self.settings_manager.update_zone(index, data)
                    return jsonify({"status": "OK", "message": "Zone updated"}), 200
                elif data_type == 'accounts':
                    if 'ip' in data or 'port' in data:
                        return jsonify({"status": "ERROR", "message": "Cannot modify server IP or port"}), 403
                    self.settings_manager.update_account(index, data)
                    return jsonify({"status": "OK", "message": "Account updated"}), 200

            elif request.method == 'DELETE':
                index = request.args.get('index')
                if not index:
                    return jsonify({"status": "ERROR", "message": "Missing index"}), 400
                index = int(index)
                if data_type == 'monitors':
                    self.monitor_manager.data["monitors"].pop(index)
                    self.monitor_manager.save()
                    return jsonify({"status": "OK", "message": "Monitor deleted"}), 200
                elif data_type == 'zones':
                    self.settings_manager.data["zones"].pop(index)
                    self.settings_manager.save()
                    return jsonify({"status": "OK", "message": "Zone deleted"}), 200
                elif data_type == 'accounts':
                    self.settings_manager.data["accounts"].pop(index)
                    self.settings_manager.save()
                    return jsonify({"status": "OK", "message": "Account deleted"}), 200

        @self.app.route('/connect', methods=['POST'])
        def connect():
            data = request.get_json(silent=True)
            if not data:
                print("[ERROR] No JSON data in /connect")
                return jsonify({"status": "ERROR", "message": "Invalid request: No JSON data"}), 400
            
            key = data.get('key')
            name = data.get('name')
            
            if not key or not name:
                print(f"[ERROR] Missing key={key} or name={name} in /connect")
                return jsonify({"status": "ERROR", "message": "Key and name are required"}), 400
            
            if not self._is_valid_client(key, name):
                print(f"[ERROR] Invalid key={key} or name={name} in /connect")
                return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403

            client_id = f"{key}_{name}"
            connected_clients[client_id] = {
                'key': key,
                'name': name,
                'people_count': 0,
                'image': None,
                "last_request": time.time(),
                "delay": 0
            }
            print(f"[INFO] Client connected: key={key}, name={name}")
            return jsonify({"status": "OK", "key": key, "name": name}), 200

        @self.app.route('/update_count', methods=['POST'])
        def update_count():
            data = request.get_json(silent=True)
            if not data:
                print("[ERROR] No JSON data in /update_count")
                return jsonify({"status": "ERROR", "message": "Invalid request: No JSON data"}), 400
            
            key = data.get('key')
            name = data.get('name')
            people_count = data.get('people_count')
            image_base64 = data.get('image')
            
            if not key or not name or people_count is None:
                print(f"[ERROR] Missing key={key}, name={name}, or people_count={people_count} in /update_count")
                return jsonify({"status": "ERROR", "message": "Missing required fields"}), 400
            
            if not self._is_valid_client(key, name):
                print(f"[ERROR] Invalid key={key} or name={name} in /update_count")
                return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403

            client_id = f"{key}_{name}"
            now = time.time()
            if client_id in connected_clients:
                client = connected_clients[client_id]
                prev = client.get("last_request")
                client["delay"] = round((now - prev) * 1000, 2) if prev else 0
                client["last_request"] = now
                client["people_count"] = people_count
                if image_base64:
                    client["image"] = image_base64
                    print(f"[INFO] Received image from {name} (key={key})")
                print(f"[INFO] Received update from {name} (key={key}): people_count={people_count}")
                return jsonify({"status": "OK"}), 200
            else:
                print(f"[WARNING] Client not connected: key={key}, name={name}")
                return jsonify({"status": "ERROR", "message": "Client not connected"}), 403

        @self.app.route('/client', methods=['POST'])
        def client():
            data = request.get_json(silent=True)
            if not data:
                print("[ERROR] No JSON data in /client")
                return jsonify({"status": "ERROR", "message": "Invalid request: No JSON data"}), 400
            
            action = data.get("action", "")
            if action == "connect":
                key = data.get('key')
                name = data.get('name')
                
                if not key or not name:
                    print(f"[ERROR] Missing key={key} or name={name} in /client?action=connect")
                    return jsonify({"status": "ERROR", "message": "Key and name are required"}), 400
                
                if not self._is_valid_client(key, name):
                    print(f"[ERROR] Invalid key={key} or name={name} in /client?action=connect")
                    return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403

                client_id = f"{key}_{name}"
                connected_clients[client_id] = {
                    'key': key,
                    'name': name,
                    'people_count': 0,
                    'image': None,
                    "last_request": time.time(),
                    "delay": 0
                }
                print(f"[INFO] Client connected (via /client): key={key}, name={name}")
                return jsonify({"status": "OK", "key": key, "name": name}), 200
            
            elif action == "update":
                key = data.get('key')
                name = data.get('name')
                people_count = data.get('people_count')
                image_base64 = data.get('image')
                
                if not key or not name or people_count is None:
                    print(f"[ERROR] Missing key={key}, name={name}, or people_count={people_count} in /client?action=update")
                    return jsonify({"status": "ERROR", "message": "Missing required fields"}), 400
                
                if not self._is_valid_client(key, name):
                    print(f"[ERROR] Invalid key={key} or name={name} in /client?action=update")
                    return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403

                client_id = f"{key}_{name}"
                now = time.time()
                if client_id in connected_clients:
                    client = connected_clients[client_id]
                    prev = client.get("last_request")
                    client["delay"] = round((now - prev) * 1000, 2) if prev else 0
                    client["last_request"] = now
                    client["people_count"] = people_count
                    if image_base64:
                        client["image"] = image_base64
                        print(f"[INFO] Received image from {name} (key={key}) via /client")
                    print(f"[INFO] Received update from {name} (key={key}): people_count={people_count} via /client")
                    return jsonify({"status": "OK"}), 200
                else:
                    print(f"[WARNING] Client not connected (via /client): key={key}, name={name}")
                    return jsonify({"status": "ERROR", "message": "Client not connected"}), 403
            
            else:
                print(f"[ERROR] Invalid action={action} in /client")
                return jsonify({"status": "ERROR", "message": "Invalid action"}), 400

    def run(self):
        server_ip = self.settings_manager.data["server"]["ip"]
        server_port = self.settings_manager.data["server"]["port"]
        self.app.run(host=server_ip, port=server_port, threaded=True)
# ---------------- Login Dialog ----------------
class LoginDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.user_account = None
        self.setWindowTitle("Đăng nhập")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Tên tài khoản")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Mật khẩu")
        layout.addWidget(QLabel("Tên tài khoản:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Mật khẩu:"))
        layout.addWidget(self.password_input)
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Đăng nhập")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.login_btn.clicked.connect(self.login)
        self.cancel_btn.clicked.connect(self.reject)
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        for account in self.settings_manager.data["accounts"]:
            if account["username"] == username and account["password"] == password:
                self.user_account = account
                self.accept()
                return
        QMessageBox.warning(self, "Lỗi", "Thông tin đăng nhập không hợp lệ")

# ---------------- Account Creation Dialog ----------------
class AccountCreationDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setWindowTitle("Tạo tài khoản mới")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Tên tài khoản")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Mật khẩu")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Nhập lại mật khẩu")
        layout.addWidget(QLabel("Tên tài khoản:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Mật khẩu:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Nhập lại mật khẩu:"))
        layout.addWidget(self.confirm_input)
        layout.addWidget(QLabel("Chọn quyền truy cập:"))
        self.chk_home = QCheckBox("Trang chủ")
        self.chk_zone = QCheckBox("Quản lý khu vực")
        self.chk_monitor = QCheckBox("Quản lý máy giám sát")
        layout.addWidget(self.chk_home)
        layout.addWidget(self.chk_zone)
        layout.addWidget(self.chk_monitor)
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Tạo tài khoản")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.create_btn.clicked.connect(self.create_account)
        self.cancel_btn.clicked.connect(self.reject)
    def create_account(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()
        if not username or not password or not confirm:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin")
            return
        if password != confirm:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu không khớp")
            return
        permissions = []
        if self.chk_home.isChecked():
            permissions.append("home")
        if self.chk_zone.isChecked():
            permissions.append("zone")
        if self.chk_monitor.isChecked():
            permissions.append("monitor")
        account = {"username": username, "password": password, "permissions": permissions}
        self.settings_manager.add_account(account)
        self.accept()

# ---------------- Account Edit Dialog ----------------
class AccountEditDialog(QDialog):
    def __init__(self, settings_manager, account, index):
        super().__init__()
        self.settings_manager = settings_manager
        self.account = account
        self.index = index
        self.setWindowTitle("Chỉnh sửa tài khoản")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Tên tài khoản: {self.account['username']}"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Mật khẩu mới (nếu muốn đổi)")
        layout.addWidget(QLabel("Mật khẩu mới:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Chọn quyền truy cập:"))
        self.chk_home = QCheckBox("Trang chủ")
        self.chk_zone = QCheckBox("Quản lý khu vực")
        self.chk_monitor = QCheckBox("Quản lý máy giám sát")
        permissions = self.account.get("permissions", [])
        self.chk_home.setChecked("home" in permissions)
        self.chk_zone.setChecked("zone" in permissions)
        self.chk_monitor.setChecked("monitor" in permissions)
        layout.addWidget(self.chk_home)
        layout.addWidget(self.chk_zone)
        layout.addWidget(self.chk_monitor)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Lưu")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.save_btn.clicked.connect(self.save_account)
        self.cancel_btn.clicked.connect(self.reject)
    def save_account(self):
        new_password = self.password_input.text().strip()
        if new_password:
            self.account["password"] = new_password
        new_permissions = []
        if self.chk_home.isChecked():
            new_permissions.append("home")
        if self.chk_zone.isChecked():
            new_permissions.append("zone")
        if self.chk_monitor.isChecked():
            new_permissions.append("monitor")
        self.account["permissions"] = new_permissions
        self.settings_manager.update_account(self.index, self.account)
        self.accept()

# ---------------- Home Page ----------------
class HomePage(QWidget):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP:"))
        self.ip_input = QLineEdit(self.settings_manager.data["server"]["ip"])
        ip_layout.addWidget(self.ip_input)
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit(str(self.settings_manager.data["server"]["port"]))
        port_layout.addWidget(self.port_input)
        layout.addLayout(ip_layout)
        layout.addLayout(port_layout)
        self.save_server_btn = QPushButton("Lưu Server")
        layout.addWidget(self.save_server_btn)
        self.account_list = QListWidget()
        self.refresh_accounts()
        layout.addWidget(QLabel("Danh sách tài khoản:"))
        layout.addWidget(self.account_list)
        btn_layout = QHBoxLayout()
        self.edit_account_btn = QPushButton("Edit Account")
        btn_layout.addWidget(self.edit_account_btn)
        layout.addLayout(btn_layout)
        self.save_server_btn.clicked.connect(self.save_server)
        self.edit_account_btn.clicked.connect(self.edit_account)
    def refresh_accounts(self):
        self.account_list.clear()
        for account in self.settings_manager.data["accounts"]:
            self.account_list.addItem(account["username"])
    def save_server(self):
        self.settings_manager.data["server"]["ip"] = self.ip_input.text().strip()
        self.settings_manager.data["server"]["port"] = int(self.port_input.text().strip())
        self.settings_manager.save()
        QMessageBox.information(self, "Thông báo", "Server đã được lưu!")
    def edit_account(self):
        selected = self.account_list.currentRow()
        if selected < 0:
            return
        account = self.settings_manager.data["accounts"][selected]
        dialog = AccountEditDialog(self.settings_manager, account, selected)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_accounts()

# ---------------- Zone Dialog ----------------
class ZoneDialog(QDialog):
    def __init__(self, monitor_manager, zone=None, parent=None):
        super().__init__(parent)
        self.monitor_manager = monitor_manager
        self.zone = zone  # Nếu None: tạo khu vực mới, nếu có: chỉnh sửa khu vực
        if self.zone:
            self.setWindowTitle("Sửa khu vực")
        else:
            self.setWindowTitle("Tạo khu vực")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tên khu vực:"))
        self.name_edit = QLineEdit()
        if self.zone:
            self.name_edit.setText(self.zone.get("name", ""))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Chế độ People Count:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["max", "min", "avg"])
        if self.zone:
            mode = self.zone.get("mode", "max")
            index = self.mode_combo.findText(mode)
            if index >= 0:
                self.mode_combo.setCurrentIndex(index)
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("Chọn máy giám sát:"))
        self.monitor_list = QListWidget()
        monitors = self.monitor_manager.data.get("monitors", [])
        for monitor in monitors:
            item = QListWidgetItem(monitor["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.zone and monitor["name"] in self.zone.get("monitors", []):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.monitor_list.addItem(item)
        layout.addWidget(self.monitor_list)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
    def get_zone_data(self):
        zone_data = {}
        zone_data["name"] = self.name_edit.text().strip()
        zone_data["mode"] = self.mode_combo.currentText()
        monitors = []
        for i in range(self.monitor_list.count()):
            item = self.monitor_list.item(i)
            if item.checkState() == Qt.Checked:
                monitors.append(item.text())
        zone_data["monitors"] = monitors
        zone_data["people_count"] = 0
        return zone_data

# ---------------- Zone Management Tab ----------------
class ZoneManagementTab(QWidget):
    def __init__(self, settings_manager, monitor_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.monitor_manager = monitor_manager
        self.setup_ui()
        self.zone_timer = QTimer(self)
        self.zone_timer.timeout.connect(self.update_zones_people)
        self.zone_timer.start(5000)
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.zone_list = QListWidget()
        self.refresh_zones()
        layout.addWidget(QLabel("Danh sách khu vực:"))
        layout.addWidget(self.zone_list)
        btn_layout = QHBoxLayout()
        self.create_zone_btn = QPushButton("Tạo khu vực")
        self.edit_zone_btn = QPushButton("Edit")
        btn_layout.addWidget(self.create_zone_btn)
        btn_layout.addWidget(self.edit_zone_btn)
        layout.addLayout(btn_layout)
        self.create_zone_btn.clicked.connect(self.create_zone)
        self.edit_zone_btn.clicked.connect(self.edit_zone)
    def refresh_zones(self):
        self.zone_list.clear()
        for zone in self.settings_manager.data["zones"]:
            mode = zone.get("mode", "max")
            self.zone_list.addItem(f"{zone['name']} - Mode: {mode}, People: {zone.get('people_count', 0)}")
    def create_zone(self):
        dialog = ZoneDialog(self.monitor_manager, zone=None, parent=self)
        if dialog.exec() == QDialog.Accepted:
            zone = dialog.get_zone_data()
            self.settings_manager.add_zone(zone)
            self.refresh_zones()
    def edit_zone(self):
        index = self.zone_list.currentRow()
        if index < 0:
            return
        zone = self.settings_manager.data["zones"][index]
        dialog = ZoneDialog(self.monitor_manager, zone=zone, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_zone = dialog.get_zone_data()
            self.settings_manager.update_zone(index, new_zone)
            self.refresh_zones()
    def update_zones_people(self):
        THRESHOLD = 15.0
        now = time.time()
        for zone in self.settings_manager.data["zones"]:
            counts = []
            for mname in zone.get("monitors", []):
                for monitor in self.monitor_manager.data.get("monitors", []):
                    if monitor["name"] == mname:
                        client_id = f"{monitor['key']}_{monitor['name']}"
                        client = connected_clients.get(client_id)
                        if client and (now - client.get("last_request", 0)) <= THRESHOLD:
                            counts.append(client.get("people_count", 0))
                        break
            if counts:
                mode = zone.get("mode", "max")
                if mode == "max":
                    zone["people_count"] = max(counts)
                elif mode == "min":
                    zone["people_count"] = min(counts)
                elif mode == "avg":
                    zone["people_count"] = int(round(sum(counts) / len(counts)))
                else:
                    zone["people_count"] = 0
            else:
                zone["people_count"] = 0
        self.refresh_zones()

# ---------------- Add Monitor Dialog ----------------
class AddMonitorDialog(QDialog):
    def __init__(self, monitor_manager):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.setWindowTitle("Thêm máy giám sát")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên máy giám sát")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Key")
        self.gen_key_btn = QPushButton("Tạo key")
        layout.addWidget(QLabel("Tên máy giám sát:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Key:"))
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.gen_key_btn)
        layout.addLayout(key_layout)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.gen_key_btn.clicked.connect(self.generate_key)
        self.ok_btn.clicked.connect(self.add_monitor)
        self.cancel_btn.clicked.connect(self.reject)
    def generate_key(self):
        self.key_input.setText(RandomGenerator.generate_key(16))
    def add_monitor(self):
        name = self.name_input.text().strip()
        key = self.key_input.text().strip()
        if not name or not key:
            QMessageBox.warning(self, "Lỗi", "Nhập đầy đủ thông tin")
            return
        monitor = {
            "name": name,
            "key": key,
            "image": "",
            "people_count": 0,
            "status": "ERROR",
            "delay": 0
        }
        self.monitor_manager.add_monitor(monitor)
        self.accept()

# ---------------- Monitor Edit Dialog ----------------
class MonitorEditDialog(QDialog):
    def __init__(self, monitor_manager, monitor, index):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.monitor = monitor
        self.index = index
        self.setWindowTitle("Chỉnh sửa máy giám sát")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit(self.monitor.get("name", ""))
        self.key_input = QLineEdit(self.monitor.get("key", ""))
        layout.addWidget(QLabel("Tên máy giám sát:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Key:"))
        layout.addWidget(self.key_input)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Lưu")
        self.cancel_btn = QPushButton("Hủy")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.save_btn.clicked.connect(self.save_monitor)
        self.cancel_btn.clicked.connect(self.reject)
    def save_monitor(self):
        new_name = self.name_input.text().strip()
        new_key = self.key_input.text().strip()
        if not new_name or not new_key:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin")
            return
        self.monitor["name"] = new_name
        self.monitor["key"] = new_key
        self.monitor_manager.update_monitor(self.index, self.monitor)
        self.accept()

# ---------------- Monitor Management Tab ----------------
class MonitorManagementTab(QWidget):
    def __init__(self, monitor_manager):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.setup_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_monitor_data)
        self.timer.start(1000)
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        self.monitor_list = QListWidget()
        self.refresh_monitors()
        left_layout.addWidget(QLabel("Danh sách máy giám sát:"))
        left_layout.addWidget(self.monitor_list)
        btn_layout = QHBoxLayout()
        self.add_monitor_btn = QPushButton("Thêm máy giám sát")
        self.import_monitor_btn = QPushButton("Import JSON")
        self.edit_monitor_btn = QPushButton("Edit Monitor")
        self.reload_btn = QPushButton("Tải lại")
        btn_layout.addWidget(self.add_monitor_btn)
        btn_layout.addWidget(self.import_monitor_btn)
        btn_layout.addWidget(self.edit_monitor_btn)
        btn_layout.addWidget(self.reload_btn)
        left_layout.addLayout(btn_layout)
        right_layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setFixedSize(320, 240)
        self.image_label.setStyleSheet("background-color: black;")
        right_layout.addWidget(self.image_label)
        self.detail_label = QLabel("Chi tiết máy giám sát:")
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)
        self.monitor_list.itemClicked.connect(self.show_monitor_detail)
        self.add_monitor_btn.clicked.connect(self.add_monitor)
        self.import_monitor_btn.clicked.connect(self.import_monitors)
        self.edit_monitor_btn.clicked.connect(self.edit_monitor)
        self.reload_btn.clicked.connect(self.update_monitor_data)
    def refresh_monitors(self):
        self.monitor_list.clear()
        for monitor in self.monitor_manager.data["monitors"]:
            self.monitor_list.addItem(monitor["name"])
    def add_monitor(self):
        dialog = AddMonitorDialog(self.monitor_manager)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_monitors()
    def import_monitors(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if "monitors" in data:
                    self.monitor_manager.data = data
                    self.monitor_manager.save()
                    self.refresh_monitors()
                else:
                    QMessageBox.warning(self, "Lỗi", "File không hợp lệ")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Lỗi khi đọc file: {e}")
    def show_monitor_detail(self, item):
        self.update_monitor_data()
    def update_monitor_data(self):
        selected = self.monitor_list.currentRow()
        if selected < 0:
            self.detail_label.setText("Chi tiết máy giám sát:")
            self.show_black_image()
            return
        monitor = self.monitor_manager.data["monitors"][selected]
        client_id = f"{monitor.get('key','')}_{monitor.get('name','')}"
        client = connected_clients.get(client_id)
        now = time.time()
        THRESHOLD = 15.0
        if client and (now - client.get("last_request", 0)) <= THRESHOLD:
            status = "OK"
            delay = client.get("delay", "-")
            people_count = client.get("people_count", 0)
            image_b64 = client.get("image")
        else:
            status = "ERROR"
            delay = "-"
            people_count = 0
            image_b64 = None
            if client:
                client["image"] = None
                client["people_count"] = 0
        detail = (
            f"Name: {monitor['name']}\n"
            f"Key: {monitor.get('key','')}\n"
            f"People Count: {people_count}\n"
            f"Status: {status}\n"
            f"Delay: {delay} ms"
        )
        if image_b64:
            detail += "\n[Image available]"
        self.detail_label.setText(detail)
        if image_b64:
            try:
                image_data = base64.b64decode(image_b64)
                nparray = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparray, cv2.IMREAD_COLOR)
                if frame is not None:
                    frame = cv2.flip(frame, -1)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width, channel = frame.shape
                    bytes_per_line = 3 * width
                    qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                    self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))
                else:
                    self.show_black_image()
            except Exception as e:
                print(f"Error decoding image: {e}")
                self.show_black_image()
        else:
            self.show_black_image()
    def show_black_image(self):
        black = QPixmap(self.image_label.size())
        black.fill(Qt.black)
        self.image_label.setPixmap(black)
    def edit_monitor(self):
        selected = self.monitor_list.currentRow()
        if selected < 0:
            return
        monitor = self.monitor_manager.data["monitors"][selected]
        dialog = MonitorEditDialog(self.monitor_manager, monitor, selected)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_monitors()

# ---------------- Main Window ----------------
class MainWindow(QMainWindow):
    def __init__(self, settings_manager, monitor_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.monitor_manager = monitor_manager
        self.setWindowTitle("Server Monitor App")
        self.setup_ui()
    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.home_page = HomePage(self.settings_manager)
        self.zone_tab = ZoneManagementTab(self.settings_manager, self.monitor_manager)
        self.monitor_tab = MonitorManagementTab(self.monitor_manager)
        self.tab_widget.addTab(self.home_page, "Trang chủ")
        self.tab_widget.addTab(self.zone_tab, "Quản lý khu vực")
        self.tab_widget.addTab(self.monitor_tab, "Quản lý máy giám sát")
        self.setCentralWidget(self.tab_widget)

# ---------------- Main ----------------
def main():
    settings_manager = SettingsManager()
    monitor_manager = MonitorManager()
    flask_server = FlaskServer(settings_manager, monitor_manager)
    flask_thread = threading.Thread(target=flask_server.run)
    flask_thread.daemon = True
    flask_thread.start()
    app = QApplication(sys.argv)
    if not settings_manager.data["accounts"]:
        acct_dialog = AccountCreationDialog(settings_manager)
        if acct_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
    login_dialog = LoginDialog(settings_manager)
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    main_win = MainWindow(settings_manager, monitor_manager)
    main_win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()