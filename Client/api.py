import requests

class ApiClient:
    def __init__(self, settings):
        self.settings = settings
        self.base_url = f"http://{settings.server_ip}:{settings.server_port}"
        self.headers = {"Authorization": settings.token}

    def login(self, username, password):
        url = f"{self.base_url}/login"
        return requests.post(url, json={"username": username, "password": password}, timeout=5)

    def get_accounts(self):
        url = f"{self.base_url}/app?type=accounts"
        return requests.get(url, headers=self.headers, timeout=5)

    def add_account(self, data):
        url = f"{self.base_url}/app?type=accounts"
        return requests.post(url, json=data, headers=self.headers, timeout=5)

    def delete_account(self, id):
        url = f"{self.base_url}/app?type=accounts&id={id}"
        return requests.delete(url, headers=self.headers, timeout=5)

    def update_account(self, data):
        url = f"{self.base_url}/app?type=accounts"
        return requests.put(url, json=data, headers=self.headers, timeout=5)

    def get_zones(self):
        url = f"{self.base_url}/app?type=zones"
        return requests.get(url, headers=self.headers, timeout=5)

    def add_zone(self, data):
        url = f"{self.base_url}/app?type=zones"
        return requests.post(url, json=data, headers=self.headers, timeout=5)

    def delete_zone(self, id):
        url = f"{self.base_url}/app?type=zones&id={id}"
        return requests.delete(url, headers=self.headers, timeout=5)

    def update_zone(self, data):
        url = f"{self.base_url}/app?type=zones"
        return requests.put(url, json=data, headers=self.headers, timeout=5)

    def get_monitors(self):
        url = f"{self.base_url}/app?type=monitors"
        return requests.get(url, headers=self.headers, timeout=5)

    def add_monitor(self, data):
        url = f"{self.base_url}/app?type=monitors"
        return requests.post(url, json=data, headers=self.headers, timeout=5)

    def delete_monitor(self, id):
        url = f"{self.base_url}/app?type=monitors&id={id}"
        return requests.delete(url, headers=self.headers, timeout=5)

    def update_monitor(self, data):
        url = f"{self.base_url}/app?type=monitors"
        return requests.put(url, json=data, headers=self.headers, timeout=5)
    
    def reset_monitor_counter(self, name, key):
        data = {"action": "reset", "name": name, "key": key}
        return requests.post(f"{self.base_url}/app?type=monitors",headers=self.headers, json=data, timeout=5)
    