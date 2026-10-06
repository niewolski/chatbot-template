import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI-API")
MODEL = os.getenv("GEMINI-MODEL")
SYSTEM_PROMPT = (BASE_DIR / "bot" / "prompts" / "system_instructions.txt").read_text(
    encoding="utf-8"
).strip()

if not API_KEY or not MODEL:
    raise RuntimeError("Uzupełnij GEMINI-API i GEMINI-MODEL w pliku .env")

client = genai.Client(api_key=API_KEY)
app = Flask(__name__)
CORS(app)

chats: dict[str, list[types.Content]] = {}


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    chat_id = (data.get("chat_id") or "").strip() or os.urandom(8).hex()

    if not message:
        return jsonify({"error": "Pusta wiadomość"}), 400

    history = chats.setdefault(chat_id, [])
    history.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        reply = (response.text or "").strip() or "(brak odpowiedzi)"
    except Exception as exc:
        history.pop()
        return jsonify({"error": str(exc)}), 500

    history.append(types.Content(role="model", parts=[types.Part(text=reply)]))
    return jsonify({"reply": reply, "chat_id": chat_id})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
