import os
import json

class MonitorManager:
    def __init__(self, filename="giamsat.json"):
        self.filename = filename
        self.data = {"monitors": []}
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

    def add_monitor(self, monitor):
        self.data["monitors"].append(monitor)
        self.save()

    def update_monitor(self, index, monitor):
        self.data["monitors"][index] = monitor
        self.save()