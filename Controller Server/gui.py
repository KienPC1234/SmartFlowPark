from PySide6.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget, QDialog, QCheckBox, QMessageBox, QFileDialog, QListWidgetItem, QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
import base64
import cv2
import numpy as np
import time
from random_generator import RandomGenerator
from flask_server import connected_clients
import json

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
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
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

class AccountCreationDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setWindowTitle("Tạo tài khoản mới")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
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
        self.create_account_btn = QPushButton("Create Account")
        btn_layout.addWidget(self.edit_account_btn)
        btn_layout.addWidget(self.create_account_btn)
        layout.addLayout(btn_layout)
        self.save_server_btn.clicked.connect(self.save_server)
        self.edit_account_btn.clicked.connect(self.edit_account)
        self.create_account_btn.clicked.connect(self.create_account)

    def create_account(self):
        dialog = AccountCreationDialog(self.settings_manager)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_accounts()

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

class ZoneDialog(QDialog):
    def __init__(self, monitor_manager, zone=None, parent=None):
        super().__init__(parent)
        self.monitor_manager = monitor_manager
        self.zone = zone
        self.setWindowTitle("Sửa khu vực" if self.zone else "Tạo khu vực")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tên khu vực:"))
        self.name_edit = QLineEdit(self.zone.get("name", "") if self.zone else "")
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Chế độ People Count:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["max", "min", "avg"])
        if self.zone:
            self.mode_combo.setCurrentText(self.zone.get("mode", "max"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("Chọn máy giám sát:"))
        self.monitor_list = QListWidget()
        for monitor in self.monitor_manager.data.get("monitors", []):
            item = QListWidgetItem(monitor["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if self.zone and monitor["name"] in self.zone.get("monitors", []) else Qt.Unchecked)
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
        return {
            "name": self.name_edit.text().strip(),
            "mode": self.mode_combo.currentText(),
            "monitors": [self.monitor_list.item(i).text() for i in range(self.monitor_list.count()) if self.monitor_list.item(i).checkState() == Qt.Checked],
            "people_count": 0
        }

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
            self.zone_list.addItem(f"{zone['name']} - Mode: {zone.get('mode', 'max')}, People: {zone.get('people_count', 0)}")

    def create_zone(self):
        dialog = ZoneDialog(self.monitor_manager, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.settings_manager.add_zone(dialog.get_zone_data())
            self.refresh_zones()

    def edit_zone(self):
        index = self.zone_list.currentRow()
        if index < 0:
            return
        dialog = ZoneDialog(self.monitor_manager, self.settings_manager.data["zones"][index], self)
        if dialog.exec() == QDialog.Accepted:
            self.settings_manager.update_zone(index, dialog.get_zone_data())
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
            zone["people_count"] = (
                max(counts) if counts and zone.get("mode", "max") == "max" else
                min(counts) if counts and zone.get("mode") == "min" else
                int(round(sum(counts) / len(counts))) if counts and zone.get("mode") == "avg" else 0
            )
        self.refresh_zones()

class AddMonitorDialog(QDialog):
    def __init__(self, monitor_manager):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.setWindowTitle("Thêm máy giám sát")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit()
        self.key_input = QLineEdit()
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
        self.monitor_manager.add_monitor({"name": name, "key": key, "image": "", "people_count": 0, "status": "ERROR", "delay": 0})
        self.accept()

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

        # Thêm các nút vào layout
        btn_layout = QHBoxLayout()
        self.add_monitor_btn = QPushButton("Thêm máy giám sát")
        self.import_monitor_btn = QPushButton("Import JSON")
        self.edit_monitor_btn = QPushButton("Edit Monitor")
        self.reset_monitor_btn = QPushButton("Reset Counter")  # Thêm nút Reset
        self.reload_btn = QPushButton("Tải lại")
        btn_layout.addWidget(self.add_monitor_btn)
        btn_layout.addWidget(self.import_monitor_btn)
        btn_layout.addWidget(self.edit_monitor_btn)
        btn_layout.addWidget(self.reset_monitor_btn)  # Thêm vào layout
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

        # Kết nối sự kiện
        self.monitor_list.itemClicked.connect(self.show_monitor_detail)
        self.add_monitor_btn.clicked.connect(self.add_monitor)
        self.import_monitor_btn.clicked.connect(self.import_monitors)
        self.edit_monitor_btn.clicked.connect(self.edit_monitor)
        self.reset_monitor_btn.clicked.connect(self.reset_monitor)  # Kết nối sự kiện Reset
        self.reload_btn.clicked.connect(self.update_monitor_data)

    def reset_monitor(self):
        selected = self.monitor_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một máy giám sát để reset.")
            return
        monitor = self.monitor_manager.data["monitors"][selected]
        key = monitor.get("key")
        name = monitor.get("name")
        if not key or not name:
            QMessageBox.warning(self, "Lỗi", "Máy giám sát không có key hoặc name.")
            return
        client_id = f"{key}_{name}"
        if client_id in connected_clients:
            connected_clients[client_id]["people_count"] = 0
            connected_clients[client_id]["reset_counter"] = True  # Đặt flag để thông báo client
            QMessageBox.information(self, "Thành công", "Đã reset đếm người.")
        else:
            QMessageBox.warning(self, "Lỗi", "Máy giám sát không được kết nối.")

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