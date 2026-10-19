import os
import sqlite3
import secrets
from functools import wraps
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deploying")
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "zenfury.db"))

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_messages_pair ON messages(sender_id, receiver_id, id)")

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "login_required"}), 401
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapped

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

@app.route("/", methods=["GET"])
def index():
    if session.get("user_id"):
        return render_template("chat.html", username=session.get("username"))
    return render_template("index.html")

@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not (3 <= len(username) <= 24) or not username.replace("_", "").isalnum():
        flash("Username harus 3–24 karakter: huruf, angka, atau underscore.", "error")
        return redirect(url_for("index"))
    if len(password) < 8:
        flash("Password minimal 8 karakter.", "error")
        return redirect(url_for("index"))
    try:
        with db() as con:
            cur = con.execute(
                "INSERT INTO users(username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            session.clear()
            session["user_id"] = cur.lastrowid
            session["username"] = username
    except sqlite3.IntegrityError:
        flash("Username itu sudah dipakai. Coba nama lain.", "error")
        return redirect(url_for("index"))
    return redirect(url_for("index"))

@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with db() as con:
        user = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Username atau password salah.", "error")
        return redirect(url_for("index"))
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("index"))

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.get("/api/me")
@login_required
def me():
    return jsonify({"id": session["user_id"], "username": session["username"]})

@app.get("/api/users")
@login_required
def users():
    with db() as con:
        rows = con.execute("""
            SELECT u.id, u.username,
              (SELECT body FROM messages m
               WHERE (m.sender_id=u.id AND m.receiver_id=?)
                  OR (m.sender_id=? AND m.receiver_id=u.id)
               ORDER BY m.id DESC LIMIT 1) AS last_message,
              (SELECT created_at FROM messages m
               WHERE (m.sender_id=u.id AND m.receiver_id=?)
                  OR (m.sender_id=? AND m.receiver_id=u.id)
               ORDER BY m.id DESC LIMIT 1) AS last_time
            FROM users u WHERE u.id != ? ORDER BY COALESCE(last_time, u.created_at) DESC, u.username COLLATE NOCASE
        """, (session["user_id"], session["user_id"], session["user_id"], session["user_id"], session["user_id"])).fetchall()
    return jsonify([dict(r) for r in rows])

@app.get("/api/messages/<int:other_id>")
@login_required
def get_messages(other_id):
    after = request.args.get("after", "0")
    try:
        after_id = max(0, int(after))
    except ValueError:
        after_id = 0
    with db() as con:
        other = con.execute("SELECT id FROM users WHERE id=?", (other_id,)).fetchone()
        if not other or other_id == session["user_id"]:
            return jsonify({"error": "user_not_found"}), 404
        rows = con.execute("""
            SELECT m.id, m.sender_id, m.receiver_id, m.body, m.created_at, u.username AS sender
            FROM messages m JOIN users u ON u.id=m.sender_id
            WHERE ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
              AND m.id > ?
            ORDER BY m.id ASC LIMIT 200
        """, (session["user_id"], other_id, other_id, session["user_id"], after_id)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/messages/<int:other_id>")
@login_required
def send_message(other_id):
    data = request.get_json(silent=True) or {}
    body = str(data.get("body", "")).strip()
    if not body:
        return jsonify({"error": "Pesan tidak boleh kosong."}), 400
    if len(body) > 2000:
        return jsonify({"error": "Pesan maksimal 2000 karakter."}), 400
    if other_id == session["user_id"]:
        return jsonify({"error": "Tidak bisa mengirim pesan ke diri sendiri."}), 400
    with db() as con:
        recipient = con.execute("SELECT id FROM users WHERE id=?", (other_id,)).fetchone()
        if not recipient:
            return jsonify({"error": "Pengguna tidak ditemukan."}), 404
        cur = con.execute(
            "INSERT INTO messages(sender_id, receiver_id, body) VALUES (?, ?, ?)",
            (session["user_id"], other_id, body)
        )
        row = con.execute("""
            SELECT m.id, m.sender_id, m.receiver_id, m.body, m.created_at, u.username AS sender
            FROM messages m JOIN users u ON u.id=m.sender_id WHERE m.id=?
        """, (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201

@app.get("/health")
def health():
    return {"ok": True}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
