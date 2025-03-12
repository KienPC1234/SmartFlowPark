from flask import Flask, request, jsonify
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import DictProperty
import random
import string
import threading
import cv2
import numpy as np
import base64

# Flask app
flask_app = Flask(__name__)

# Biến toàn cục lưu trữ dữ liệu client
connected_clients = {}

def generate_random_key(length=16):
    """Tạo key ngẫu nhiên với độ dài 16 ký tự"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_name(length=8):
    """Tạo tên ngẫu nhiên với độ dài 8 ký tự"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Tạo key và name mặc định
default_key = generate_random_key(16)
default_name = generate_random_name(8)
client_id = f"{default_key}_{default_name}"
connected_clients[client_id] = {'key': default_key, 'name': default_name, 'people_count': 0, 'image': None}

@flask_app.route('/connect', methods=['POST'])
def connect():
    data = request.get_json(silent=True)
    key = data.get('key') if data else None
    name = data.get('name') if data else None

    if not key or not name:
        key = default_key
        name = default_name

    client_id = f"{key}_{name}"
    connected_clients[client_id] = {'key': key, 'name': name, 'people_count': 0, 'image': None}
    print(f"[INFO] Client connected: key={key}, name={name}")
    return jsonify({"status": "OK", "key": key, "name": name}), 200

@flask_app.route('/update_count', methods=['POST'])
def update_count():
    data = request.get_json(silent=True)
    
    if not data:
        print("[ERROR] Request không có JSON data!")
        return jsonify({"status": "ERROR", "message": "Invalid request"}), 400

    key = data.get('key')
    name = data.get('name')
    people_count = data.get('people_count')
    image_base64 = data.get('image')

    if not key or not name or people_count is None:
        print("[ERROR] Request thiếu thông tin key, name hoặc people_count!")
        return jsonify({"status": "ERROR", "message": "Missing required fields"}), 400

    client_id = f"{key}_{name}"
    if client_id in connected_clients:
        connected_clients[client_id]['people_count'] = people_count
        if image_base64:
            connected_clients[client_id]['image'] = image_base64
            print(f"[INFO] Received image from {name} (key={key})")
        print(f"[INFO] Received update from {name} (key={key}): people_count={people_count}")
        return jsonify({"status": "OK"}), 200
    else:
        print(f"[WARNING] Unknown client: key={key}, name={name}")
        return jsonify({"status": "ERROR", "message": "Client not connected"}), 403

# Ứng dụng Kivy để hiển thị
class ServerMonitorApp(App):
    clients_data = DictProperty(connected_clients)

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Label tiêu đề
        self.title_label = Label(text="Server Monitor", font_size=24, size_hint=(1, 0.1))
        self.layout.add_widget(self.title_label)

        # Layout chứa thông tin client
        self.clients_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.8))
        self.layout.add_widget(self.clients_layout)

        # Cập nhật giao diện mỗi giây
        Clock.schedule_interval(self.update_ui, 1.0)
        return self.layout

    def update_ui(self, dt):
        """Cập nhật giao diện với dữ liệu từ connected_clients"""
        self.clients_layout.clear_widgets()
        for client_id, data in connected_clients.items():
            client_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=150, spacing=10)
            
            # Thông tin text
            info_label = Label(
                text=f"Name: {data['name']}\nKey: {data['key']}\nPeople Count: {data['people_count']}",
                size_hint=(0.4, 1)
            )
            client_box.add_widget(info_label)

            # Hiển thị ảnh nếu có
            image_widget = Image(size_hint=(0.6, 1))
            if data['image']:
                try:
                    # Giải mã base64 thành frame
                    image_data = base64.b64decode(data['image'])
                    nparray = np.frombuffer(image_data, np.uint8)
                    frame = cv2.imdecode(nparray, cv2.IMREAD_COLOR)
                    
                    # Tạo texture cho Kivy
                    texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
                    texture.blit_buffer(frame.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                    image_widget.texture = texture
                except Exception as e:
                    print(f"[ERROR] Failed to decode image for {client_id}: {e}")
            client_box.add_widget(image_widget)
            
            self.clients_layout.add_widget(client_box)

def run_flask():
    """Chạy Flask server trong thread riêng"""
    flask_app.run(host='127.0.0.1', port=8080, threaded=True)

if __name__ == "__main__":
    print("🚀 Server starting on http://127.0.0.1:8080...")
    print(f"🔑 Default Key: {default_key}")
    print(f"🆔 Default Name: {default_name}")

    # Chạy Flask trong thread riêng
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Chạy ứng dụng Kivy
    ServerMonitorApp().run()