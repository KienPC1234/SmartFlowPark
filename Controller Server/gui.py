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

class LoginDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.user_account = None
        self.setWindowTitle("Login")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_input)
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.login_btn.clicked.connect(self.login)
        self.cancel_btn.clicked.connect(self.reject)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        for account in self.settings_manager.get_all_accounts():
            if account["username"] == username and account["password"] == password:
                self.user_account = account
                self.accept()
                return
        QMessageBox.warning(self, "Error", "Invalid login credentials")

class AccountCreationDialog(QDialog):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setWindowTitle("Create New Account")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Confirm Password:"))
        layout.addWidget(self.confirm_input)
        layout.addWidget(QLabel("Select Permissions:"))
        self.chk_home = QCheckBox("Home")
        self.chk_zone = QCheckBox("Zone Management")
        self.chk_monitor = QCheckBox("Monitor Management")
        layout.addWidget(self.chk_home)
        layout.addWidget(self.chk_zone)
        layout.addWidget(self.chk_monitor)
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Account")
        self.cancel_btn = QPushButton("Cancel")
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
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match")
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
    def __init__(self, settings_manager, account):
        super().__init__()
        self.settings_manager = settings_manager
        self.account = account
        self.setWindowTitle("Edit Account")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Username: {self.account['username']}"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("New Password:"))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Select Permissions:"))
        self.chk_home = QCheckBox("Home")
        self.chk_zone = QCheckBox("Zone Management")
        self.chk_monitor = QCheckBox("Monitor Management")
        permissions = self.account.get("permissions", [])
        self.chk_home.setChecked("home" in permissions)
        self.chk_zone.setChecked("zone" in permissions)
        self.chk_monitor.setChecked("monitor" in permissions)
        layout.addWidget(self.chk_home)
        layout.addWidget(self.chk_zone)
        layout.addWidget(self.chk_monitor)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.save_btn.clicked.connect(self.save_account)
        self.cancel_btn.clicked.connect(self.reject)

    def save_account(self):
        new_password = self.password_input.text().strip()
        if new_password:
            self.account["password"] = new_password
        permissions = []
        if self.chk_home.isChecked():
            permissions.append("home")
        if self.chk_zone.isChecked():
            permissions.append("zone")
        if self.chk_monitor.isChecked():
            permissions.append("monitor")
        self.account["permissions"] = permissions
        self.settings_manager.update_account(self.account["id"], self.account)
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
        server_settings = self.settings_manager.get_server_settings()
        self.ip_input = QLineEdit(server_settings["ip"])
        ip_layout.addWidget(self.ip_input)
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit(str(server_settings["port"]))
        port_layout.addWidget(self.port_input)
        layout.addLayout(ip_layout)
        layout.addLayout(port_layout)
        self.save_server_btn = QPushButton("Save Server")
        layout.addWidget(self.save_server_btn)
        self.account_list = QListWidget()
        self.refresh_accounts()
        layout.addWidget(QLabel("Account List:"))
        layout.addWidget(self.account_list)
        btn_layout = QHBoxLayout()
        self.edit_account_btn = QPushButton("Edit Account")
        self.create_account_btn = QPushButton("Create Account")
        self.refresh_btn = QPushButton("Refresh")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.edit_account_btn)
        btn_layout.addWidget(self.create_account_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)
        self.save_server_btn.clicked.connect(self.save_server)
        self.edit_account_btn.clicked.connect(self.edit_account)
        self.create_account_btn.clicked.connect(self.create_account)
        self.refresh_btn.clicked.connect(self.refresh_accounts)
        self.delete_btn.clicked.connect(self.delete_selected_account)

    def refresh_accounts(self):
        self.account_list.clear()
        for account in self.settings_manager.get_all_accounts():
            self.account_list.addItem(account["username"])

    def delete_selected_account(self):
        selected = self.account_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Please select an account to delete.")
            return
        account = self.settings_manager.get_all_accounts()[selected]
        account_id = account["id"]
        reply = QMessageBox.question(self, "Confirm", "Are you sure you want to delete this account?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                import sqlite3
                conn = sqlite3.connect(self.settings_manager.db_name)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Error", "Account does not exist.")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Success", "Account has been deleted.")
                    self.refresh_accounts()
                conn.close()
            except sqlite3.Error as e:
                QMessageBox.warning(self, "Error", f"Unable to delete account: {str(e)}")

    def create_account(self):
        dialog = AccountCreationDialog(self.settings_manager)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_accounts()

    def save_server(self):
        ip = self.ip_input.text().strip()
        port = int(self.port_input.text().strip())
        self.settings_manager.update_server_settings(ip, port)
        QMessageBox.information(self, "Notification", "Server has been saved!")

    def edit_account(self):
        selected = self.account_list.currentRow()
        if selected < 0:
            return
        account = self.settings_manager.get_all_accounts()[selected]
        dialog = AccountEditDialog(self.settings_manager, account)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_accounts()

class ZoneDialog(QDialog):
    def __init__(self, monitor_manager, zone=None, parent=None):
        super().__init__(parent)
        self.monitor_manager = monitor_manager
        self.zone = zone
        self.setWindowTitle("Edit Zone" if self.zone else "Create Zone")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Zone Name:"))
        self.name_edit = QLineEdit(self.zone.get("name", "") if self.zone else "")
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("People Count Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["max", "min", "avg", "sum"])
        if self.zone:
            self.mode_combo.setCurrentText(self.zone.get("mode", "max"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("Select Monitors:"))
        self.monitor_list = QListWidget()
        for monitor in self.monitor_manager.get_all_monitors():
            item = QListWidgetItem(monitor["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if self.zone and monitor["name"] in self.zone.get("monitors", []) else Qt.Unchecked)
            self.monitor_list.addItem(item)
        layout.addWidget(self.monitor_list)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
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
        layout.addWidget(QLabel("Zone List:"))
        layout.addWidget(self.zone_list)
        btn_layout = QHBoxLayout()
        self.create_zone_btn = QPushButton("Create Zone")
        self.edit_zone_btn = QPushButton("Edit")
        self.refresh_btn = QPushButton("Refresh")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.create_zone_btn)
        btn_layout.addWidget(self.edit_zone_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)
        self.create_zone_btn.clicked.connect(self.create_zone)
        self.edit_zone_btn.clicked.connect(self.edit_zone)
        self.refresh_btn.clicked.connect(self.refresh_zones)
        self.delete_btn.clicked.connect(self.delete_selected_zone)

    def refresh_zones(self):
        self.zone_list.clear()
        for zone in self.settings_manager.get_all_zones():
            self.zone_list.addItem(f"{zone['name']} - Mode: {zone.get('mode', 'max')}, People: {zone.get('people_count', 0)}")

    def delete_selected_zone(self):
        selected = self.zone_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Please select a zone to delete.")
            return
        zone = self.settings_manager.get_all_zones()[selected]
        zone_id = zone["id"]
        reply = QMessageBox.question(self, "Confirm", "Are you sure you want to delete this zone?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                import sqlite3
                conn = sqlite3.connect(self.settings_manager.db_name)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM zones WHERE id = ?', (zone_id,))
                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Error", "Zone does not exist.")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Success", "Zone has been deleted.")
                    self.refresh_zones()
                conn.close()
            except sqlite3.Error as e:
                QMessageBox.warning(self, "Error", f"Unable to delete zone: {str(e)}")

    def create_zone(self):
        dialog = ZoneDialog(self.monitor_manager, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.settings_manager.add_zone(dialog.get_zone_data())
            self.refresh_zones()

    def edit_zone(self):
        index = self.zone_list.currentRow()
        if index < 0:
            return
        zone = self.settings_manager.get_all_zones()[index]
        dialog = ZoneDialog(self.monitor_manager, zone, self)
        if dialog.exec() == QDialog.Accepted:
            self.settings_manager.update_zone(zone["id"], dialog.get_zone_data())
            self.refresh_zones()

    def update_zones_people(self):
        THRESHOLD = 15.0
        now = time.time()
        zones = self.settings_manager.get_all_zones()
        monitors = self.monitor_manager.get_all_monitors()
        for zone in zones:
            counts = []
            for mname in zone.get("monitors", []):
                for monitor in monitors:
                    if monitor["name"] == mname:
                        client_id = f"{monitor['key']}_{monitor['name']}"
                        client = connected_clients.get(client_id)
                        if client and (now - client.get("last_request", 0)) <= THRESHOLD:
                            counts.append(client.get("people_count", 0))
                        break
            zone["people_count"] = (
                max(counts) if counts and zone.get("mode", "max") == "max" else
                min(counts) if counts and zone.get("mode") == "min" else
                int(round(sum(counts) / len(counts))) if counts and zone.get("mode") == "avg" else 
                sum(counts) if counts and zone.get("mode") == "sum" else 0
            )
            self.settings_manager.update_zone(zone["id"], zone)
        self.refresh_zones()

class AddMonitorDialog(QDialog):
    def __init__(self, monitor_manager):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.setWindowTitle("Add Monitor")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit()
        self.key_input = QLineEdit()
        self.gen_key_btn = QPushButton("Generate Key")
        layout.addWidget(QLabel("Monitor Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Key:"))
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.gen_key_btn)
        layout.addLayout(key_layout)
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
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
            QMessageBox.warning(self, "Error", "Please fill in all fields")
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

class MonitorEditDialog(QDialog):
    def __init__(self, monitor_manager, monitor):
        super().__init__()
        self.monitor_manager = monitor_manager
        self.monitor = monitor
        self.setWindowTitle("Edit Monitor")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_input = QLineEdit(self.monitor.get("name", ""))
        self.key_input = QLineEdit(self.monitor.get("key", ""))
        layout.addWidget(QLabel("Monitor Name:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Key:"))
        layout.addWidget(self.key_input)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        self.save_btn.clicked.connect(self.save_monitor)
        self.cancel_btn.clicked.connect(self.reject)

    def save_monitor(self):
        new_name = self.name_input.text().strip()
        new_key = self.key_input.text().strip()
        if not new_name or not new_key:
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
        self.monitor["name"] = new_name
        self.monitor["key"] = new_key
        self.monitor_manager.update_monitor(self.monitor["id"], self.monitor)
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
        left_layout.addWidget(QLabel("Monitor List:"))
        left_layout.addWidget(self.monitor_list)

        btn_layout = QHBoxLayout()
        self.add_monitor_btn = QPushButton("Add Monitor")
        self.edit_monitor_btn = QPushButton("Edit Monitor")
        self.reset_monitor_btn = QPushButton("Reset Counter")
        self.reload_btn = QPushButton("Reload")
        self.refresh_btn = QPushButton("Refresh")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.add_monitor_btn)
        btn_layout.addWidget(self.edit_monitor_btn)
        btn_layout.addWidget(self.reset_monitor_btn)
        btn_layout.addWidget(self.reload_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        left_layout.addLayout(btn_layout)

        right_layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setFixedSize(320, 240)
        self.image_label.setStyleSheet("background-color: black;")
        right_layout.addWidget(self.image_label)
        self.detail_label = QLabel("Monitor Details:")
        self.detail_label.setWordWrap(True)
        right_layout.addWidget(self.detail_label)
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)

        self.monitor_list.itemClicked.connect(self.show_monitor_detail)
        self.add_monitor_btn.clicked.connect(self.add_monitor)
        self.edit_monitor_btn.clicked.connect(self.edit_monitor)
        self.reset_monitor_btn.clicked.connect(self.reset_monitor)
        self.reload_btn.clicked.connect(self.update_monitor_data)
        self.refresh_btn.clicked.connect(self.refresh_monitors)
        self.delete_btn.clicked.connect(self.delete_selected_monitor)

    def refresh_monitors(self):
        self.monitor_list.clear()
        for monitor in self.monitor_manager.get_all_monitors():
            self.monitor_list.addItem(monitor["name"])

    def delete_selected_monitor(self):
        selected = self.monitor_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Please select a monitor to delete.")
            return
        monitor = self.monitor_manager.get_all_monitors()[selected]
        monitor_id = monitor["id"]
        reply = QMessageBox.question(self, "Confirm", "Are you sure you want to delete this monitor?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                import sqlite3
                conn = sqlite3.connect(self.monitor_manager.db_name)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM monitors WHERE id = ?', (monitor_id,))
                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Error", "Monitor does not exist.")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Success", "Monitor has been deleted.")
                    self.refresh_monitors()
                conn.close()
            except sqlite3.Error as e:
                QMessageBox.warning(self, "Error", f"Unable to delete monitor: {str(e)}")

    def reset_monitor(self):
        selected = self.monitor_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Please select a monitor to reset.")
            return
        monitor = self.monitor_manager.get_all_monitors()[selected]
        key = monitor.get("key")
        name = monitor.get("name")
        if not key or not name:
            QMessageBox.warning(self, "Error", "Monitor does not have a key or name.")
            return
        client_id = f"{key}_{name}"
        if client_id in connected_clients:
            connected_clients[client_id]["people_count"] = 0
            connected_clients[client_id]["reset_counter"] = True
            QMessageBox.information(self, "Success", "People count has been reset.")
        else:
            QMessageBox.warning(self, "Error", "Monitor is not connected.")
        self.refresh_monitors()

    def add_monitor(self):
        dialog = AddMonitorDialog(self.monitor_manager)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_monitors()

    def show_monitor_detail(self, item):
        self.update_monitor_data()

    def update_monitor_data(self):
        selected = self.monitor_list.currentRow()
        monitors = self.monitor_manager.get_all_monitors()

        if selected < 0 or selected >= len(monitors):
            self.detail_label.setText("Monitor Details: (No monitor selected or monitor has been deleted)")
            self.show_black_image()
            return

        monitor = monitors[selected]
        client_id = f"{monitor.get('key', '')}_{monitor.get('name', '')}"
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
            f"Key: {monitor.get('key', '')}\n"
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
        monitor = self.monitor_manager.get_all_monitors()[selected]
        dialog = MonitorEditDialog(self.monitor_manager, monitor)
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
        self.tab_widget.addTab(self.home_page, "Home")
        self.tab_widget.addTab(self.zone_tab, "Zone Management")
        self.tab_widget.addTab(self.monitor_tab, "Monitor Management")
        self.setCentralWidget(self.tab_widget)