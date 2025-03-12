import requests
import time
import base64
import json
import cv2
from kivy.clock import Clock

class ServerConnector:
    def __init__(self, server_url, key, name):
        self.server_url = server_url
        self.key = key
        self.name = name
        self.connected = False
        self.latency = None
        self.request_count = 0

    def connect(self):
        data = {'key': self.key, 'name': self.name}
        try:
            start_time = time.time()
            response = requests.post(f"{self.server_url}/connect", json=data,verify=True)
            self.latency = (time.time() - start_time) * 1000
            if response.status_code == 200:
                self.connected = True
                print("Kết nối thành công!")
                return True
            print("Kết nối thất bại!")
            return False
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            return False

    def send_people_count(self, people_count, frame=None):
        if not self.connected:
            print("Chưa kết nối, không thể gửi dữ liệu!")
            return False
        data = {'key': self.key, 'name': self.name, 'people_count': people_count}
        self.request_count += 1
        if self.request_count % 10 == 0 and frame is not None:
            width = 320

            height = int(frame.shape[0] * (width / frame.shape[1]))
            resized_frame = cv2.resize(frame, (width, height))
            success, encoded_image = cv2.imencode('.png', resized_frame)
            if success:
                image_base64 = base64.b64encode(encoded_image).decode('utf-8')
                data['image'] = image_base64
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(f"{self.server_url}/update_count", json=data, headers=headers,verify=True)
            if response.status_code == 200:
                try:
                    resp_data = response.json()
                    if resp_data.get("action") == "Reset Counter" and hasattr(self, 'app'):
                        Clock.schedule_once(lambda dt: setattr(self.app, 'people_count', 0))
                except Exception as e:
                    print("Lỗi xử lý phản hồi JSON:", e)
                return True
            print(f"Lỗi gửi dữ liệu: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            self.connected = False
            print(f"Lỗi khi gửi dữ liệu: {e}")
            return False