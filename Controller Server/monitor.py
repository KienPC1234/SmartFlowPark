import sqlite3
import os

class MonitorManager:
    def __init__(self, db_name="app_database.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                key TEXT NOT NULL,  
                url TEXT DEFAULT '',
                status TEXT DEFAULT 'ERROR',
                zone_id INTEGER,
                people_count INTEGER DEFAULT 0,
                image TEXT DEFAULT '',
                delay REAL DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def add_monitor(self, monitor):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO monitors (name, key, url, status, zone_id, people_count, image, delay) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (monitor.get('name', ''), 
              monitor.get('key', ''), 
              monitor.get('url', ''), 
              monitor.get('status', 'active'),
              monitor.get('zone_id', None),
              monitor.get('people_count', 0),
              monitor.get('image', ''),
              monitor.get('delay', 0)))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def update_monitor(self, monitor_id, monitor):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE monitors 
            SET name = ?, key = ?, url = ?, status = ?, zone_id = ?, people_count = ?, image = ?, delay = ?
            WHERE id = ?
        ''', (monitor.get('name', ''),
              monitor.get('key', ''),  
              monitor.get('url', ''),
              monitor.get('status', 'active'),
              monitor.get('zone_id', None),
              monitor.get('people_count', 0),
              monitor.get('image', ''),
              monitor.get('delay', 0),
              monitor_id))
        conn.commit()
        conn.close()

    def get_all_monitors(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM monitors')
        monitors = [{'id': row[0], 'name': row[1], 'key': row[2], 'url': row[3], 
                    'status': row[4], 'zone_id': row[5], 'people_count': row[6], 
                    'image': row[7], 'delay': row[8]} 
                   for row in cursor.fetchall()]
        conn.close()
        return monitors

    def get_monitor_by_id(self, monitor_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM monitors WHERE id = ?', (monitor_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'name': row[1], 'key': row[2], 'url': row[3], 
                   'status': row[4], 'zone_id': row[5], 'people_count': row[6], 
                   'image': row[7], 'delay': row[8]}
        return None