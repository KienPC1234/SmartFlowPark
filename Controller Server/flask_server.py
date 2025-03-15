from flask import Flask, request, jsonify
import time
import secrets
from settings import RandomGenerator
import sqlite3

connected_clients = {}
default_key = RandomGenerator.generate_key(16)
default_name = RandomGenerator.generate_name(8)
client_id = f"{default_key}_{default_name}"
connected_clients[client_id] = {
    'key': default_key,
    'name': default_name,
    'people_count': 0,
    'image': None,
    "last_request": None,
    "delay": 0
}

class FlaskServer:
    def __init__(self, settings_manager, monitor_manager):
        self.settings_manager = settings_manager
        self.monitor_manager = monitor_manager
        self.app = Flask(__name__)
        self.tokens = {}  # {token: {"username": "...", "permissions": [...], "expiry": timestamp}}
        self.register_routes()

    def _is_valid_client(self, key, name):
        for monitor in self.monitor_manager.get_all_monitors():
            if monitor.get("key") == key and monitor.get("name") == name:
                return True
        return False

    def _check_auth(self, token, required_permission=None):
        if token not in self.tokens:
            return False, "Invalid or expired token"
        user_info = self.tokens[token]
        if time.time() > user_info["expiry"]:
            del self.tokens[token]
            return False, "Token has expired"
        if required_permission and required_permission not in user_info["permissions"]:
            return False, f"Permission '{required_permission}' required"
        return True, user_info["username"]

    def register_routes(self):
        @self.app.route('/login', methods=['POST'])
        def login():
            data = request.get_json(silent=True)
            if not data or "username" not in data or "password" not in data:
                return jsonify({"status": "ERROR", "message": "Username and password required"}), 400
            username = data["username"]
            password = data["password"]
            for account in self.settings_manager.get_all_accounts():
                if account["username"] == username and account["password"] == password:
                    token = secrets.token_hex(16)
                    permissions = account.get("permissions", [])
                    self.tokens[token] = {
                        "username": username,
                        "permissions": permissions,
                        "expiry": time.time() + 28800 
                    }
                    # Trả về token và permissions
                    return jsonify({"status": "OK", "token": token, "permissions": permissions}), 200
            return jsonify({"status": "ERROR", "message": "Invalid credentials"}), 401

        @self.app.route('/app', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def manage_app():
            try:
                token = request.headers.get('Authorization')
                if not token:
                    return jsonify({"status": "ERROR", "message": "Authorization token required"}), 401
        
                is_valid, message = self._check_auth(token)
                if not is_valid:
                    return jsonify({"status": "ERROR", "message": message}), 403
        
                data_type = request.args.get('type')
                if not data_type or data_type not in ['monitors', 'zones', 'accounts']:
                    return jsonify({"status": "ERROR", "message": "Invalid type parameter"}), 400
        
                required_permission = 'monitor' if data_type == 'monitors' else 'zone' if data_type == 'zones' else 'home'
                is_valid, message = self._check_auth(token, required_permission)
                if not is_valid:
                    return jsonify({"status": "ERROR", "message": message}), 403
        
                now = time.time()
                THRESHOLD = 15.0
        
                if request.method == 'GET':
                    if data_type == 'monitors':
                        real_time_monitors = []
                        for monitor in self.monitor_manager.get_all_monitors():
                            client_id = f"{monitor.get('key', '')}_{monitor.get('name', '')}"
                            client = connected_clients.get(client_id, {})
                            status = "OK" if client and (now - client.get("last_request", 0)) <= THRESHOLD else "ERROR"
                            real_time_monitor = {
                                "id": monitor.get("id"),
                                "name": monitor.get("name", ""),
                                "key": monitor.get("key", ""),  
                                "people_count": client.get("people_count", 0) if status == "OK" else 0,
                                "image": client.get("image", None) if status == "OK" else "",
                                "status": status,
                                "delay": client.get("delay", 0) if status == "OK" else 0
                            }
                            real_time_monitors.append(real_time_monitor)
                        return jsonify({"status": "OK", "data": real_time_monitors}), 200
        
                    elif data_type == 'zones':
                        real_time_zones = []
                        for zone in self.settings_manager.get_all_zones():
                            counts = []
                            for mname in zone.get("monitors", []):
                                for monitor in self.monitor_manager.get_all_monitors():
                                    if monitor["name"] == mname:
                                        client_id = f"{monitor['key']}_{monitor['name']}"
                                        client = connected_clients.get(client_id)
                                        if client and (now - client.get("last_request", 0)) <= THRESHOLD:
                                            counts.append(client.get("people_count", 0))
                                        break
                            people_count = 0
                            if counts:
                                mode = zone.get("mode", "max")
                                if mode == "max":
                                    people_count = max(counts)
                                elif mode == "min":
                                    people_count = min(counts)
                                elif mode == "avg":
                                    people_count = int(round(sum(counts) / len(counts)))
                                elif mode == "sum":
                                    people_count = sum(counts)
                            real_time_zone = {
                                "id": zone.get("id"),
                                "name": zone.get("name", ""),
                                "mode": zone.get("mode", "max"),
                                "monitors": zone.get("monitors", []),
                                "people_count": people_count
                            }
                            real_time_zones.append(real_time_zone)
                        return jsonify({"status": "OK", "data": real_time_zones}), 200
        
                    elif data_type == 'accounts':
                        return jsonify({"status": "OK", "data": self.settings_manager.get_all_accounts()}), 200
        
                elif request.method == 'POST':
                    data = request.get_json(silent=True)
                    if not data:
                        return jsonify({"status": "ERROR", "message": "Invalid data"}), 400
        
                    if data_type == 'monitors':
                        if data.get("action") == "reset":
                            key = data.get("key")
                            name = data.get("name")
                            if not key or not name:
                                return jsonify({"status": "ERROR", "message": "Missing key or name"}), 400
                            client_id = f"{key}_{name}"
                            if client_id in connected_clients:
                                connected_clients[client_id]["people_count"] = 0 
                                connected_clients[client_id]["reset_counter"] = True
                                return jsonify({"status": "OK", "message": "People counter reset"}), 200
                            else:
                                return jsonify({"status": "ERROR", "message": "Monitor not connected"}), 404
        
                        self.monitor_manager.add_monitor(data)
                        return jsonify({"status": "OK", "message": "Monitor added"}), 201
        
                    elif data_type == 'zones':
                        self.settings_manager.add_zone(data)
                        return jsonify({"status": "OK", "message": "Zone added"}), 201
        
                    elif data_type == 'accounts':
                        self.settings_manager.add_account(data)
                        return jsonify({"status": "OK", "message": "Account added"}), 201
        
                elif request.method == 'PUT':
                    data = request.get_json(silent=True)
                    if not data or 'id' not in data:
                        return jsonify({"status": "ERROR", "message": "Invalid data or missing id"}), 400
        
                    id = data.pop('id')
                    if data_type == 'monitors':
                        self.monitor_manager.update_monitor(id, data)  
                        return jsonify({"status": "OK", "message": "Monitor updated"}), 200
                    elif data_type == 'zones':
                        self.settings_manager.update_zone(id, data)
                        return jsonify({"status": "OK", "message": "Zone updated"}), 200
                    elif data_type == 'accounts':
                        if 'ip' in data or 'port' in data:
                            return jsonify({"status": "ERROR", "message": "Cannot modify server IP or port"}), 403
                        self.settings_manager.update_account(id, data)
                        return jsonify({"status": "OK", "message": "Account updated"}), 200
        
                elif request.method == 'DELETE':
                    id_param = request.args.get('id')
                    if not id_param:
                        return jsonify({"status": "ERROR", "message": "Missing id"}), 400
                    try:
                        id = int(id_param)
                    except ValueError:
                        return jsonify({"status": "ERROR", "message": "Invalid id format"}), 400
        
                    if data_type == 'monitors':
                        try:
                            with sqlite3.connect(self.monitor_manager.db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('DELETE FROM monitors WHERE id = ?', (id,))
                                if cursor.rowcount == 0:
                                    return jsonify({"status": "ERROR", "message": "Monitor not found"}), 404
                                conn.commit()
                        except Exception as e:
                            return jsonify({"status": "ERROR", "message": "Database error", "error": str(e)}), 500
                        return jsonify({"status": "OK", "message": "Monitor deleted"}), 200
        
                    elif data_type == 'zones':
                        try:
                            with sqlite3.connect(self.settings_manager.db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('DELETE FROM zones WHERE id = ?', (id,))
                                if cursor.rowcount == 0:
                                    return jsonify({"status": "ERROR", "message": "Zone not found"}), 404
                                conn.commit()
                        except Exception as e:
                            return jsonify({"status": "ERROR", "message": "Database error", "error": str(e)}), 500
                        return jsonify({"status": "OK", "message": "Zone deleted"}), 200
        
                    elif data_type == 'accounts':
                        try:
                            with sqlite3.connect(self.settings_manager.db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('DELETE FROM accounts WHERE id = ?', (id,))
                                if cursor.rowcount == 0:
                                    return jsonify({"status": "ERROR", "message": "Account not found"}), 404
                                conn.commit()
                        except Exception as e:
                            return jsonify({"status": "ERROR", "message": "Database error", "error": str(e)}), 500
                        return jsonify({"status": "OK", "message": "Account deleted"}), 200
        
                else:
                    return jsonify({"status": "ERROR", "message": "Method not allowed"}), 405
        
            except Exception as e:
                # Bắt các ngoại lệ không lường trước được và trả về lỗi chung
                return jsonify({"status": "ERROR", "message": "Internal server error", "error": str(e)}), 500

        @self.app.route('/connect', methods=['POST'])
        def connect():
            data = request.get_json(silent=True)
            if not data or 'key' not in data or 'name' not in data:
                return jsonify({"status": "ERROR", "message": "Key and name are required"}), 400
            key = data['key']
            name = data['name']
            if not self._is_valid_client(key, name):
                return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403
            client_id = f"{key}_{name}"
            connected_clients[client_id] = {
                'key': key,
                'name': name,
                'people_count': 0,
                'image': None,
                "last_request": time.time(),
                "delay": 0
            }
            return jsonify({"status": "OK", "key": key, "name": name}), 200

        @self.app.route('/update_count', methods=['POST'])
        def update_count():
            data = request.get_json(silent=True)
            if not data or 'key' not in data or 'name' not in data or 'people_count' not in data:
                return jsonify({"status": "ERROR", "message": "Missing required fields"}), 400
            key = data['key']
            name = data['name']
            people_count = data['people_count']
            image_base64 = data.get('image')
            if not self._is_valid_client(key, name):
                return jsonify({"status": "ERROR", "message": "Invalid key or name"}), 403
            client_id = f"{key}_{name}"
            now = time.time()
            if client_id in connected_clients:
                client = connected_clients[client_id]
                prev = client.get("last_request")
                client["delay"] = round((now - prev) * 1000, 2) if prev else 0
                client["last_request"] = now
                client["people_count"] = people_count
                if image_base64:
                    client["image"] = image_base64
                if client.get("reset_counter", False):
                    client["reset_counter"] = False  
                    return jsonify({"status": "OK", "action": "Reset Counter"}), 200
                return jsonify({"status": "OK"}), 200
            return jsonify({"status": "ERROR", "message": "Client not connected"}), 403

    def run(self):
        server_settings = self.settings_manager.get_server_settings()
        server_ip = server_settings["ip"]
        server_port = server_settings["port"]
        self.app.run(host=server_ip, port=server_port, threaded=True)