import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request, session
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
app.secret_key = os.urandom(24)

# Prosta pamięć historii rozmów (session_id -> lista wiadomości)
chats: dict[str, list[types.Content]] = {}

HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Chatbot</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(160deg, #1a2332 0%, #2d3a4f 50%, #1e2a3a 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #e8e4dc;
    }
    .chat {
      width: min(560px, 94vw);
      height: min(700px, 90vh);
      display: flex;
      flex-direction: column;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      overflow: hidden;
    }
    h1 {
      margin: 0;
      padding: 1rem 1.25rem;
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      background: rgba(0,0,0,0.15);
    }
    #messages {
      flex: 1;
      overflow-y: auto;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .msg {
      max-width: 85%;
      padding: 0.65rem 0.9rem;
      border-radius: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .user {
      align-self: flex-end;
      background: #c4a574;
      color: #1a1814;
    }
    .bot {
      align-self: flex-start;
      background: rgba(255,255,255,0.1);
    }
    form {
      display: flex;
      gap: 0.5rem;
      padding: 1rem;
      border-top: 1px solid rgba(255,255,255,0.1);
      background: rgba(0,0,0,0.15);
    }
    input {
      flex: 1;
      padding: 0.7rem 1rem;
      border: 1px solid rgba(255,255,255,0.2);
      border-radius: 10px;
      background: rgba(255,255,255,0.08);
      color: #e8e4dc;
      font: inherit;
      outline: none;
    }
    input:focus { border-color: #c4a574; }
    button {
      padding: 0.7rem 1.1rem;
      border: none;
      border-radius: 10px;
      background: #c4a574;
      color: #1a1814;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    button:disabled { opacity: 0.5; cursor: wait; }
  </style>
</head>
<body>
  <div class="chat">
    <h1>Chatbot</h1>
    <div id="messages"></div>
    <form id="form">
      <input id="input" type="text" placeholder="Napisz wiadomość..." autocomplete="off" required />
      <button type="submit">Wyślij</button>
    </form>
  </div>
  <script>
    const messages = document.getElementById("messages");
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const button = form.querySelector("button");

    function addMsg(text, role) {
      const el = document.createElement("div");
      el.className = "msg " + role;
      el.textContent = text;
      messages.appendChild(el);
      messages.scrollTop = messages.scrollHeight;
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      addMsg(text, "user");
      input.value = "";
      button.disabled = true;
      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Błąd");
        addMsg(data.reply, "bot");
      } catch (err) {
        addMsg("Błąd: " + err.message, "bot");
      } finally {
        button.disabled = false;
        input.focus();
      }
    });
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Pusta wiadomość"}), 400

    sid = session.get("chat_id")
    if not sid:
        sid = os.urandom(8).hex()
        session["chat_id"] = sid
        chats[sid] = []

    history = chats.setdefault(sid, [])
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
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
