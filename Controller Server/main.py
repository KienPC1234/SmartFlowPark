import sys
import threading
from settings import SettingsManager
from monitor import MonitorManager
from flask_server import FlaskServer
from gui import LoginDialog, AccountCreationDialog, MainWindow
from PySide6.QtWidgets import QApplication, QDialog  # Thêm import này

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