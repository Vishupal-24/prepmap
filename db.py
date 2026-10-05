import os
import secrets
import sqlite3

DB_PATH = os.environ.get("PREPMAP_DB", os.path.join(os.path.dirname(__file__), "data", "prepmap.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    company TEXT NOT NULL,
    role TEXT,
    year INTEGER,
    outcome TEXT,              -- offer / rejected / no reply / unknown
    route TEXT,                -- campus / off-campus / referral / PPO / unknown
    source TEXT,               -- form / paste
    raw_text TEXT,
    name TEXT,                 -- only kept if consent_contact = 1
    contact TEXT,              -- only kept if consent_contact = 1
    proof_url TEXT,
    consent_summary INTEGER DEFAULT 0,
    consent_contact INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    delete_token TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,        -- round / topic / resource / mistake / advice / timeline
    value TEXT NOT NULL,
    quote TEXT,
    position INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS facts_story ON facts(story_id);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    company TEXT,              -- optional: which company or program it is about
    text TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    by_line TEXT,              -- optional, e.g. "4th year, got the offer"
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        # older databases were made before the route column existed
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(stories)")}
        if "route" not in cols:
            conn.execute("ALTER TABLE stories ADD COLUMN route TEXT")


def save_story(story, facts):
    """story: dict of story columns, facts: list of (kind, value, quote)."""
    # no consent, no identity
    if not story.get("consent_contact"):
        story["name"] = None
        story["contact"] = None
    story["delete_token"] = secrets.token_urlsafe(8)
    cols = ["company", "role", "year", "outcome", "route", "source", "raw_text", "name", "contact",
            "proof_url", "consent_summary", "consent_contact", "approved", "delete_token"]
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO stories ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [story.get(c) for c in cols],
        )
        sid = cur.lastrowid
        conn.executemany(
            "INSERT INTO facts (story_id, kind, value, quote, position) VALUES (?,?,?,?,?)",
            [(sid, k, v, q, i) for i, (k, v, q) in enumerate(facts)],
        )
    return sid, story["delete_token"]


def delete_story(token):
    with connect() as conn:
        return conn.execute("DELETE FROM stories WHERE delete_token = ?", (token,)).rowcount


def stories(company=None, approved_only=True):
    sql = "SELECT * FROM stories WHERE 1=1"
    args = []
    if approved_only:
        sql += " AND approved = 1"
    if company:
        sql += " AND lower(company) = lower(?)"
        args.append(company)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY year DESC, id DESC", args)]


def facts_for(story_ids):
    if not story_ids:
        return []
    marks = ",".join("?" * len(story_ids))
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM facts WHERE story_id IN ({marks}) ORDER BY story_id, position", story_ids)
        return [dict(r) for r in rows]


def companies():
    with connect() as conn:
        rows = conn.execute(
            "SELECT company, COUNT(*) n FROM stories WHERE approved = 1 GROUP BY lower(company) ORDER BY n DESC")
        return [dict(r) for r in rows]


def story(story_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM stories WHERE id = ? AND approved = 1", (story_id,)).fetchone()
        return dict(row) if row else None


# --- anonymous questions board ----------------------------------------------

def add_question(text, company=None):
    with connect() as conn:
        return conn.execute("INSERT INTO questions (text, company) VALUES (?, ?)", (text, company)).lastrowid


def add_answer(question_id, text, by_line=None):
    with connect() as conn:
        conn.execute("INSERT INTO answers (question_id, text, by_line) VALUES (?, ?, ?)",
                     (question_id, text, by_line))


def questions(company=None):
    sql = """SELECT q.*, COUNT(a.id) AS answers FROM questions q
             LEFT JOIN answers a ON a.question_id = q.id"""
    args = []
    if company:
        sql += " WHERE lower(q.company) = lower(?)"
        args.append(company)
    sql += " GROUP BY q.id ORDER BY answers = 0 DESC, q.id DESC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args)]


def question(question_id):
    with connect() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not q:
            return None
        q = dict(q)
        q["answers"] = [dict(r) for r in conn.execute(
            "SELECT * FROM answers WHERE question_id = ? ORDER BY id", (question_id,))]
        return q
