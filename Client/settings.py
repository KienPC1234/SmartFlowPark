import json
import os
from secure_settings import SecureSettings

DATA_FILE = "client_data.dat"
SETTINGS_FILE = "settings.json"
ZONE_THRESHOLDS_FILE = "zone_thresholds.json"

class ClientSettings:
    def __init__(self):
        self.server_ip = "127.0.0.1"
        self.server_port = 8080
        self.username = ""
        self.password = ""
        self.token = ""
        self.pin_hash = ""
        self.salt = ""
        self.font = "Arial"
        self.font_size = 10
        self.theme = "Default Dark"
        self.bg_color = "Dark Gray"
        self.text_color = "White"
        self.permissions = []
        self.load_ui_settings()

    def to_dict(self):
        return {
            "server_ip": self.server_ip,
            "server_port": self.server_port,
            "username": self.username,
            "password": self.password,
            "token": self.token,
            "pin_hash": self.pin_hash,
            "salt": self.salt,
            "font": self.font,
            "font_size": self.font_size,
            "theme": self.theme,
            "bg_color": self.bg_color,
            "text_color": self.text_color,
            "permissions": self.permissions
        }

    def load(self, data: dict):
        self.__dict__.update(data)

    def load_ui_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    ui_settings = json.load(f)
                    self.font = ui_settings.get("font", "Arial")
                    self.font_size = ui_settings.get("font_size", 10)
                    self.theme = ui_settings.get("theme", "Dark")
                    self.bg_color = ui_settings.get("bg_color", "Dark Gray")
                    self.text_color = ui_settings.get("text_color", "White")
            except Exception as e:
                print(f"Error loading UI settings: {e}")

def save_client_data(settings: ClientSettings, pin: str):
    secure = SecureSettings(settings_file=DATA_FILE)
    secure.authenticate(pin)
    secure.save_settings(
        username=settings.username,
        ip=settings.server_ip,
        port=settings.server_port,
        pin=pin
    )
    secure.settings = secure.load_settings()
    settings.pin_hash = secure.settings["pin_hash"]
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    if settings.password:
        data["password"] = secure.encrypt_data(settings.password)
    else:
        data["password"] = ""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_client_data(pin: str) -> tuple[ClientSettings, bool]:
    secure = SecureSettings(settings_file=DATA_FILE)
    settings = ClientSettings()
    success = False
    if not os.path.exists(DATA_FILE):
        return settings, False
    try:
        secure.authenticate(pin)
        settings_data = secure.load_settings()
        if secure.verify_pin(pin):
            settings.username = settings_data["username"]
            settings.server_ip = settings_data["ip"]
            settings.server_port = int(settings_data["port"])
            settings.pin_hash = settings_data["pin_hash"]
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            if "password" in data:
                settings.password = secure.decrypt_data(data["password"])
            success = True
        else:
            print("PIN verification failed")
    except Exception as e:
        print(f"Load data failed: {e}")
    return settings, success

def save_ui_settings(settings: ClientSettings):
    try:
        ui_settings = {
            "font": settings.font,
            "font_size": settings.font_size,
            "theme": settings.theme,
            "bg_color": settings.bg_color,
            "text_color": settings.text_color
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(ui_settings, f, indent=4)
    except Exception as e:
        print(f"Error saving UI settings: {e}")

def load_zone_thresholds() -> dict:
    if os.path.exists(ZONE_THRESHOLDS_FILE):
        try:
            with open(ZONE_THRESHOLDS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Load zone thresholds failed: {e}")
    return {}

def save_zone_thresholds(zone_thresholds: dict):
    try:
        with open(ZONE_THRESHOLDS_FILE, "w") as f:
            json.dump(zone_thresholds, f, indent=4)
    except Exception as e:
        print(f"Save zone thresholds failed: {e}")