
import os
import hmac
import time
from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)

# Geheimnisse werden ausschließlich auf Render gespeichert.
secret_key = os.environ.get("JARVIS_SESSION_SECRET")
if not secret_key:
    raise RuntimeError("JARVIS_SESSION_SECRET fehlt")

app.secret_key = secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None",
    PERMANENT_SESSION_LIFETIME=3600,
    MAX_CONTENT_LENGTH=16384,
)

FRONTEND_ORIGIN = "https://tayfunerol100693.github.io"

CORS(
    app,
    resources={
        r"/login": {"origins": [FRONTEND_ORIGIN]},
        r"/logout": {"origins": [FRONTEND_ORIGIN]},
        r"/chat": {"origins": [FRONTEND_ORIGIN]},
        r"/auth-status": {"origins": [FRONTEND_ORIGIN]},
    },
    supports_credentials=True,
)

# Einfache Begrenzung fehlgeschlagener Anmeldungen.
failed_logins = {}
WINDOW = 900
MAX_ATTEMPTS = 5

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return jsonify({"error": "Bitte anmelden"}), 401
        return function(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    return jsonify({"status": "JARVIS Backend online"})

@app.post("/login")
def login():
    ip = request.remote_addr or "unknown"
    now = time.monotonic()

    attempts = [
        t for t in failed_logins.get(ip, [])
        if now - t < WINDOW
    ]
    failed_logins[ip] = attempts

    if len(attempts) >= MAX_ATTEMPTS:
        return jsonify({
            "error": "Zu viele Versuche. Bitte später erneut versuchen."
        }), 429

    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    expected = os.environ.get("JARVIS_PASSWORD", "")

    if not isinstance(password, str) or not expected:
        return jsonify({"error": "Anmeldung nicht verfügbar"}), 503

    if not hmac.compare_digest(password, expected):
        attempts.append(now)
        failed_logins[ip] = attempts
        return jsonify({"error": "Falsches Passwort"}), 401

    failed_logins.pop(ip, None)
    session.clear()
    session.permanent = True
    session["authenticated"] = True

    return jsonify({"success": True})

@app.get("/auth-status")
def auth_status():
    return jsonify({
        "authenticated": bool(session.get("authenticated"))
    })

@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"success": True})

@app.post("/chat")
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Bitte Nachricht eingeben"}), 400

    if len(message) > 4000:
        return jsonify({"error": "Nachricht zu lang"}), 400

    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error": "KI noch nicht konfiguriert"}), 503

    try:
        client = OpenAI()
        response = client.responses.create(
            model="gpt-4.1-mini",
            instructions=(
                "Du bist JARVIS, ein deutschsprachiger "
                "persönlicher KI-Assistent. "
                "Antworte hilfreich, klar und natürlich. "
                "Behaupte niemals, externe Aktionen "
                "ausgeführt zu haben, wenn das nicht stimmt."
            ),
            input=message,
            max_output_tokens=500,
        )
        return jsonify({"reply": response.output_text})
    except Exception:
        app.logger.exception("OpenAI-Anfrage fehlgeschlagen")
        return jsonify({"error": "KI-Anfrage fehlgeschlagen"}), 502
