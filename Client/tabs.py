import secrets
import base64
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFormLayout, QDialog, QComboBox, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QLabel, QMessageBox, QLineEdit, QHeaderView, QGridLayout, QMenu, QToolTip, QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
import requests
import cv2
import numpy as np
from api import GoogleGenAI
import markdown

class AccountTab(QWidget):
    def __init__(self, settings, api_client, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.api_client = api_client
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search accounts...")
        self.search_bar.textChanged.connect(self.filter_table)
        self.layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Password", "Permissions", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)

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
        try:
            resp = self.api_client.get_accounts()
            if resp.status_code == 200:
                accounts = resp.json().get("data", [])
                self.table.clearContents()
                self.table.setRowCount(0)
                self.table.setRowCount(len(accounts))
                for i, acc in enumerate(accounts):
                    self.table.setItem(i, 0, QTableWidgetItem(str(acc.get("id", ""))))
                    self.table.setItem(i, 1, QTableWidgetItem(acc.get("username", "")))
                    self.table.setItem(i, 2, QTableWidgetItem(acc.get("password", "")))
                    self.table.setItem(i, 3, QTableWidgetItem(str(acc.get("permissions", ""))))
                    self.table.setItem(i, 4, QTableWidgetItem(acc.get("status", "")))
                header = self.table.horizontalHeader()
                for col in range(self.table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
            elif resp.status_code == 403:
                QMessageBox.warning(self, "Error", "No permission to view Account tab")
                self.setEnabled(False)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def filter_table(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            row_visible = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            self.table.setRowHidden(row, not row_visible)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row == -1:
            return
        menu = QMenu(self)
        update_action = menu.addAction("Update")
        delete_action = menu.addAction("Delete")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == update_action:
            self.table.selectRow(row)
            self.update_account()
        elif action == delete_action:
            self.table.selectRow(row)
            self.delete_account()

    def add_account(self):
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

        self.gen_ai = GoogleGenAI()

        self.custom_request_input = QLineEdit()
        self.custom_request_input.setPlaceholderText("Enter custom request for AI (e.g., 'Focus on peak hours')")
        self.layout.addWidget(self.custom_request_input)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search zones...")
        self.search_bar.textChanged.connect(self.filter_table)
        self.layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Mode", "People Count", "Max Zone"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)

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
        self.timer.start(4000)

    def tab_deactivated(self):
        self.timer.stop()

    def load_data(self):
        from settings import load_zone_thresholds
        zone_thresholds = load_zone_thresholds()
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                if not isinstance(zones, list):
                    QMessageBox.warning(self, "Error", "Invalid data format from server!")
                    return

                selected_row = self.table.currentRow()
                selected_id = self.table.item(selected_row, 0).text() if selected_row >= 0 else None

                self.table.clearContents()
                self.table.setRowCount(0)
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

                    count = zone.get("people_count", 0)
                    if count < maxzone * 0.6:
                        color = QColor("green")
                    elif count <= maxzone * 0.8:
                        color = QColor("yellow")
                    else:
                        color = QColor("red")
                    for col in range(5):
                        item = self.table.item(i, col)
                        if item:
                            item.setBackground(color)

                    if maxzone * 0.6 <= count <= maxzone * 0.8:
                        warning = self.gen_ai.warn_people_management(zone, zone_thresholds)
                        pos = self.table.viewport().mapToGlobal(self.table.visualItemRect(self.table.item(i, 0)).bottomLeft())
                        QToolTip.showText(pos, warning, self.table)

                    if selected_id and str(zone.get("id", "")) == selected_id:
                        self.table.selectRow(i)

                self.table.resizeColumnsToContents()
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            elif resp.status_code == 403:
                QMessageBox.warning(self, "Error", "No permission to view Zone tab")
                self.setEnabled(False)
        except requests.RequestException as e:
            QMessageBox.warning(self, "Error", f"Connection failed: {str(e)}")

    def filter_table(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            row_visible = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            self.table.setRowHidden(row, not row_visible)

    def show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row == -1:
            return

        from settings import load_zone_thresholds
        zone_thresholds = load_zone_thresholds()
        zone = {
            "id": self.table.item(row, 0).text(),
            "name": self.table.item(row, 1).text(),
            "mode": self.table.item(row, 2).text(),
            "people_count": int(self.table.item(row, 3).text())
        }

        custom_request = self.custom_request_input.text()

        menu = QMenu(self)
        update_action = menu.addAction("Update")
        delete_action = menu.addAction("Delete")
        predict_action = menu.addAction("Predict People Count")
        suggest_action = menu.addAction("Suggest People Management")
        warn_action = menu.addAction("Warn People Management")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == update_action:
            self.table.selectRow(row)
            self.update_zone()
        elif action == delete_action:
            self.table.selectRow(row)
            self.delete_zone()
        elif action == predict_action:
            prediction = self.gen_ai.predict_people_count(zone, zone_thresholds, custom_request)
            self._show_html_popup(prediction, "Prediction")
        elif action == suggest_action:
            suggestion = self.gen_ai.suggest_people_management(zone, zone_thresholds, custom_request)
            self._show_html_popup(suggestion, "Suggestion")
        elif action == warn_action:
            warning = self.gen_ai.warn_people_management(zone, zone_thresholds, custom_request)
            self._show_html_popup(warning, "Warning")

    def _show_html_popup(self, markdown_content, title):
        html_content = markdown.markdown(markdown_content)
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout()
        browser = QTextBrowser()
        browser.setHtml(html_content)
        browser.setReadOnly(True)
        layout.addWidget(browser)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.setLayout(layout)
        dialog.exec_()

    def add_zone(self):
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
        try:
            resp = self.api_client.get_zones()
            if resp.status_code == 200:
                zones = resp.json().get("data", [])
                return zones[-1]["id"] if zones else 1
            return 1
        except:
            return 1

    def delete_zone(self):
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

class MonitorTab(QWidget):
    def __init__(self, settings, api_client, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.api_client = api_client
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search monitors by name...")
        self.search_bar.textChanged.connect(self.filter_monitors)
        self.layout.addWidget(self.search_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.content_widget.setLayout(self.grid_layout)
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)

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

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.load_data()

    def tab_activated(self):
        self.timer.start(2000)

    def tab_deactivated(self):
        self.timer.stop()

    def load_data(self):
        try:
            resp = self.api_client.get_monitors()
            if resp.status_code == 200:
                monitors = resp.json().get("data", [])
                selected_name = self.selected_monitor["name"] if self.selected_monitor else None

                current_monitors = {box.monitor_data["name"]: box for box in self.monitor_boxes if "name" in box.monitor_data}

                new_monitor_boxes = []
                row = 0
                col = 0
                for monitor in monitors:
                    name = monitor.get("name")
                    if name in current_monitors:
                        box = current_monitors[name]
                        box.update_data(monitor)
                    else:
                        box = MonitorBox(monitor)
                        box.clicked.connect(lambda checked, m=monitor, b=box: self.select_monitor(m, b))
                        box.doubleClicked.connect(lambda m=monitor: self.show_monitor_detail(monitor=m))
                        box.setContextMenuPolicy(Qt.CustomContextMenu)
                        box.customContextMenuRequested.connect(lambda pos, m=monitor, b=box: self.show_context_menu(pos, m, b))
                        self.grid_layout.addWidget(box, row, col)
                        col += 1
                        if col == 2:
                            col = 0
                            row += 1
                    new_monitor_boxes.append(box)

                for name, box in current_monitors.items():
                    if name not in [m.get("name") for m in monitors]:
                        self.grid_layout.removeWidget(box)
                        box.deleteLater()

                self.monitor_boxes = new_monitor_boxes

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

    def filter_monitors(self):
        search_text = self.search_bar.text().lower()
        for box in self.monitor_boxes:
            box.setVisible(search_text in box.monitor_data.get("name", "").lower())

    def show_context_menu(self, pos, monitor, box):
        menu = QMenu(self)
        update_action = menu.addAction("Update")
        delete_action = menu.addAction("Delete")
        reset_action = menu.addAction("Reset Counter")
        action = menu.exec_(box.mapToGlobal(pos))
        if action == update_action:
            self.select_monitor(monitor, box)
            self.update_monitor()
        elif action == delete_action:
            self.select_monitor(monitor, box)
            self.delete_monitor()
        elif action == reset_action:
            self.select_monitor(monitor, box)
            self.reset_monitor_counter()

    def select_monitor(self, monitor, box):
        if self.selected_monitor_box and self.selected_monitor_box in self.monitor_boxes:
            self.selected_monitor_box.setStyleSheet(self.selected_monitor_box.default_stylesheet)

        self.selected_monitor = monitor
        self.selected_monitor_box = box
        highlight_stylesheet = """
            QFrame {
                border: 2px solid #00FF00;
                background-color: #333;
                padding: 10px;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """
        box.setStyleSheet(highlight_stylesheet)

    def add_monitor(self):
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
        if not monitor and not self.selected_monitor:
            QMessageBox.warning(self, "Error", "Please select a monitor to view details!")
            return
        monitor = monitor or self.selected_monitor
        dialog = QDialog(self)
        dialog.setWindowTitle("Monitor Details")
        layout = QVBoxLayout()
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

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 150)
        self.image_label.setStyleSheet("background-color: black; border-radius: 8px;")
        layout.addWidget(self.image_label)

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
        count_label.setStyleSheet("color: white; font-size: 9px;")
        count_label.setFixedWidth(80)
        self.count_value = QLabel(str(monitor_data.get('people_count', 0)))
        self.count_value.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.count_layout.addWidget(count_label)
        self.count_layout.addWidget(self.count_value)
        info_layout.addLayout(self.count_layout)

        layout.addLayout(info_layout)
        layout.setStretch(0, 2)
        layout.setStretch(1, 3)

        self.setLayout(layout)
        self.setMouseTracking(True)
        self.update_image()

    def update_data(self, new_data: dict):
        self.monitor_data = new_data
        self.name_value.setText(new_data.get('name', 'Unknown'))
        self.count_value.setText(str(new_data.get('people_count', 0)))
        self.update_image()

    def update_image(self):
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
        if self.isVisible():
            self.clicked.emit(True)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.isVisible():
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class SettingTab(QWidget):
    apply_settings = Signal()

    def __init__(self, settings, parent_tab_widget):
        super().__init__()
        self.settings = settings
        self.parent_tab_widget = parent_tab_widget
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.form = QFormLayout()

        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Times New Roman", "Helvetica", "Courier"])
        self.font_combo.setCurrentText(self.settings.font)
        self.form.addRow("Font:", self.font_combo)

        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["8", "10", "12", "14", "16"])
        self.font_size_combo.setCurrentText(str(self.settings.font_size))
        self.form.addRow("Font Size:", self.font_size_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Default Dark"])
        self.theme_combo.setCurrentText(self.settings.theme if hasattr(self.settings, 'theme') else "Default Dark")
        self.form.addRow("Theme:", self.theme_combo)

        self.bg_color_combo = QComboBox()
        self.bg_color_combo.addItems(["White", "Light Gray", "Dark Gray", "Black"])
        self.bg_color_combo.setCurrentText(self.settings.bg_color if hasattr(self.settings, 'bg_color') else "Dark Gray")
        self.form.addRow("Background Color:", self.bg_color_combo)

        self.text_color_combo = QComboBox()
        self.text_color_combo.addItems(["Black", "White", "Gray", "Blue"])
        self.text_color_combo.setCurrentText(self.settings.text_color if hasattr(self.settings, 'text_color') else "White")
        self.form.addRow("Text Color:", self.text_color_combo)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.clicked.connect(self.apply_changes)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.apply_btn)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def apply_changes(self):
        try:
            self.settings.font = self.font_combo.currentText()
            self.settings.font_size = int(self.font_size_combo.currentText())
            self.settings.theme = self.theme_combo.currentText()
            self.settings.bg_color = self.bg_color_combo.currentText() if self.theme_combo.currentText() != "Default Dark" else "Dark Gray"
            self.settings.text_color = self.text_color_combo.currentText() if self.theme_combo.currentText() != "Default Dark" else "White"

            from settings import save_ui_settings
            save_ui_settings(self.settings)

            self.apply_settings.emit()
            QMessageBox.information(self, "Success", "Settings applied. Application will reset!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error applying settings: {str(e)}")