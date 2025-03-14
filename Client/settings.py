import json
import os
from secure_settings import SecureSettings

DATA_FILE = "client_data.dat"
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
        self.permissions = []

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
            "permissions": self.permissions
        }
    
    def load(self, data: dict):
        self.__dict__.update(data)

def save_client_data(settings: ClientSettings, pin: str):
    """Lưu dữ liệu cài đặt bằng SecureSettings"""
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
    data["password"] = secure.encrypt_data(settings.password)  
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_client_data(pin: str) -> tuple[ClientSettings, bool]:
    """Tải dữ liệu cài đặt bằng SecureSettings"""
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
            settings.server_port = settings_data["port"]
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

def save_zone_thresholds(zone_thresholds: dict):
    try:
        with open(ZONE_THRESHOLDS_FILE, "w") as f:
            json.dump(zone_thresholds, f, indent=4)
    except Exception as e:
        print(f"Save zone thresholds failed: {e}")

def load_zone_thresholds() -> dict:
    if os.path.exists(ZONE_THRESHOLDS_FILE):
        try:
            with open(ZONE_THRESHOLDS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Load zone thresholds failed: {e}")
    return {}