import os
import json

class SettingsManager:
    def __init__(self, filename="setting.json"):
        self.filename = filename
        self.data = {"server": {"ip": "127.0.0.1", "port": 8080}, "accounts": [], "zones": []}
        self.load()

    def load(self):
        if os.path.isfile(self.filename):
            try:
                with open(self.filename, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.save()
        else:
            self.save()

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_account(self, account):
        self.data["accounts"].append(account)
        self.save()

    def update_account(self, index, account):
        self.data["accounts"][index] = account
        self.save()

    def add_zone(self, zone):
        self.data["zones"].append(zone)
        self.save()

    def update_zone(self, index, zone):
        self.data["zones"][index] = zone
        self.save()