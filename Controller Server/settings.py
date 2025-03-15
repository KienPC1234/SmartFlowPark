import sqlite3
import json
import random
import string

class RandomGenerator:
    @staticmethod
    def generate_key(length=16):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    @staticmethod
    def generate_name(length=8):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

class SettingsManager:
    def __init__(self, db_name="app_database.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL DEFAULT '127.0.0.1',
                port INTEGER NOT NULL DEFAULT 8080
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                permissions TEXT DEFAULT '[]',  
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mode TEXT DEFAULT 'max',
                monitors TEXT DEFAULT '[]',  
                people_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM server_settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO server_settings (ip, port) VALUES (?, ?)', 
                         ('127.0.0.1', 8080))
        
        conn.commit()
        conn.close()

    def add_account(self, account):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        permissions = json.dumps(account.get('permissions', []))  
        cursor.execute('INSERT INTO accounts (username, password, permissions, status) VALUES (?, ?, ?, ?)',
                      (account.get('username', ''),
                       account.get('password', ''),
                       permissions,
                       account.get('status', 'active')))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_account(self, account_id, account):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        permissions = json.dumps(account.get('permissions', []))  
        cursor.execute('''
            UPDATE accounts 
            SET username = ?, password = ?, permissions = ?, status = ?
            WHERE id = ?
        ''', (account.get('username', ''),
              account.get('password', ''),
              permissions,
              account.get('status', 'active'),
              account_id))
        conn.commit()
        conn.close()

    def add_zone(self, zone):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        monitors = json.dumps(zone.get('monitors', []))  
        cursor.execute('INSERT INTO zones (name, mode, monitors, people_count, status) VALUES (?, ?, ?, ?, ?)',
                      (zone.get('name', ''),
                       zone.get('mode', 'max'),
                       monitors,
                       zone.get('people_count', 0),
                       zone.get('status', 'active')))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_zone(self, zone_id, zone):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        monitors = json.dumps(zone.get('monitors', []))  
        cursor.execute('''
            UPDATE zones 
            SET name = ?, mode = ?, monitors = ?, people_count = ?, status = ?
            WHERE id = ?
        ''', (zone.get('name', ''),
              zone.get('mode', 'max'),
              monitors,
              zone.get('people_count', 0),
              zone.get('status', 'active'),
              zone_id))
        conn.commit()
        conn.close()

    def get_server_settings(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT ip, port FROM server_settings LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        return {'ip': row[0], 'port': row[1]} if row else {'ip': '127.0.0.1', 'port': 8080}

    def update_server_settings(self, ip, port):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('UPDATE server_settings SET ip = ?, port = ? WHERE id = 1', 
                      (ip, port))
        conn.commit()
        conn.close()

    def get_all_accounts(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts')
        accounts = [{'id': row[0], 'username': row[1], 'password': row[2], 
                    'permissions': json.loads(row[3]), 'status': row[4]} 
                   for row in cursor.fetchall()]
        conn.close()
        return accounts

    def get_all_zones(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM zones')
        zones = [{'id': row[0], 'name': row[1], 'mode': row[2], 
                 'monitors': json.loads(row[3]), 'people_count': row[4], 'status': row[5]}  
                for row in cursor.fetchall()]
        conn.close()
        return zones