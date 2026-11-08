import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({"status": "JARVIS Backend online"})

@app.post("/chat")
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
            max_output_tokens=500
        )
        return jsonify({"reply": response.output_text})
    except Exception:
        app.logger.exception("OpenAI-Anfrage fehlgeschlagen")
        return jsonify({"error": "KI-Anfrage fehlgeschlagen"}), 502
