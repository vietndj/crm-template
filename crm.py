import http.server
import socketserver
import sqlite3
import json
import urllib.parse
import webbrowser
import threading
import os
import sys
import uuid
import time
from datetime import datetime

PORT = 8899
DB_FILE = 'crm.db'
MASTER_PASSWORD = '1234'
DIST_DIR = 'dist'

SCHEMA = """
-- Bảng leads chính
CREATE TABLE IF NOT EXISTS leads (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name        TEXT NOT NULL,
    phone       TEXT,
    email       TEXT,
    facebook_url TEXT,
    zalo_phone  TEXT,
    avatar_url  TEXT,
    industry    TEXT,
    industry_slug TEXT,
    source      TEXT DEFAULT 'manual',
    class       TEXT,
    status      TEXT DEFAULT 'new' CHECK(status IN ('new','contacted','qualified','negotiating','converted','lost')),
    health      TEXT DEFAULT 'green' CHECK(health IN ('green','yellow','red')),
    score       INTEGER DEFAULT 0,
    notes       TEXT DEFAULT '[]',
    tags        TEXT DEFAULT '[]',
    assigned_to TEXT,
    company     TEXT,
    address     TEXT,
    custom_fields TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    synced_at   TEXT,
    deleted_at  TEXT
);

-- Index cho tìm kiếm nhanh
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry_slug);

-- Bảng lịch sử tương tác
CREATE TABLE IF NOT EXISTS interactions (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    lead_id     TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('call','sms','zalo','facebook_dm','email','note','meeting','purchase')),
    direction   TEXT CHECK(direction IN ('inbound','outbound')),
    content     TEXT,
    duration    INTEGER,
    metadata    TEXT DEFAULT '{}',
    created_by  TEXT DEFAULT 'system',
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interactions_lead ON interactions(lead_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(type);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);

-- Bảng pipeline stages (customizable)
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    color       TEXT DEFAULT '#6B7280',
    sort_order  INTEGER DEFAULT 0,
    is_default  INTEGER DEFAULT 0
);

-- Bảng products/services
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name        TEXT NOT NULL,
    price       REAL,
    description TEXT,
    active      INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng cấu hình
CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng import logs
CREATE TABLE IF NOT EXISTS import_logs (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    source      TEXT,
    filename    TEXT,
    total_rows  INTEGER,
    imported    INTEGER,
    skipped     INTEGER,
    errors      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng sessions (for auth)
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    created_at  TEXT DEFAULT (datetime('now')),
    expires_at  TEXT
);

-- Seed pipeline stages
INSERT OR IGNORE INTO pipeline_stages (id, name, color, sort_order, is_default) VALUES
    ('new', 'Mới', '#3B82F6', 0, 1),
    ('contacted', 'Đã liên hệ', '#F59E0B', 1, 0),
    ('qualified', 'Tiềm năng', '#8B5CF6', 2, 0),
    ('negotiating', 'Đang thương lượng', '#EC4899', 3, 0),
    ('converted', 'Đã chuyển đổi', '#10B981', 4, 0),
    ('lost', 'Đã mất', '#6B7280', 5, 0);

-- Seed default config
INSERT OR IGNORE INTO config (key, value) VALUES
    ('business_name', 'My Business'),
    ('currency', 'VND'),
    ('timezone', 'Asia/Ho_Chi_Minh'),
    ('sync_platform', 'auto'),
    ('telegram_bot_token', ''),
    ('telegram_chat_id', '');
"""

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class CRMRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        if os.path.exists(DIST_DIR):
            super().__init__(*args, directory=DIST_DIR, **kwargs)
        else:
            super().__init__(*args, directory='.', **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if 200 <= status < 300:
            out = {"success": True, "data": data}
        else:
            err = data.get("error", "Error") if isinstance(data, dict) else str(data)
            out = {"success": False, "error": err}
            
        self.wfile.write(json.dumps(out).encode('utf-8'))

    def read_json(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        token = auth_header.split(' ')[1]
        conn = get_db()
        sess = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        conn.close()
        return sess is not None
        
    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if not path.startswith('/api/'):
                if not os.path.exists(os.path.join(self.directory, path.lstrip('/'))) and not path.endswith('.js') and not path.endswith('.css'):
                    self.path = '/index.html'
                return super().do_GET()

            if not self.check_auth() and path != '/api/auth':
                return self.send_json(401, {"error": "Unauthorized"})

            query = urllib.parse.parse_qs(parsed_path.query)
            conn = get_db()
            try:
                if path == '/api/leads':
                    if 'id' in query:
                        lead = conn.execute("SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL", (query['id'][0],)).fetchone()
                        if lead:
                            return self.send_json(200, dict(lead))
                        return self.send_json(404, {"error": "Not found"})
                    else:
                        q = query.get('q', [''])[0]
                        status = query.get('status', [''])[0]
                        sql = "SELECT * FROM leads WHERE deleted_at IS NULL"
                        params = []
                        if q:
                            sql += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
                            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
                        if status:
                            sql += " AND status = ?"
                            params.append(status)
                        sql += " ORDER BY updated_at DESC"
                        leads = [dict(r) for r in conn.execute(sql, params).fetchall()]
                        return self.send_json(200, leads)
                
                elif path.startswith('/api/leads/'):
                    lead_id = path.split('/')[-1]
                    lead = conn.execute("SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL", (lead_id,)).fetchone()
                    if lead:
                        return self.send_json(200, dict(lead))
                    return self.send_json(404, {"error": "Not found"})

                elif path == '/api/interactions':
                    lead_id = query.get('lead_id', [''])[0]
                    if lead_id:
                        interactions = [dict(r) for r in conn.execute("SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,)).fetchall()]
                        return self.send_json(200, interactions)
                    return self.send_json(400, {"error": "Missing lead_id"})

                elif path == '/api/stats':
                    total = conn.execute("SELECT COUNT(*) as c FROM leads WHERE deleted_at IS NULL").fetchone()['c']
                    return self.send_json(200, {"total_leads": total})

                elif path == '/api/config':
                    config = {r['key']: r['value'] for r in conn.execute("SELECT * FROM config").fetchall()}
                    return self.send_json(200, config)

                else:
                    return self.send_json(404, {"error": "Endpoint not found"})
            finally:
                conn.close()
        except Exception as e:
            print(f"Error GET: {e}")
            self.send_json(500, {"error": str(e)})

    def do_POST(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if not path.startswith('/api/'):
                return self.send_json(404, {"error": "Not found"})

            try:
                data = self.read_json()
            except:
                return self.send_json(400, {"error": "Invalid JSON"})

            if path == '/api/auth':
                if data.get('password') == MASTER_PASSWORD:
                    token = str(uuid.uuid4())
                    conn = get_db()
                    conn.execute("INSERT INTO sessions (token) VALUES (?)", (token,))
                    conn.commit()
                    conn.close()
                    return self.send_json(200, {"token": token})
                return self.send_json(401, {"error": "Invalid password"})

            if not self.check_auth():
                return self.send_json(401, {"error": "Unauthorized"})

            conn = get_db()
            try:
                if path == '/api/leads':
                    uid = str(uuid.uuid4())[:16]
                    fields = ['name', 'phone', 'email', 'company', 'source', 'status']
                    vals = [data.get(f, '') for f in fields]
                    if not vals[0]: vals[0] = 'No Name'
                    
                    conn.execute(f"INSERT INTO leads (id, {','.join(fields)}) VALUES (?, ?, ?, ?, ?, ?, ?)", [uid] + vals)
                    conn.commit()
                    return self.send_json(200, {"id": uid, "status": "created"})

                elif path == '/api/interactions':
                    uid = str(uuid.uuid4())[:16]
                    fields = ['lead_id', 'type', 'content', 'direction']
                    vals = [data.get(f, '') for f in fields]
                    conn.execute(f"INSERT INTO interactions (id, {','.join(fields)}) VALUES (?, ?, ?, ?, ?)", [uid] + vals)
                    conn.commit()
                    return self.send_json(200, {"id": uid, "status": "created"})

                elif path == '/api/import':
                    rows = data.get('data', [])
                    mapping = data.get('mapping', {})
                    imported = 0
                    
                    def get_val(row, map_val):
                        if not map_val and map_val != 0: return ''
                        if isinstance(map_val, int) or (isinstance(map_val, str) and map_val.isdigit()):
                            try:
                                return list(row.values())[int(map_val)]
                            except:
                                return ''
                        return row.get(map_val, '')
                        
                    for row in rows:
                        uid = str(uuid.uuid4())[:16]
                        name = get_val(row, mapping.get('name'))
                        if not name: name = 'Unknown'
                        phone = get_val(row, mapping.get('phone'))
                        email = get_val(row, mapping.get('email'))
                        source = get_val(row, mapping.get('source'))
                        status = get_val(row, mapping.get('status'))
                        if not status: status = 'new'
                        if not source: source = 'import'
                        
                        conn.execute("INSERT INTO leads (id, name, phone, email, source, status) VALUES (?, ?, ?, ?, ?, ?)", (uid, name, phone, email, source, status))
                        imported += 1
                    conn.commit()
                    return self.send_json(200, {"imported": imported})

                else:
                    return self.send_json(404, {"error": "Endpoint not found"})
            finally:
                conn.close()
        except Exception as e:
            print(f"Error POST: {e}")
            self.send_json(500, {"error": str(e)})

    def do_PUT(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if not self.check_auth():
                return self.send_json(401, {"error": "Unauthorized"})

            try:
                data = self.read_json()
            except:
                return self.send_json(400, {"error": "Invalid JSON"})

            conn = get_db()
            try:
                if path.startswith('/api/leads/'):
                    lead_id = path.split('/')[-1]
                    updates = []
                    params = []
                    for k, v in data.items():
                        if k in ['name', 'phone', 'email', 'company', 'source', 'status']:
                            updates.append(f"{k} = ?")
                            params.append(v)
                    if updates:
                        updates.append("updated_at = datetime('now')")
                        params.append(lead_id)
                        conn.execute(f"UPDATE leads SET {', '.join(updates)} WHERE id = ?", params)
                        conn.commit()
                        return self.send_json(200, {"status": "updated"})
                    return self.send_json(400, {"error": "No valid fields to update"})

                elif path == '/api/config':
                    for k, v in data.items():
                        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, str(v)))
                    conn.commit()
                    return self.send_json(200, {"status": "updated"})

                else:
                    return self.send_json(404, {"error": "Endpoint not found"})
            finally:
                conn.close()
        except Exception as e:
            print(f"Error PUT: {e}")
            self.send_json(500, {"error": str(e)})

    def do_DELETE(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if not self.check_auth():
                return self.send_json(401, {"error": "Unauthorized"})

            conn = get_db()
            try:
                if path.startswith('/api/leads/'):
                    lead_id = path.split('/')[-1]
                    conn.execute("UPDATE leads SET deleted_at = datetime('now') WHERE id = ?", (lead_id,))
                    conn.commit()
                    return self.send_json(200, {"status": "deleted"})
                else:
                    return self.send_json(404, {"error": "Endpoint not found"})
            finally:
                conn.close()
        except Exception as e:
            print(f"Error DELETE: {e}")
            self.send_json(500, {"error": str(e)})

class ThreadedHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def run_server():
    init_db()
    handler = CRMRequestHandler
    with ThreadedHTTPServer(("", PORT), handler) as httpd:
        print(f"🟢 CRM đang chạy tại http://localhost:{PORT} (Ctrl+C để tắt)")
        httpd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐã tắt CRM.")
        sys.exit(0)
