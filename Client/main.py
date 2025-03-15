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
    reset_application = Signal()

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
        self.setting_tab = SettingTab(settings, self.tabs)
        self.setting_tab.apply_settings.connect(self.restart_application)

        self.tabs.addTab(self.account_tab, "Account")
        self.tabs.addTab(self.zone_tab, "Zone")
        self.tabs.addTab(self.monitor_tab, "Monitor")
        self.tabs.addTab(self.setting_tab, "Setting")

        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        self.tabs.tabBar().setTabButton(self.tabs.count() - 1, QTabBar.RightSide, self.logout_btn)

        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.check_session)
        self.session_timer.start(50000)

        self.apply_settings()

    def apply_settings(self):
        if self.settings.theme == "Default Dark":
            stylesheet = """
                QWidget {
                    background-color: #2C2F33;
                    color: #FFFFFF;
                    border: none;
                }
                QComboBox, QLineEdit, QPushButton {
                    background-color: #40444B;
                    color: #FFFFFF;
                    border: 1px solid #7289DA;
                    border-radius: 4px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #7289DA;
                    color: #FFFFFF;
                }
            """
        else:
            color_map = {
                "White": "white",
                "Light Gray": "#d3d3d3",
                "Dark Gray": "#555",
                "Black": "black"
            }
            text_color_map = {
                "Black": "black",
                "White": "white",
                "Gray": "gray",
                "Blue": "blue"
            }
            bg_color = color_map.get(self.settings.bg_color, "#555")
            text_color = text_color_map.get(self.settings.text_color, "white")
            if self.settings.theme == "Light":
                stylesheet = f"""
                    QWidget {{ background-color: {bg_color}; color: {text_color}; }}
                    QComboBox, QLineEdit, QPushButton {{ background-color: #f0f0f0; color: black; }}
                """
            else:
                stylesheet = f"""
                    QWidget {{ background-color: {bg_color}; color: {text_color}; }}
                    QComboBox, QLineEdit, QPushButton {{ background-color: #555; color: white; }}
                """
        self.setStyleSheet(stylesheet)
        font = QFont(self.settings.font, self.settings.font_size)
        self.setFont(font)

    def on_tab_changed(self, index):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'tab_deactivated'):
                tab.tab_deactivated()
        current_tab = self.tabs.widget(index)
        if hasattr(current_tab, 'tab_activated'):
            current_tab.tab_activated()

    def check_session(self):
        try:
            resp = self.api_client.get_accounts()
            if resp.status_code != 200:
                QMessageBox.information(self, "Notification", "Session expired or no permission!")
                self.session_expired.emit()
                self.session_timer.stop()
        except requests.RequestException:
            QMessageBox.information(self, "Notification", "Unable to connect to server!")
            self.session_expired.emit()
            self.session_timer.stop()

    def logout(self):
        self.settings.token = ""
        save_client_data(self.settings, self.pin)
        self.session_expired.emit()
        self.session_timer.stop()

    def restart_application(self):
        save_client_data(self.settings, self.pin)
        from settings import save_ui_settings
        save_ui_settings(self.settings)

        new_main_window = MainWindow(self.settings, self.pin)
        new_main_window.session_expired.connect(self.parent().on_session_expired)
        self.parent().addWidget(new_main_window)
        self.parent().setCurrentWidget(new_main_window)
        self.parent().removeWidget(self)
        self.deleteLater()

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
        self.main_window = MainWindow(settings, pin)
        self.main_window.session_expired.connect(self.on_session_expired)
        self.addWidget(self.main_window)
        self.setCurrentWidget(self.main_window)

    def on_session_expired(self):
        QMessageBox.information(self, "Notification", "Session expired. Please log in again!")
        self.setCurrentWidget(self.login_window)
        if self.main_window:
            self.removeWidget(self.main_window)
            self.main_window = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = ClientApp()
    sys.exit(app.exec())