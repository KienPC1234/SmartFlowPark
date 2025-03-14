import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QTabWidget, QPushButton, QMessageBox, QTabBar
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont
from settings import ClientSettings, save_client_data, load_client_data
from login import LoginWindow
from tabs import AccountTab, ZoneTab, MonitorTab, SettingTab
from api import ApiClient
import requests

class MainWindow(QMainWindow):
    session_expired = Signal()

    def __init__(self, settings, pin):
        super().__init__()
        self.settings = settings
        self.pin = pin 
        self.api_client = ApiClient(settings)
        self.setWindowTitle("SmartFlow Park Client")
        self.setMinimumSize(900, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.account_tab = AccountTab(settings, self.api_client, self.tabs)
        self.account_tab.setEnabled("home" in settings.permissions)
        self.zone_tab = ZoneTab(settings, self.api_client, self.tabs)
        self.zone_tab.setEnabled("zone" in settings.permissions)
        self.monitor_tab = MonitorTab(settings, self.api_client, self.tabs)
        self.monitor_tab.setEnabled("monitor" in settings.permissions)
        self.setting_tab = SettingTab(settings, pin, self.tabs)


        self.tabs.addTab(self.account_tab, "Account")
        self.tabs.addTab(self.zone_tab, "Zone")
        self.tabs.addTab(self.monitor_tab, "Monitor")
        self.tabs.addTab(self.setting_tab, "Setting")

        # Kết nối signal khi tab thay đổi
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Nút đăng xuất
        self.logout_btn = QPushButton("Đăng xuất")
        self.logout_btn.clicked.connect(self.logout)
        self.tabs.tabBar().setTabButton(self.tabs.count() - 1, QTabBar.RightSide, self.logout_btn)

        # Timer kiểm tra session
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.check_session)
        self.session_timer.start(50000)  

        self.apply_settings()

    def apply_settings(self):
        """Áp dụng cài đặt font cho giao diện."""
        font = QFont(self.settings.font, self.settings.font_size)
        self.setFont(font)

    def on_tab_changed(self, index):
        """Quản lý refresh của các tab khi chuyển đổi."""
        # Dừng timer của tất cả các tab
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'tab_deactivated'):
                tab.tab_deactivated()
        # Kích hoạt timer của tab hiện tại
        current_tab = self.tabs.widget(index)
        if hasattr(current_tab, 'tab_activated'):
            current_tab.tab_activated()

    def check_session(self):
        """Kiểm tra trạng thái session."""
        try:
            resp = self.api_client.get_accounts()
            if resp.status_code != 200:
                QMessageBox.information(self, "Thông báo", "Session hết hạn hoặc không có quyền!")
                self.session_expired.emit()
                self.session_timer.stop()
        except requests.RequestException:
            QMessageBox.information(self, "Thông báo", "Không thể kết nối server!")
            self.session_expired.emit()
            self.session_timer.stop()

    def logout(self):
        """Xử lý đăng xuất."""
        self.settings.token = ""
        save_client_data(self.settings, self.pin) 
        self.session_expired.emit()
        self.session_timer.stop()

class ClientApp(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.addWidget(self.login_window)
        self.main_window = None
        self.setMinimumSize(900, 700)
        self.show()

    def on_login_success(self, settings, pin):
        """Xử lý khi đăng nhập thành công."""
        self.main_window = MainWindow(settings, pin) 
        self.main_window.session_expired.connect(self.on_session_expired)
        self.addWidget(self.main_window)
        self.setCurrentWidget(self.main_window)

    def on_session_expired(self):
        """Xử lý khi session hết hạn."""
        QMessageBox.information(self, "Thông báo", "Session hết hạn. Vui lòng đăng nhập lại!")
        self.setCurrentWidget(self.login_window)
        if self.main_window:
            self.removeWidget(self.main_window)
            self.main_window = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = ClientApp()
    sys.exit(app.exec())