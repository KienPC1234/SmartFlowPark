import sys
import threading
import os
from settings import SettingsManager
from monitor import MonitorManager
from flask_server import FlaskServer

# Kiểm tra xem môi trường có hỗ trợ GUI không (Linux server thường không có DISPLAY)
def is_gui_supported():
    if sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        return False
    return True

def create_flask_app():
    settings_manager = SettingsManager()
    monitor_manager = MonitorManager()
    return FlaskServer(settings_manager, monitor_manager).app

def main():
    # Khởi tạo SettingsManager và MonitorManager với SQLite
    settings_manager = SettingsManager()
    monitor_manager = MonitorManager()
    
    # Khởi tạo FlaskServer với settings_manager và monitor_manager
    flask_server = FlaskServer(settings_manager, monitor_manager)
    flask_thread = threading.Thread(target=flask_server.run)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Nếu môi trường không hỗ trợ GUI, chỉ chạy server
    if not is_gui_supported():
        print("GUI không được hỗ trợ, chỉ chạy server API...")
        flask_thread.join()
        return
    
    # Nếu hỗ trợ GUI, import và chạy giao diện
    from PySide6.QtWidgets import QApplication, QDialog  
    from gui import LoginDialog, AccountCreationDialog, MainWindow
    
    app = QApplication(sys.argv)
    
    # Kiểm tra xem có tài khoản nào trong database chưa
    if not settings_manager.get_all_accounts():
        acct_dialog = AccountCreationDialog(settings_manager)
        if acct_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
    
    # Hiển thị dialog đăng nhập
    login_dialog = LoginDialog(settings_manager)
    if login_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    
    # Hiển thị cửa sổ chính
    main_win = MainWindow(settings_manager, monitor_manager)
    main_win.show()
    sys.exit(app.exec())

# Định nghĩa ứng dụng WSGI
app = create_flask_app()

if __name__ == "__main__":
    main()
