import requests
from google import genai
import os, json

class ApiClient:
    def __init__(self, settings):
        self.settings = settings
        self.base_url = f"{settings.server_ip}:{settings.server_port}"
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
        return requests.post(f"{self.base_url}/app?type=monitors", headers=self.headers, json=data, timeout=5)
    
class GoogleGenAI:
    def __init__(self):
        self.api_key = "AIzaSyA1hn2RpP0rzLJuqUYTMDzsr_IFL8H41d8"
        self.model_name = "gemini-2.0-flash"
        self._load_or_create_settings()
        self.client = genai.Client(api_key=self.api_key)

    def _load_or_create_settings(self):
        settings_file = 'settings.json'
        default_settings = {'api_key': self.api_key, 'model': self.model_name}

        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                self.api_key = settings.get('api_key', self.api_key)
                self.model_name = settings.get('model', self.model_name)
            except Exception as e:
                print(f"Error reading {settings_file}: {e}. Using default values.")
                self._save_settings(default_settings, settings_file)
        else:
            self._save_settings(default_settings, settings_file)
            print(f"Created {settings_file} with default values.")

    def _save_settings(self, settings, settings_file):
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving {settings_file}: {e}")

    def _format_zone_details(self, zone, zone_thresholds):
        max_capacity = zone_thresholds.get(str(zone['id']), 10)
        return (
            f"Name: {zone['name']}\n"
            f"People Count: {zone['people_count']}\n"
            f"Max Capacity: {max_capacity}\n"
        )

    def predict_people_count(self, zone, zone_thresholds, custom_request=""):
        details = self._format_zone_details(zone, zone_thresholds)
        prompt = (
            f"Zone info:\n{details}\n"
            "Predict the people count in this zone for the next hour. "
            "Base your estimate on current count, capacity, and typical trends. "
            "Return a number and a brief explanation."
        )
        if custom_request:
            prompt += f"\nCustom request, data: {custom_request}"
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    def suggest_people_management(self, zone, zone_thresholds, custom_request=""):
        details = self._format_zone_details(zone, zone_thresholds)
        prompt = (
            f"Zone info:\n{details}\n"
            "Suggest practical ways to manage people in this zone. "
            "Consider current count and max capacity. "
            "Advise whether to increase, decrease, or maintain the number, with clear steps."
        )
        if custom_request:
            prompt += f"\nCustom request, data: {custom_request}"
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    def warn_people_management(self, zone, zone_thresholds, custom_request=""):
        details = self._format_zone_details(zone, zone_thresholds)
        people_count = zone['people_count']
        max_capacity = zone_thresholds.get(str(zone['id']), 10)

        if people_count > max_capacity * 0.8:
            level, urgency = "Red (Serious)", "Act immediately"
        elif people_count >= max_capacity * 0.6:
            level, urgency = "Yellow (Warning)", "Action advised"
        else:
            level, urgency = "Green (Normal)", "No action needed"

        prompt = (
            f"Zone info:\n{details}\n"
            f"Status: {level}\n"
            f"Urgency: {urgency}\n"
            "Provide a warning and clear instructions for managing people. "
            "For Yellow, suggest preventive steps. For Red, recommend urgent actions to reduce crowding."
        )
        if custom_request:
            prompt += f"\nCustom request, data: {custom_request}"
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text