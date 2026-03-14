import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.thoth/thoth.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init(conn)
    return conn

def _init(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT UNIQUE NOT NULL,
        target    TEXT,
        platform  TEXT,
        category  TEXT,
        writeup   TEXT,
        stage     TEXT DEFAULT 'recon',
        status    TEXT DEFAULT 'active',
        hints     INTEGER DEFAULT 0,
        elapsed   INTEGER DEFAULT 0,
        scan_data TEXT,
        tried     TEXT DEFAULT '[]',
        created   TEXT,
        updated   TEXT
    );
    CREATE TABLE IF NOT EXISTS notes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session    TEXT NOT NULL,
        stage      TEXT,
        content    TEXT,
        timestamp  TEXT
    );
    CREATE TABLE IF NOT EXISTS activity (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session    TEXT NOT NULL,
        action     TEXT,
        detail     TEXT,
        timestamp  TEXT
    );
    CREATE TABLE IF NOT EXISTS profile (
        key   TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    conn.commit()

# ── Sessions ──
def session_create(name, target, platform, category, writeup=""):
    conn = get_conn()
    now  = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO sessions (name,target,platform,category,writeup,created,updated) VALUES (?,?,?,?,?,?,?)",
        (name, target, platform, category, writeup, now, now)
    )
    conn.commit(); conn.close()

def session_get(name):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM sessions WHERE name=?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def session_all():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sessions ORDER BY updated DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def session_update(name, **kwargs):
    conn  = get_conn()
    kwargs["updated"] = datetime.now().isoformat()
    sets  = ", ".join(f"{k}=?" for k in kwargs)
    vals  = list(kwargs.values()) + [name]
    conn.execute(f"UPDATE sessions SET {sets} WHERE name=?", vals)
    conn.commit(); conn.close()

def session_delete(name):
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE name=?", (name,))
    conn.execute("DELETE FROM notes    WHERE session=?", (name,))
    conn.execute("DELETE FROM activity WHERE session=?", (name,))
    conn.commit(); conn.close()

def session_exists(name):
    return session_get(name) is not None

# ── Notes ──
def note_add(session, stage, content):
    conn = get_conn()
    now  = datetime.now().strftime("%H:%M")
    conn.execute(
        "INSERT INTO notes (session,stage,content,timestamp) VALUES (?,?,?,?)",
        (session, stage, content, now)
    )
    conn.commit(); conn.close()

def notes_get(session):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notes WHERE session=? ORDER BY id", (session,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Activity log ──
def log_add(session, action, detail=""):
    conn = get_conn()
    now  = datetime.now().strftime("%H:%M:%S")
    conn.execute(
        "INSERT INTO activity (session,action,detail,timestamp) VALUES (?,?,?,?)",
        (session, action, detail, now)
    )
    conn.commit(); conn.close()

def log_get(session):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM activity WHERE session=? ORDER BY id", (session,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Profile ──
def profile_get(key, default=None):
    conn = get_conn()
    row  = conn.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
    conn.close()
    if row:
        try: return json.loads(row["value"])
        except: return row["value"]
    return default

def profile_set(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO profile (key,value) VALUES (?,?)",
        (key, json.dumps(value))
    )
    conn.commit(); conn.close()

def profile_all():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM profile").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

# ── Active session helper ──
def get_active():
    name = profile_get("active_session")
    if not name: return None
    return session_get(name)

def set_active(name):
    profile_set("active_session", name)
