import json
import os
import json
import os
import time
import base64
import hashlib
from argon2 import PasswordHasher, exceptions as argon_exceptions
from cryptography.fernet import Fernet

class SecureSettings:
    def __init__(self, settings_file="settings.json", salt_file="salt.bin"):
        self.settings_file = settings_file
        self.salt_file = salt_file
        self.ph = PasswordHasher()
        self.failed_attempts = 0
        self.lock_time = None
        self.salt = self.load_or_generate_salt()
        self.key = None  
        self.cipher = None
        self.settings = {}

    def derive_key(self, password):
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), self.salt, 300000)
        return base64.urlsafe_b64encode(key)

    def load_or_generate_salt(self):
        if os.path.exists(self.salt_file):
            with open(self.salt_file, "rb") as f:
                return f.read()
        salt = os.urandom(16)
        with open(self.salt_file, "wb") as f:
            f.write(salt)
        return salt

    def authenticate(self, password):
        if self.lock_time and time.time() < self.lock_time:
            raise Exception("🔒 Too many failed attempts! Try again later.")

        self.key = self.derive_key(password)
        self.cipher = Fernet(self.key)
        
        self.settings = self.load_settings()

    def encrypt_data(self, data):
        if not self.cipher:
            raise Exception("🔑 Password not set! Call `authenticate()` first.")
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, data):
        if not self.cipher:
            raise Exception("🔑 Password not set! Call `authenticate()` first.")
        try:
            return self.cipher.decrypt(data.encode()).decode()
        except Exception:
            raise Exception("⚠️ Data corrupted or incorrect password!")

    def save_settings(self, username, ip, port, pin):
        if not self.cipher:
            raise Exception("🔑 Password not set! Call `authenticate()` first.")

        hashed_pin = self.ph.hash(pin)
        encrypted_data = {
            "username": self.encrypt_data(username),
            "ip": self.encrypt_data(ip),
            "port": self.encrypt_data(str(port)),
            "pin_hash": hashed_pin
        }

        with open(self.settings_file, "w") as f:
            json.dump(encrypted_data, f)

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return {}

        try:
            with open(self.settings_file, "r") as f:
                encrypted_data = json.load(f)

            return {
                "username": self.decrypt_data(encrypted_data["username"]),
                "ip": self.decrypt_data(encrypted_data["ip"]),
                "port": int(self.decrypt_data(encrypted_data["port"])),
                "pin_hash": encrypted_data["pin_hash"]
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            raise Exception("⚠️ settings.json is corrupted or incorrectly formatted!")

    def verify_pin(self, pin):
        if self.lock_time and time.time() < self.lock_time:
            raise Exception("🔒 Too many failed attempts! Try again later.")

        try:
            if self.ph.verify(self.settings["pin_hash"], pin):
                self.failed_attempts = 0
                return True
        except argon_exceptions.VerifyMismatchError:
            self.failed_attempts += 1

        if self.failed_attempts >= 3:
            self.lock_time = time.time() + 60
            raise Exception("🔒 Too many failed attempts! Please wait 60 seconds.")

        return False


DATA_FILE = "client_data.dat"
SETTINGS_FILE = "settings.json"
ZONE_THRESHOLDS_FILE = "zone_thresholds.json"

class ClientSettings:
    def __init__(self):
        self.server_ip = "http://127.0.0.1"
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