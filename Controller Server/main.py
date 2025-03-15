import sys
import threading
import os
from settings import SettingsManager
from monitor import MonitorManager
from flask_server import FlaskServer

def is_gui_supported():
    if sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        return False
    return True

def create_flask_app():
    settings_manager = SettingsManager()
    monitor_manager = MonitorManager()
    return FlaskServer(settings_manager, monitor_manager).app

def main():
    settings_manager = SettingsManager()
    monitor_manager = MonitorManager()
    
    flask_server = FlaskServer(settings_manager, monitor_manager)
    flask_thread = threading.Thread(target=flask_server.run)
    flask_thread.daemon = True
    flask_thread.start()
    
    if not is_gui_supported():
        print("GUI is not supported, running API server only...")
        flask_thread.join()
        return
    
    from PySide6.QtWidgets import QApplication, QDialog  
    from gui import LoginDialog, AccountCreationDialog, MainWindow
    
    app = QApplication(sys.argv)
    
    if not settings_manager.get_all_accounts():
        acct_dialog = AccountCreationDialog(settings_manager)
        if acct_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
    
    login_dialog = LoginDialog(settings_manager)
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    
    main_win = MainWindow(settings_manager, monitor_manager)
    main_win.show()
    sys.exit(app.exec())

app = create_flask_app()

if __name__ == "__main__":
    main()