import threading
import cv2
from ultralytics import YOLO
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty, StringProperty
import torch
import time
import json
import os, sys
from server_connector import ServerConnector

boundary_line = []
mouse_pos = None
crossed_ids = set()
prev_sides = {}
current_frame = None
stop_thread = False
clear_boundary_flag = False
frame_lock = threading.Lock()
boundary_lock = threading.Lock()

config = {'key': '', 'name': '', 'ip': '127.0.0.1', 'port': '8080', 'protocol': 'http'}
if os.path.exists('login.json'):
    try:
        with open('login.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading config file: {e}")

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO("model.pt", verbose=False).to(device)

class LoginPopup(Popup):
    def __init__(self, on_connect, saved_config, **kwargs):
        super(LoginPopup, self).__init__(**kwargs)
        self.title = 'Enter Connection Details'
        self.size_hint = (0.6, 0.6)
        self.auto_dismiss = False
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.key_input = TextInput(hint_text='Enter key', multiline=False, text=saved_config.get('key', ''))
        self.name_input = TextInput(hint_text='Enter monitor name', multiline=False, text=saved_config.get('name', ''))
        self.protocol_spinner = Spinner(
            text=saved_config.get('protocol', 'http'),
            values=['http', 'https'],
            size_hint=(1, 0.5)
        )
        self.ip_input = TextInput(hint_text='Enter server IP', multiline=False, text=saved_config.get('ip', '127.0.0.1'))
        self.port_input = TextInput(hint_text='Enter port', multiline=False, text=saved_config.get('port', '8080'))
        submit_button = Button(text='Connect', size_hint=(1, 0.5), on_press=lambda x: on_connect(self))
        layout.add_widget(self.key_input)
        layout.add_widget(self.name_input)
        layout.add_widget(Label(text='Protocol:'))
        layout.add_widget(self.protocol_spinner)
        layout.add_widget(self.ip_input)
        layout.add_widget(self.port_input)
        layout.add_widget(submit_button)
        self.add_widget(layout)

class VideoImage(Image):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.texture:
            tex_width, tex_height = self.texture.size
            widget_width, widget_height = self.size
            scale_x = tex_width / widget_width
            scale_y = tex_height / widget_height
            frame_x = (touch.x - self.x) * scale_x
            frame_y = (self.height - (touch.y - self.y)) * scale_y
            with boundary_lock:
                if len(boundary_line) < 2:
                    boundary_line.append((frame_x, frame_y))
                    if len(boundary_line) == 1:
                        self.bind(on_touch_move=self.track_mouse)
            return True
        return super().on_touch_down(touch)

    def track_mouse(self, instance, touch):
        if self.collide_point(*touch.pos):
            tex_width, tex_height = self.texture.size
            widget_width, widget_height = self.size
            scale_x = tex_width / widget_width
            scale_y = tex_height / widget_height
            frame_x = (touch.x - self.x) * scale_x
            frame_y = (self.height - (touch.y - self.y)) * scale_y
            global mouse_pos
            mouse_pos = (frame_x, frame_y)

    def on_touch_up(self, touch):
        with boundary_lock:
            if len(boundary_line) == 2:
                self.unbind(on_touch_move=self.track_mouse)
        return super().on_touch_up(touch)

def get_available_cameras(max_test=5):
    available = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(str(i))
            cap.release()
    return available if available else ["No camera available"]

class PeopleCounterApp(App):
    people_count = NumericProperty(0)
    connection_status = StringProperty("Disconnected")
    direction_left_to_right = True

    def build(self):
        global config
        layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        
        self.image = VideoImage(size_hint=(1, 0.65))
        layout.add_widget(self.image)
        
        self.count_label = Label(text="People Count: 0", size_hint=(1, 0.1))
        self.bind(people_count=lambda instance, value: setattr(self.count_label, 'text', f"People Count: {value}"))
        layout.add_widget(self.count_label)
        
        direction_layout = BoxLayout(size_hint=(1, 0.1))
        self.direction_label = Label(text="Entry direction: Left to Right")
        self.direction_checkbox = CheckBox(active=True)
        self.direction_checkbox.bind(active=self.on_checkbox_active)
        direction_layout.add_widget(self.direction_label)
        direction_layout.add_widget(self.direction_checkbox)
        layout.add_widget(direction_layout)
        
        status_layout = BoxLayout(size_hint=(1, 0.05))
        self.status_icon = Label(text="ERROR", color=(1, 0, 0, 1), font_size=24)
        self.status_label = Label(text="Status: Disconnected")
        self.bind(connection_status=lambda instance, value: self.update_status(value))
        status_layout.add_widget(self.status_icon)
        status_layout.add_widget(self.status_label)
        layout.add_widget(status_layout)
        
        camera_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        camera_options = get_available_cameras()
        self.camera_spinner = Spinner(
            text=camera_options[0] if camera_options else "No camera available",
            values=camera_options,
            size_hint=(0.5, 1)
        )
        self.camera_spinner.bind(text=self.on_camera_select)
        self.connect_button = Button(text="Connect to Server")
        self.connect_button.bind(on_press=self.open_login_popup)
        clear_button = Button(text="Clear Boundary")
        clear_button.bind(on_press=self.on_clear_boundary)
        camera_layout.add_widget(self.camera_spinner)
        camera_layout.add_widget(self.connect_button)
        camera_layout.add_widget(clear_button)
        layout.add_widget(camera_layout)
        
        Clock.schedule_interval(self.update_texture, 1 / 30.0)
        
        if camera_options:
            self.start_video_thread()
        
        return layout

    def update_status(self, value):
        if "Connected" in value:
            self.status_icon.text = "OK"
            self.status_icon.color = (0, 1, 0, 1)
        else:
            self.status_icon.text = "ERROR"
            self.status_icon.color = (1, 0, 0, 1)
        self.status_label.text = f"Status: {value}"

    def open_login_popup(self, instance):
        self.login_popup = LoginPopup(on_connect=self.on_connect, saved_config=config)
        self.login_popup.open()

    def on_connect(self, popup):
        global config
        config['key'] = popup.key_input.text
        config['name'] = popup.name_input.text
        config['ip'] = popup.ip_input.text
        config['port'] = popup.port_input.text
        config['protocol'] = popup.protocol_spinner.text
    
        try:
            with open('login.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
        server_url = f"{config['protocol']}://{config['ip']}:{config['port']}"
        self.connector = ServerConnector(server_url, config['key'], config['name'])
        self.connector.app = self
    
        if self.connector.connect():
            self.connection_status = f"Connected (Latency: {self.connector.latency:.2f} ms)"
        else:
            self.connection_status = "Connection Failed"
        popup.dismiss()

    def on_camera_select(self, spinner, text):
        if text != "No camera available":
            global stop_thread
            stop_thread = True
            time.sleep(0.5)
            stop_thread = False
            self.start_video_thread()

    def start_video_thread(self):
        video_source = int(self.camera_spinner.text) if self.camera_spinner.text.isdigit() else 0
        video_thread = threading.Thread(target=process_video, args=(video_source, self))
        video_thread.start()

    def on_checkbox_active(self, checkbox, value):
        self.direction_left_to_right = value
        if value:
            self.direction_label.text = "Entry direction: Left to Right"
        else:
            self.direction_label.text = "Entry direction: Right to Left"

    def on_clear_boundary(self, instance):
        global clear_boundary_flag
        clear_boundary_flag = True

    def on_stop(self):
        global stop_thread
        stop_thread = True

    def update_texture(self, dt):
        with frame_lock:
            if current_frame is not None:
                texture = Texture.create(size=(current_frame.shape[1], current_frame.shape[0]), colorfmt='bgr')
                texture.blit_buffer(current_frame.tobytes(), colorfmt='bgr', bufferfmt='ubyte')
                self.image.texture = texture

def process_video(source, app):
    global current_frame, stop_thread, boundary_line, mouse_pos, clear_boundary_flag, crossed_ids, prev_sides
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    if not cap.isOpened():
        Clock.schedule_once(lambda dt: app.show_error_popup(f"Unable to open camera {source}"))
        return
    while cap.isOpened() and not stop_thread:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        if results and results[0].boxes:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id
            classes = results[0].boxes.cls.cpu().numpy()
            if track_ids is not None:
                track_ids = track_ids.cpu().numpy().astype(int)
                for i, box in enumerate(boxes):
                    if classes[i] == 0:
                        x1, y1, x2, y2 = map(int, box[:4])
                        track_id = track_ids[i]
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                        cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                        with boundary_lock:
                            if len(boundary_line) == 2:
                                A, B = boundary_line
                                AB = (B[0] - A[0], B[1] - A[1])
                                P = (cx, cy)
                                AP = (P[0] - A[0], P[1] - A[1])
                                cross = AB[0] * AP[1] - AB[1] * AP[0]
                                side = 1 if cross > 0 else -1 if cross < 0 else 0
                                if track_id in prev_sides:
                                    prev_side = prev_sides[track_id]
                                    if prev_side != 0 and side != 0 and prev_side != side:
                                        direction = "left_to_right" if prev_side == -1 and side == 1 else "right_to_left"
                                        if app.direction_left_to_right:
                                            if direction == "left_to_right":
                                                Clock.schedule_once(lambda dt: setattr(app, 'people_count', app.people_count + 1))
                                            else:
                                                Clock.schedule_once(lambda dt: setattr(app, 'people_count', max(0, app.people_count - 1)))
                                        else:
                                            if direction == "right_to_left":
                                                Clock.schedule_once(lambda dt: setattr(app, 'people_count', app.people_count + 1))
                                            else:
                                                Clock.schedule_once(lambda dt: setattr(app, 'people_count', max(0, app.people_count - 1)))
                                prev_sides[track_id] = side

        if clear_boundary_flag:
            with boundary_lock:
                boundary_line.clear()
                mouse_pos = None
            crossed_ids.clear()
            prev_sides.clear()
            Clock.schedule_once(lambda dt: setattr(app, 'people_count', 0))
            clear_boundary_flag = False

        with boundary_lock:
            if len(boundary_line) == 1 and mouse_pos is not None:
                cv2.line(frame, (int(boundary_line[0][0]), int(boundary_line[0][1])), 
                         (int(mouse_pos[0]), int(mouse_pos[1])), (0, 255, 0), 2)
            elif len(boundary_line) == 2:
                cv2.line(frame, (int(boundary_line[0][0]), int(boundary_line[0][1])), 
                         (int(boundary_line[1][0]), int(boundary_line[1][1])), (0, 0, 255), 2)

        frame = cv2.flip(frame, 0)
        with frame_lock:
            current_frame = frame.copy()
            
        if hasattr(app, 'connector') and app.connector.connected:
            if not app.connector.send_people_count(app.people_count, frame):
                app.connection_status = "Disconnected"

    cap.release()

if __name__ == "__main__":
    PeopleCounterApp().run()