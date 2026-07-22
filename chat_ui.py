"""
A simple, self-contained web chat page -- shared by app.py (talks to
the Telegram agent) and local_web.py (talks to the local shell
agent). Both POST to a relative /chat endpoint, so the same HTML
works for either server; only the title/subtitle/badge differ.
"""


def render_chat_page(title: str, subtitle: str, badge: str, badge_color: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f7f7f8;
    --card: #ffffff;
    --border: #e2e2e6;
    --text: #1a1a1d;
    --muted: #6b6b70;
    --accent: {badge_color};
    --bubble-user: {badge_color};
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #16171a;
      --card: #1f2023;
      --border: #313236;
      --text: #f2f2f3;
      --muted: #a0a0a6;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }}
  header {{
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: var(--card);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }}
  header h1 {{ font-size: 1.1rem; margin: 0; }}
  header p {{ font-size: 0.8rem; color: var(--muted); margin: 0.2rem 0 0; }}
  .badge {{
    background: var(--accent);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.3rem 0.6rem;
    border-radius: 999px;
    white-space: nowrap;
  }}
  #messages {{
    flex: 1;
    overflow-y: auto;
    padding: 1.25rem;
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
  }}
  .msg {{ margin-bottom: 1rem; display: flex; }}
  .msg.user {{ justify-content: flex-end; }}
  .msg.agent {{ justify-content: flex-start; }}
  .bubble {{
    max-width: 80%;
    padding: 0.65rem 0.9rem;
    border-radius: 14px;
    font-size: 0.92rem;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
  }}
  .msg.user .bubble {{ background: var(--bubble-user); color: white; border-bottom-right-radius: 4px; }}
  .msg.agent .bubble {{ background: var(--card); border: 1px solid var(--border); border-bottom-left-radius: 4px; }}
  .trace {{
    max-width: 80%;
    margin: 0.35rem 0 0;
    font-size: 0.78rem;
    color: var(--muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    white-space: pre-wrap;
    word-break: break-word;
    border-left: 2px solid var(--border);
    padding-left: 0.6rem;
  }}
  .status {{ font-size: 0.8rem; color: var(--muted); padding: 0 0.2rem; }}
  .files {{
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin: 0.35rem 0 0;
  }}
  .file-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    width: fit-content;
    max-width: 80%;
    padding: 0.5rem 0.8rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    font-size: 0.85rem;
    text-decoration: none;
  }}
  .file-link:hover {{ border-color: var(--accent); }}
  form {{
    display: flex;
    gap: 0.6rem;
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--border);
    background: var(--card);
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
    flex-shrink: 0;
  }}
  input[type="text"] {{
    flex: 1;
    padding: 0.65rem 0.9rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font-size: 0.95rem;
  }}
  button {{
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.2rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }}
  button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>
  <span class="badge">{badge}</span>
</header>

<div id="messages"></div>

<form id="chat-form">
  <input type="text" id="input" placeholder="Type a message..." autocomplete="off">
  <button type="submit" id="send-btn">Send</button>
</form>

<script>
(function () {{
  const messagesEl = document.getElementById("messages");
  const formEl = document.getElementById("chat-form");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("send-btn");

  let history = [];

  function addBubble(role, text) {{
    const row = document.createElement("div");
    row.className = "msg " + (role === "user" ? "user" : "agent");
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return row;
  }}

  function addTrace(lines) {{
    if (!lines || !lines.length) return;
    const el = document.createElement("div");
    el.className = "trace";
    el.textContent = lines.join("\\n");
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }}

  function addFiles(files) {{
    if (!files || !files.length) return;
    const row = document.createElement("div");
    row.className = "msg agent";
    const wrap = document.createElement("div");
    wrap.className = "files";
    files.forEach((f) => {{
      const link = document.createElement("a");
      link.className = "file-link";
      link.href = f.data_url;
      link.download = f.filename;
      link.textContent = "📄 Download " + f.filename;
      wrap.appendChild(link);
    }});
    row.appendChild(wrap);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }}

  function addStatus(text) {{
    const el = document.createElement("div");
    el.className = "status";
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }}

  formEl.addEventListener("submit", async (e) => {{
    e.preventDefault();
    const message = inputEl.value.trim();
    if (!message) return;

    addBubble("user", message);
    inputEl.value = "";
    inputEl.disabled = true;
    sendBtn.disabled = true;
    const statusEl = addStatus("Thinking...");

    try {{
      const resp = await fetch("/chat", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ message: message, history: history }}),
      }});
      const data = await resp.json();
      statusEl.remove();

      if (!resp.ok) {{
        addBubble("agent", "Error: " + (data.detail || resp.statusText));
      }} else {{
        addTrace(data.trace);
        addBubble("agent", data.reply);
        addFiles(data.files);
        history = data.history || history;
      }}
    }} catch (err) {{
      statusEl.remove();
      addBubble("agent", "Error: " + String(err));
    }} finally {{
      inputEl.disabled = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }}
  }});

  inputEl.focus();
}})();
</script>
</body>
</html>
"""
