const API_URL = "http://localhost:5000/chat";

const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");
const button = form.querySelector("button");

let chatId = localStorage.getItem("chat_id") || "";

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
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, chat_id: chatId || undefined }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Błąd");

    if (data.chat_id) {
      chatId = data.chat_id;
      localStorage.setItem("chat_id", chatId);
    }
    addMsg(data.reply, "bot");
  } catch (err) {
    addMsg("Błąd: " + err.message, "bot");
  } finally {
    button.disabled = false;
    input.focus();
  }
});
