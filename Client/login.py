from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QCheckBox, QMessageBox
from PySide6.QtCore import Signal, Qt
from settings import ClientSettings, load_client_data, save_client_data
from api import ApiClient
import requests
import os

class LoginWindow(QWidget):
    login_successful = Signal(ClientSettings, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setMinimumSize(400, 350)
        self.settings = None
        self.failed_attempts = 0  # Đếm số lần thử sai PIN
        self.max_attempts = 3  # Giới hạn số lần thử sai PIN
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_server = QFormLayout()
        self.ip_edit = QLineEdit("127.0.0.1")
        self.ip_edit.setMinimumHeight(30)
        self.port_edit = QLineEdit("8080")
        self.port_edit.setMinimumHeight(30)
        form_server.addRow("Server IP:", self.ip_edit)
        form_server.addRow("Port:", self.port_edit)
        layout.addLayout(form_server)

        form_auth = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setMinimumHeight(30)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumHeight(30)
        form_auth.addRow("Username:", self.username_edit)
        form_auth.addRow("Password:", self.password_edit)
        layout.addLayout(form_auth)

        self.remember_cb = QCheckBox("Remember Me (Only enter PIN next time)")
        layout.addWidget(self.remember_cb)

        self.pin_edit = QLineEdit()
        self.pin_edit.setPlaceholderText("Enter PIN (4 or 8 digits)")
        self.pin_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_edit.setMinimumHeight(30)
        layout.addWidget(QLabel("PIN is used to encrypt data"))
        layout.addWidget(self.pin_edit)

        self.login_btn = QPushButton("Login")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_btn)

        # Thêm nút "Use Another Account"
        self.use_another_btn = QPushButton("Use Another Account")
        self.use_another_btn.setMinimumHeight(40)
        self.use_another_btn.clicked.connect(self.reset_login_form)
        layout.addWidget(self.use_another_btn)

        layout.addStretch()
        self.setLayout(layout)

        self.check_saved_data()

    def check_saved_data(self):
        if os.path.exists("client_data.dat"):
            self.ip_edit.setEnabled(False)
            self.port_edit.setEnabled(False)
            self.username_edit.setEnabled(False)
            self.password_edit.setEnabled(False)
            self.remember_cb.setEnabled(False)
            self.remember_cb.setChecked(True)
        else:
            self.ip_edit.setEnabled(True)
            self.port_edit.setEnabled(True)
            self.username_edit.setEnabled(True)
            self.password_edit.setEnabled(True)
            self.remember_cb.setEnabled(True)

    def attempt_login(self):
        pin = self.pin_edit.text().strip()
        if not pin:
            QMessageBox.warning(self, "Error", "Please enter a PIN!")
            return
        if len(pin) not in (4, 8) or not pin.isdigit():
            QMessageBox.warning(self, "Error", "PIN must be 4 or 8 digits!")
            return

        if not self.ip_edit.isEnabled():
            settings, success = load_client_data(pin)
            if success:
                self.failed_attempts = 0  # Reset số lần thử sai khi thành công
                api_client = ApiClient(settings)
                try:
                    resp = api_client.login(settings.username, settings.password)
                    if resp.status_code == 200:
                        data = resp.json()
                        settings.token = data.get("token", "")
                        settings.permissions = data.get("permissions", [])
                        if not settings.token:
                            QMessageBox.warning(self, "Error", "Invalid token from server!")
                            return
                        self.login_successful.emit(settings, pin)
                    else:
                        QMessageBox.warning(self, "Error", "Authentication with server failed! Please re-enter information.")
                        self.reset_login_form()
                except requests.RequestException as e:
                    QMessageBox.warning(self, "Error", f"Cannot connect to server: {str(e)}")
                    self.reset_login_form()
            else:
                self.failed_attempts += 1
                if self.failed_attempts >= self.max_attempts:
                    QMessageBox.warning(self, "Error", f"Too many failed attempts ({self.max_attempts})! Please use another account.")
                    self.reset_login_form()
                else:
                    QMessageBox.warning(self, "Error", "Incorrect PIN or corrupted data! Please try again.")
        else:
            ip = self.ip_edit.text().strip()
            port = self.port_edit.text().strip()
            username = self.username_edit.text().strip()
            password = self.password_edit.text().strip()
            if not all([ip, port, username, password]):
                QMessageBox.warning(self, "Error", "Please fill in all fields!")
                return
            settings = ClientSettings()
            settings.server_ip = ip
            try:
                settings.server_port = int(port)
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid port!")
                return
            settings.username = username
            settings.password = password
            api_client = ApiClient(settings)
            try:
                resp = api_client.login(username, password)
                if resp.status_code == 200:
                    data = resp.json()
                    settings.token = data.get("token", "")
                    settings.permissions = data.get("permissions", [])
                    if not settings.token:
                        QMessageBox.warning(self, "Error", "Invalid token from server!")
                        return
                    if self.remember_cb.isChecked():
                        save_client_data(settings, pin)
                    self.login_successful.emit(settings, pin)
                else:
                    QMessageBox.warning(self, "Error", f"Login failed: {resp.json().get('message', 'Unknown error')}")
            except requests.RequestException as e:
                QMessageBox.warning(self, "Error", f"Cannot connect to server: {str(e)}")

    def reset_login_form(self):
        """Đặt lại form đăng nhập và cho phép nhập thông tin mới."""
        self.ip_edit.setEnabled(True)
        self.port_edit.setEnabled(True)
        self.username_edit.setEnabled(True)
        self.password_edit.setEnabled(True)
        self.remember_cb.setEnabled(True)
        self.username_edit.clear()
        self.password_edit.clear()
        self.pin_edit.clear()
        self.remember_cb.setChecked(False)
        self.failed_attempts = 0  # Reset số lần thử sai
        if os.path.exists("client_data.dat"):
            os.remove("client_data.dat")
            os.remove("salt.bin")