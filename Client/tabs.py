import json
import base64
import secrets
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFormLayout, QDialog, QComboBox, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QLabel, QMessageBox, QLineEdit, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import requests
import cv2
import numpy as np

# Tab quản lý tài khoản
class AccountTab(QWidget):
    def __init__(self, settings, api_client, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.api_client = api_client
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Tạo bảng hiển thị tài khoản
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Password", "Permissions", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # Tạo các nút chức năng
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_account)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_account)
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.update_account)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        for btn in [self.btn_add, self.btn_delete, self.btn_update, self.btn_refresh]:
            btn.setMinimumHeight(35)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)
        self.load_data()

    def load_data(self):
        """Tải dữ liệu tài khoản từ API và hiển thị lên bảng với kích thước cột phân chia đều."""
        try:
            resp = self.api_client.get_accounts()
            if resp.status_code == 200:
                accounts = resp.json().get("data", [])

                # Xóa toàn bộ nội dung cũ trước khi load mới
                self.table.clearContents()
                self.table.setRowCount(0)

                # Cập nhật số dòng
                self.table.setRowCount(len(accounts))
                for i, acc in enumerate(accounts):
                    self.table.setItem(i, 0, QTableWidgetItem(str(acc.get("id", ""))))
                    self.table.setItem(i, 1, QTableWidgetItem(acc.get("username", "")))
                    self.table.setItem(i, 2, QTableWidgetItem(acc.get("password", "")))
                    self.table.setItem(i, 3, QTableWidgetItem(str(acc.get("permissions", ""))))
                    self.table.setItem(i, 4, QTableWidgetItem(acc.get("status", "")))

                # Điều chỉnh lại kích thước cột đồng đều
                header = self.table.horizontalHeader()
                for col in range(self.table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Stretch)

            elif resp.status_code == 403:
                QMessageBox.warning(self, "Error", "No permission to view Account tab")
                self.setEnabled(False)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")



    def add_account(self):
        """Hiển thị dialog để thêm tài khoản mới."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Account")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        username = QLineEdit()
        password = QLineEdit()
        permissions = QListWidget()
        for perm in ["home", "zone", "monitor"]:
            item = QListWidgetItem(perm)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            permissions.addItem(item)
        status = QComboBox()
        status.addItems(["active", "inactive"])
        layout.addRow("Username:", username)
        layout.addRow("Password:", password)
        layout.addRow("Permissions:", permissions)
        layout.addRow("Status:", status)
        btn = QPushButton("Add")
        btn.clicked.connect(lambda: self.send_add_account(dialog, username.text(), password.text(), permissions, status.currentText()))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def send_add_account(self, dialog, username, password, permissions, status):
        """Gửi yêu cầu thêm tài khoản lên API."""
        try:
            perms = [item.text() for item in [permissions.item(i) for i in range(permissions.count())] if item.checkState() == Qt.Checked]
            data = {"username": username, "password": password, "permissions": perms, "status": status}
            resp = self.api_client.add_account(data)
            if resp.status_code == 201:
                QMessageBox.information(self, "Success", "Account added successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Add failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def delete_account(self):
        """Xóa tài khoản được chọn."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Error", "Please select an account to delete!")
            return
        id_text = self.table.item(selected, 0).text()
        try:
            resp = self.api_client.delete_account(id_text)
            if resp.status_code == 200:
                QMessageBox.information(self, "Success", "Account deleted successfully!")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", f"Delete failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def update_account(self):
        """Hiển thị dialog để cập nhật tài khoản."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Error", "Please select an account to update!")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Account")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        id_text = self.table.item(selected, 0).text()
        account_data = self.get_account_data(id_text)
        username = QLineEdit(account_data.get("username", ""))
        password = QLineEdit(account_data.get("password", ""))
        permissions = QListWidget()
        current_perms = account_data.get("permissions", [])
        for perm in ["home", "zone", "monitor"]:
            item = QListWidgetItem(perm)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if perm in current_perms else Qt.Unchecked)
            permissions.addItem(item)
        status = QComboBox()
        status.addItems(["active", "inactive"])
        status.setCurrentText(account_data.get("status", "active"))
        layout.addRow("Username:", username)
        layout.addRow("Password:", password)
        layout.addRow("Permissions:", permissions)
        layout.addRow("Status:", status)
        btn = QPushButton("Update")
        btn.clicked.connect(lambda: self.send_update_account(dialog, id_text, username.text(), password.text(), permissions, status.currentText()))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def get_account_data(self, account_id):
        """Lấy dữ liệu chi tiết của tài khoản từ API."""
        try:
            resp = self.api_client.get_accounts()
            if resp.status_code == 200:
                accounts = resp.json().get("data", [])
                for acc in accounts:
                    if str(acc.get("id")) == str(account_id):
                        return acc
            return {"username": "", "password": "", "permissions": [], "status": "active"}
        except requests.RequestException:
            return {"username": "", "password": "", "permissions": [], "status": "active"}

    def send_update_account(self, dialog, id, username, password, permissions, status):
        """Gửi yêu cầu cập nhật tài khoản lên API."""
        try:
            perms = [item.text() for item in [permissions.item(i) for i in range(permissions.count())] if item.checkState() == Qt.Checked]
            data = {"id": int(id), "username": username, "password": password, "permissions": perms, "status": status}
            resp = self.api_client.update_account(data)
            if resp.status_code == 200:
                QMessageBox.information(self, "Success", "Account updated successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Update failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

class ZoneTab(QWidget):
    def __init__(self, settings, api_client, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.api_client = api_client
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Tạo bảng hiển thị vùng
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Mode", "People Count", "Max Zone"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # Tạo các nút chức năng
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_zone)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_zone)
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.update_zone)
        self.btn_detail = QPushButton("Details")
        self.btn_detail.clicked.connect(self.show_zone_detail)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        for btn in [self.btn_add, self.btn_delete, self.btn_update, self.btn_detail, self.btn_refresh]:
            btn.setMinimumHeight(35)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.load_data()

    def tab_activated(self):
        """Kích hoạt timer khi tab được chọn."""
        self.timer.start(4000)

    def tab_deactivated(self):
        """Tắt timer khi tab không được chọn."""
        self.timer.stop()

    def load_data(self):
        """Tải dữ liệu vùng từ API và cập nhật bảng với màu sắc, giữ nguyên hàng đã chọn."""
        from settings import load_zone_thresholds
        zone_thresholds = load_zone_thresholds()
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                if not isinstance(zones, list):
                    QMessageBox.warning(self, "Error", "Invalid data format from server!")
                    return

                # Lưu hàng đang chọn
                selected_row = self.table.currentRow()
                selected_id = self.table.item(selected_row, 0).text() if selected_row >= 0 else None

                # Xóa nội dung bảng trước khi thêm mới
                self.table.clearContents()
                self.table.setRowCount(0)

                # Thêm dữ liệu mới
                self.table.setRowCount(len(zones))
                for i, zone in enumerate(zones):
                    if not isinstance(zone, dict):
                        continue

                    self.table.setItem(i, 0, QTableWidgetItem(str(zone.get("id", ""))))
                    self.table.setItem(i, 1, QTableWidgetItem(zone.get("name", "")))
                    self.table.setItem(i, 2, QTableWidgetItem(zone.get("mode", "max")))
                    self.table.setItem(i, 3, QTableWidgetItem(str(zone.get("people_count", 0))))
                    maxzone = zone_thresholds.get(str(zone.get("id", "")), 10)
                    self.table.setItem(i, 4, QTableWidgetItem(str(maxzone)))

                    # Cập nhật màu sắc
                    count = zone.get("people_count", 0)
                    color = QColor("green") if count < maxzone * 0.8 else QColor("yellow") if count <= maxzone else QColor("red")
                    for col in range(5):
                        item = self.table.item(i, col)
                        if item:
                            item.setBackground(color)

                    # Khôi phục hàng đã chọn
                    if selected_id and str(zone.get("id", "")) == selected_id:
                        self.table.selectRow(i)

                # Cập nhật giao diện bảng
                self.table.resizeColumnsToContents()
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            elif resp.status_code == 403:
                QMessageBox.warning(self, "Error", "No permission to view Zone tab")
                self.setEnabled(False)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")



    def add_zone(self):
        """Hiển thị dialog để thêm vùng mới."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Zone")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        name = QLineEdit()
        mode = QComboBox()
        mode.addItems(["max", "min", "avg"])
        maxzone = QLineEdit()
        monitors = QListWidget()
        self.populate_monitors(monitors)
        layout.addRow("Name:", name)
        layout.addRow("Mode:", mode)
        layout.addRow("Max Zone:", maxzone)
        layout.addRow("Monitors:", monitors)
        btn = QPushButton("Add")
        btn.clicked.connect(lambda: self.send_add_zone(dialog, name.text(), mode.currentText(), maxzone.text(), monitors))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def populate_monitors(self, list_widget):
        """Điền danh sách monitor vào QListWidget."""
        try:
            resp = self.api_client.get_monitors()
            if resp.status_code == 200:
                monitors = resp.json().get("data", [])
                for m in monitors:
                    item = QListWidgetItem(m["name"])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    list_widget.addItem(item)
        except requests.RequestException:
            pass

    def send_add_zone(self, dialog, name, mode, maxzone, monitors):
        """Gửi yêu cầu thêm vùng lên API."""
        try:
            selected_monitors = [item.text() for item in [monitors.item(i) for i in range(monitors.count())] if item.checkState() == Qt.Checked]
            data = {"name": name, "mode": mode, "monitors": selected_monitors}
            resp = self.api_client.add_zone(data)
            if resp.status_code == 201:
                zone_id = resp.json().get("id", self.get_last_zone_id())
                from settings import load_zone_thresholds, save_zone_thresholds
                zone_thresholds = load_zone_thresholds()
                zone_thresholds[str(zone_id)] = int(maxzone or 10)
                save_zone_thresholds(zone_thresholds)
                QMessageBox.information(self, "Success", "Zone added successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Add failed: {resp.json().get('message', 'Unknown error')}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Max Zone must be a number!")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def get_last_zone_id(self):
        """Lấy ID của vùng cuối cùng nếu API không trả về ID."""
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                return zones[-1]["id"] if zones else 1
            return 1
        except:
            return 1

    def delete_zone(self):
        """Xóa vùng được chọn."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Error", "Please select a zone to delete!")
            return
        id_text = self.table.item(selected, 0).text()
        try:
            resp = self.api_client.delete_zone(id_text)
            if resp.status_code == 200:
                from settings import load_zone_thresholds, save_zone_thresholds
                zone_thresholds = load_zone_thresholds()
                if id_text in zone_thresholds:
                    del zone_thresholds[id_text]
                    save_zone_thresholds(zone_thresholds)
                QMessageBox.information(self, "Success", "Zone deleted successfully!")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", f"Delete failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def update_zone(self):
        """Hiển thị dialog để cập nhật vùng."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Error", "Please select a zone to update!")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Zone")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        id_text = self.table.item(selected, 0).text()
        zone_data = self.get_zone_data(id_text)
        name = QLineEdit(zone_data.get("name", ""))
        mode = QComboBox()
        mode.addItems(["max", "min", "avg"])
        mode.setCurrentText(zone_data.get("mode", "max"))
        from settings import load_zone_thresholds
        zone_thresholds = load_zone_thresholds()
        maxzone = QLineEdit(str(zone_thresholds.get(id_text, 10)))
        monitors = QListWidget()
        self.populate_monitors(monitors)
        current_monitors = zone_data.get("monitors", [])
        for i in range(monitors.count()):
            item = monitors.item(i)
            if item.text() in current_monitors:
                item.setCheckState(Qt.Checked)
        layout.addRow("Name:", name)
        layout.addRow("Mode:", mode)
        layout.addRow("Max Zone:", maxzone)
        layout.addRow("Monitors:", monitors)
        btn = QPushButton("Update")
        btn.clicked.connect(lambda: self.send_update_zone(dialog, id_text, name.text(), mode.currentText(), maxzone.text(), monitors))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def get_zone_data(self, zone_id):
        """Lấy dữ liệu chi tiết của vùng từ API."""
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                for zone in zones:
                    if str(zone.get("id")) == str(zone_id):
                        return zone
            return {}
        except requests.RequestException:
            return {}

    def send_update_zone(self, dialog, id, name, mode, maxzone, monitors):
        """Gửi yêu cầu cập nhật vùng lên API."""
        try:
            selected_monitors = [item.text() for item in [monitors.item(i) for i in range(monitors.count())] if item.checkState() == Qt.Checked]
            data = {"id": int(id), "name": name, "mode": mode, "monitors": selected_monitors}
            resp = self.api_client.update_zone(data)
            if resp.status_code == 200:
                from settings import load_zone_thresholds, save_zone_thresholds
                zone_thresholds = load_zone_thresholds()
                zone_thresholds[id] = int(maxzone or 10)
                save_zone_thresholds(zone_thresholds)
                QMessageBox.information(self, "Success", "Zone updated successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Update failed: {resp.json().get('message', 'Unknown error')}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Max Zone must be a number!")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def show_zone_detail(self):
        """Hiển thị chi tiết của vùng được chọn."""
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Error", "Please select a zone to view details!")
            return
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                zone = zones[selected]
                monitors = zone.get("monitors", [])
                from settings import load_zone_thresholds
                zone_thresholds = load_zone_thresholds()
                details = f"ID: {zone['id']}\nName: {zone['name']}\nMode: {zone['mode']}\nPeople Count: {zone['people_count']}\nMax Zone: {zone_thresholds.get(str(zone['id']), 10)}\n\nMonitors:\n"
                m_resp = self.api_client.get_monitors()
                if m_resp.status_code == 200:
                    for m in monitors:
                        for monitor in m_resp.json().get("data", []):
                            if monitor["name"] == m:
                                details += f"- {m}: {monitor['people_count']} people\n"
                QMessageBox.information(self, "Zone Details", details)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

# Tab quản lý monitor
class MonitorTab(QWidget):
    def __init__(self, settings, api_client, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.api_client = api_client
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Tạo khu vực cuộn để hiển thị các monitor
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.content_widget.setLayout(self.grid_layout)
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)

        # Tạo các nút chức năng
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_monitor)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_monitor)
        self.btn_update = QPushButton("Update")
        self.btn_update.clicked.connect(self.update_monitor)
        self.btn_reset = QPushButton("Reset Counter")
        self.btn_reset.clicked.connect(self.reset_monitor_counter)
        self.btn_detail = QPushButton("Details")
        self.btn_detail.clicked.connect(self.show_monitor_detail)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_data)
        for btn in [self.btn_add, self.btn_delete, self.btn_update, self.btn_reset, self.btn_detail, self.btn_refresh]:
            btn.setMinimumHeight(35)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)

        self.selected_monitor = None
        self.selected_monitor_box = None
        self.monitor_boxes = []

        # Thiết lập timer để tự động làm mới
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.load_data()

    def tab_activated(self):
        """Kích hoạt timer khi tab được chọn."""
        self.timer.start(2000)

    def tab_deactivated(self):
        """Tắt timer khi tab không được chọn."""
        self.timer.stop()

    def load_data(self):
        """Tải dữ liệu monitor từ API và hiển thị dưới dạng lưới."""
        try:
            resp = self.api_client.get_monitors()
            if resp.status_code == 200:
                monitors = resp.json().get("data", [])
                selected_name = self.selected_monitor["name"] if self.selected_monitor else None

                # Lấy danh sách monitor hiện có
                current_monitors = {box.monitor_data["name"]: box for box in self.monitor_boxes if "name" in box.monitor_data}

                # Cập nhật hoặc thêm mới các monitor
                new_monitor_boxes = []
                row = 0
                col = 0
                for monitor in monitors:
                    name = monitor.get("name")
                    if name in current_monitors:
                        # Cập nhật dữ liệu cho widget hiện có
                        box = current_monitors[name]
                        box.update_data(monitor)
                    else:
                        # Tạo mới MonitorBox
                        box = MonitorBox(monitor)
                        box.clicked.connect(lambda checked, m=monitor, b=box: self.select_monitor(m, b))
                        box.doubleClicked.connect(lambda m=monitor: self.show_monitor_detail(monitor=m))
                        self.grid_layout.addWidget(box, row, col)
                        col += 1
                        if col == 2:  # Sắp xếp 2 cột
                            col = 0
                            row += 1
                    new_monitor_boxes.append(box)

                # Xóa các monitor không còn trong danh sách
                for name, box in current_monitors.items():
                    if name not in [m.get("name") for m in monitors]:
                        self.grid_layout.removeWidget(box)
                        box.deleteLater()

                self.monitor_boxes = new_monitor_boxes

                # Cập nhật monitor được chọn nếu có
                if selected_name:
                    for box in self.monitor_boxes:
                        if box.monitor_data.get("name") == selected_name:
                            self.select_monitor(box.monitor_data, box)
                            break
            elif resp.status_code == 403:
                QMessageBox.warning(self, "Error", "No permission to view Monitor tab")
                self.setEnabled(False)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def select_monitor(self, monitor, box):
        """Chọn monitor và cập nhật giao diện."""
        if self.selected_monitor_box and self.selected_monitor_box in self.monitor_boxes:
            self.selected_monitor_box.setStyleSheet(self.selected_monitor_box.default_stylesheet)
        self.selected_monitor = monitor
        self.selected_monitor_box = box
        box.setStyleSheet(self.selected_monitor_box.default_stylesheet + "border: 2px solid #00FF00;")

    def add_monitor(self):
        """Hiển thị dialog để thêm monitor mới."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Monitor")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        name = QLineEdit()
        key = QLineEdit()
        gen_key_btn = QPushButton("Generate Key")
        gen_key_btn.clicked.connect(lambda: key.setText(secrets.token_hex(9)[:19]))
        layout.addRow("Name:", name)
        layout.addRow("Key:", key)
        layout.addWidget(gen_key_btn)
        btn = QPushButton("Add")
        btn.clicked.connect(lambda: self.send_add_monitor(dialog, name.text(), key.text()))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def send_add_monitor(self, dialog, name, key):
        """Gửi yêu cầu thêm monitor lên API."""
        try:
            data = {"name": name, "key": key}
            resp = self.api_client.add_monitor(data)
            if resp.status_code == 201:
                QMessageBox.information(self, "Success", "Monitor added successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Add failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def delete_monitor(self):
        """Xóa monitor được chọn."""
        if not self.selected_monitor:
            QMessageBox.warning(self, "Error", "Please select a monitor to delete!")
            return
        try:
            resp = self.api_client.delete_monitor(self.selected_monitor['id'])
            if resp.status_code == 200:
                QMessageBox.information(self, "Success", "Monitor deleted successfully!")
                self.selected_monitor = None
                self.selected_monitor_box = None
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", f"Delete failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def update_monitor(self):
        """Hiển thị dialog để cập nhật monitor."""
        if not self.selected_monitor:
            QMessageBox.warning(self, "Error", "Please select a monitor to update!")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Monitor")
        dialog.setMinimumWidth(300)
        layout = QFormLayout()
        name = QLineEdit(self.selected_monitor["name"])
        key = QLineEdit(self.selected_monitor["key"])
        gen_key_btn = QPushButton("Generate Key")
        gen_key_btn.clicked.connect(lambda: key.setText(secrets.token_hex(9)[:19]))
        layout.addRow("Name:", name)
        layout.addRow("Key:", key)
        layout.addWidget(gen_key_btn)
        btn = QPushButton("Update")
        btn.clicked.connect(lambda: self.send_update_monitor(dialog, self.selected_monitor["id"], name.text(), key.text()))
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

    def send_update_monitor(self, dialog, id, name, key):
        """Gửi yêu cầu cập nhật monitor lên API."""
        try:
            data = {"id": int(id), "name": name, "key": key}
            resp = self.api_client.update_monitor(data)
            if resp.status_code == 200:
                QMessageBox.information(self, "Success", "Monitor updated successfully!")
                self.load_data()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", f"Update failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def reset_monitor_counter(self):
        """Đặt lại bộ đếm của monitor được chọn."""
        if not self.selected_monitor:
            QMessageBox.warning(self, "Error", "Please select a monitor to reset counter!")
            return
        try:
            name = self.selected_monitor["name"]
            key = self.selected_monitor["key"]
            resp = self.api_client.reset_monitor_counter(name, key)
            if resp.status_code == 200:
                QMessageBox.information(self, "Success", "Counter reset successfully!")
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", f"Reset failed: {resp.json().get('message', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def show_monitor_detail(self, monitor=None):
        """Hiển thị chi tiết của monitor được chọn mà không hiển thị base64."""
        if not monitor and not self.selected_monitor:
            QMessageBox.warning(self, "Error", "Please select a monitor to view details!")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Monitor Details")
        layout = QVBoxLayout()
        image_label = QLabel()
        image_label.setFixedSize(320, 240)
        image_b64 = monitor.get("image")
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
                    image_label.setPixmap(pixmap.scaled(image_label.size(), Qt.KeepAspectRatio))
                else:
                    image_label.setText("Unable to load image")
                    image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")
            except Exception as e:
                image_label.setText(f"Image load error: {str(e)}")
                image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")
        else:
            image_label.setText("No image available")
            image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")
        layout.addWidget(image_label)
        details = QLabel("\n".join([f"{k}: {v}" for k, v in monitor.items() if k != "image"]))
        layout.addWidget(details)
        dialog.setLayout(layout)
        dialog.exec()

class MonitorBox(QFrame):
    clicked = Signal(bool)
    doubleClicked = Signal()

    def __init__(self, monitor_data: dict):
        super().__init__()
        self.monitor_data = monitor_data
        self.setFrameShape(QFrame.Box)
        self.setFixedSize(400, 200)
        
        # Stylesheet mặc định
        self.default_stylesheet = """
            QFrame {
                border: 2px solid #555;
                background-color: #333;
                padding: 10px;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """
        self.setStyleSheet(self.default_stylesheet)
        
        # Layout chính
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Hiển thị hình ảnh
        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 150)
        self.image_label.setStyleSheet("background-color: black; border-radius: 8px;")
        layout.addWidget(self.image_label)
        
        # Hiển thị thông tin
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        self.name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setStyleSheet("color: white; font-size: 14px;")
        name_label.setFixedWidth(80)
        self.name_value = QLabel(monitor_data.get('name', 'Unknown'))
        self.name_value.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.name_layout.addWidget(name_label)
        self.name_layout.addWidget(self.name_value)
        info_layout.addLayout(self.name_layout)
        
        self.count_layout = QHBoxLayout()
        count_label = QLabel("People Count:")
        count_label.setStyleSheet("color: white; font-size: 8px;")
        count_label.setFixedWidth(80)
        self.count_value = QLabel(str(monitor_data.get('people_count', 0)))
        self.count_value.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.count_layout.addWidget(count_label)
        self.count_layout.addWidget(self.count_value)
        info_layout.addLayout(self.count_layout)
        
        layout.addLayout(info_layout)
        layout.setStretch(0, 2)  # Hình ảnh chiếm 2 phần
        layout.setStretch(1, 3)  # Thông tin chiếm 3 phần
        
        self.setLayout(layout)

    def update_data(self, new_data: dict):
        """Cập nhật dữ liệu mà không xóa widget."""
        self.monitor_data = new_data
        self.name_value.setText(new_data.get('name', 'Unknown'))
        self.count_value.setText(str(new_data.get('people_count', 0)))
        self.update_image()

    def update_image(self):
        """Cập nhật hình ảnh của monitor."""
        image_b64 = self.monitor_data.get("image")
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
                    self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.image_label.setText("Unable to load image")
                    self.image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")
            except Exception as e:
                self.image_label.setText(f"Error: {str(e)}")
                self.image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")
        else:
            self.image_label.setText("No image available")
            self.image_label.setStyleSheet("background-color: black; border: 1px solid white; color: white; text-align: center;")

    def mousePressEvent(self, event):
        """Phát tín hiệu khi nhấp chuột."""
        if self.isVisible():  # Kiểm tra widget còn hiển thị không
            self.clicked.emit(True)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Phát tín hiệu khi nhấp đúp chuột."""
        if self.isVisible():  # Kiểm tra widget còn hiển thị không
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
# Tab cài đặt
class SettingTab(QWidget):
    def __init__(self, settings, pin, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.pin = pin
        self.parent_tab_widget = parent_tab_widget
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()

        # Chọn font
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Times New Roman", "Helvetica", "Courier"])
        self.font_combo.setCurrentText(self.settings.font)
        self.font_combo.currentTextChanged.connect(self.apply_font)
        form.addRow("Font:", self.font_combo)

        # Chọn kích thước font
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["8", "10", "12", "14", "16"])
        self.font_size_combo.setCurrentText(str(self.settings.font_size))
        self.font_size_combo.currentTextChanged.connect(self.apply_font_size)
        form.addRow("Font Size:", self.font_size_combo)

        # Thay đổi PIN
        self.new_pin_edit = QLineEdit()
        self.new_pin_edit.setPlaceholderText("Enter new PIN (4 or 8 digits)")
        self.new_pin_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Change PIN:", self.new_pin_edit)

        self.btn_save_pin = QPushButton("Save New PIN")
        self.btn_save_pin.setMinimumHeight(40)
        self.btn_save_pin.clicked.connect(self.save_pin)

        layout.addLayout(form)
        layout.addWidget(self.btn_save_pin)
        layout.addStretch()
        self.setLayout(layout)

    def apply_font(self):
        """Áp dụng font được chọn."""
        self.settings.font = self.font_combo.currentText()
        from PySide6.QtGui import QFont
        font = QFont(self.settings.font, self.settings.font_size)
        self.parent_tab_widget.window().setFont(font)
        from settings import save_client_data
        save_client_data(self.settings, self.pin)

    def apply_font_size(self):
        """Áp dụng kích thước font được chọn."""
        try:
            self.settings.font_size = int(self.font_size_combo.currentText())
            from PySide6.QtGui import QFont
            font = QFont(self.settings.font, self.settings.font_size)
            self.parent_tab_widget.window().setFont(font)
            from settings import save_client_data
            save_client_data(self.settings, self.pin)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error applying font size: {str(e)}")

    def save_pin(self):
        """Lưu PIN mới."""
        try:
            new_pin = self.new_pin_edit.text().strip()
            if new_pin:
                if len(new_pin) not in (4, 8) or not new_pin.isdigit():
                    QMessageBox.warning(self, "Error", "PIN must be 4 or 8 digits!")
                    return
                from settings import save_client_data
                self.pin = new_pin
                save_client_data(self.settings, self.pin)
                QMessageBox.information(self, "Success", "PIN changed successfully!")
            else:
                QMessageBox.warning(self, "Error", "Please enter a new PIN!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error saving PIN: {str(e)}")