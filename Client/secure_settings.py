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
