"""
The /setup helper page -- a small browser-based UI for registering,
checking, and stopping your bot's Telegram webhook, instead of
constructing and pasting URLs by hand.

This is infrastructure code -- you do NOT need to edit this file.

Security note: every button on this page talks to Telegram's API
*directly from your browser* (plain fetch() calls to
api.telegram.org). Your bot token never passes through this app's
own server, isn't logged anywhere, and isn't written to disk --
only to your browser's sessionStorage, so it's forgotten the moment
you close the tab.
"""

ADMIN_PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot Setup Helper</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f7f7f8;
    --card: #ffffff;
    --border: #e2e2e6;
    --text: #1a1a1d;
    --muted: #6b6b70;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --danger: #dc2626;
    --danger-hover: #b91c1c;
    --ok: #16a34a;
    --err: #dc2626;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16171a;
      --card: #1f2023;
      --border: #313236;
      --text: #f2f2f3;
      --muted: #a0a0a6;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 2rem 1rem 4rem;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.5;
  }
  main { max-width: 640px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin: 0 0 0.25rem; }
  .subtitle { color: var(--muted); margin: 0 0 1.5rem; font-size: 0.95rem; }
  .notice {
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 0.9rem 1rem;
    font-size: 0.88rem;
    color: var(--muted);
    margin-bottom: 1.5rem;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
  }
  .card h2 {
    font-size: 1.05rem;
    margin: 0 0 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    background: var(--accent);
    color: white;
    font-size: 0.8rem;
    flex-shrink: 0;
  }
  label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
    margin-top: 0.9rem;
  }
  label:first-of-type { margin-top: 0; }
  .field-hint { font-weight: 400; color: var(--muted); font-size: 0.8rem; }
  input[type="text"], input[type="password"] {
    width: 100%;
    padding: 0.55rem 0.7rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font-size: 0.9rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .url-row { display: flex; gap: 0.5rem; }
  .url-row input { flex: 1; }
  .inline-btn {
    padding: 0.55rem 0.8rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
  }
  .inline-btn:hover { border-color: var(--accent); }
  .actions { display: flex; gap: 0.6rem; margin-top: 1.1rem; flex-wrap: wrap; }
  button.primary {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.1rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }
  button.primary:hover { background: var(--accent-hover); }
  button.danger {
    background: transparent;
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 8px;
    padding: 0.6rem 1.1rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }
  button.danger:hover { background: var(--danger); color: white; }
  button.secondary {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 1.1rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }
  button.secondary:hover { border-color: var(--accent); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  #log {
    display: flex;
    flex-direction: column-reverse;
    gap: 0.6rem;
    margin-top: 1.5rem;
  }
  .log-entry {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.85rem;
  }
  .log-entry.ok { border-left: 3px solid var(--ok); }
  .log-entry.err { border-left: 3px solid var(--err); }
  .log-title { font-weight: 600; margin-bottom: 0.35rem; }
  .log-title .status { font-weight: 400; color: var(--muted); }
  .log-entry pre {
    margin: 0.4rem 0 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .empty-log { color: var(--muted); font-size: 0.85rem; text-align: center; padding: 1rem 0; }
</style>
</head>
<body>
<main>
  <h1>Bot Setup Helper</h1>
  <p class="subtitle">Connect, check, or stop your Telegram bot's webhook -- no URL-pasting required.</p>

  <div class="notice">
    🔒 Every button here calls Telegram's API directly from <em>your browser</em>. Your bot token
    never touches this app's server or gets logged -- it's only kept in this tab's session memory,
    and forgotten the moment you close it.
  </div>

  <div class="card">
    <h2><span class="step-num">1</span> Connect your bot</h2>

    <label for="token">Bot token <span class="field-hint">from @BotFather</span></label>
    <input type="password" id="token" placeholder="123456789:AA...">

    <label for="secret">Webhook secret <span class="field-hint">any random string you choose</span></label>
    <div class="url-row">
      <input type="text" id="secret" placeholder="mango-tiger-42">
      <button class="inline-btn" id="generate-secret" type="button">Generate</button>
    </div>

    <label for="webhook-url">Webhook URL <span class="field-hint">auto-filled from this page</span></label>
    <div class="url-row">
      <input type="text" id="webhook-url" readonly>
      <button class="inline-btn" id="copy-url" type="button">Copy</button>
    </div>

    <div class="actions">
      <button class="primary" id="set-webhook" type="button">Set Webhook</button>
    </div>
  </div>

  <div class="card">
    <h2><span class="step-num">2</span> Check status</h2>
    <p class="field-hint" style="margin: 0 0 0.9rem;">
      Uses the bot token from step 1. Shows whether the webhook is registered and how many
      messages are waiting to be delivered.
    </p>
    <div class="actions">
      <button class="secondary" id="check-status" type="button">Check Status</button>
    </div>
  </div>

  <div class="card">
    <h2><span class="step-num">3</span> Stop the bot</h2>
    <p class="field-hint" style="margin: 0 0 0.9rem;">
      Removes the webhook and drops any queued messages. Use this if your bot seems stuck
      retrying the same thing -- it stops Telegram from redelivering the stuck message. Run
      step 1 again whenever you're ready to resume.
    </p>
    <div class="actions">
      <button class="danger" id="stop-bot" type="button">Stop Bot</button>
    </div>
  </div>

  <div id="log"></div>
</main>

<script>
(function () {
  const tokenEl = document.getElementById("token");
  const secretEl = document.getElementById("secret");
  const urlEl = document.getElementById("webhook-url");
  const logEl = document.getElementById("log");

  // Prefill from this tab's session (never sent anywhere but Telegram,
  // never written to disk) so you don't retype between steps.
  tokenEl.value = sessionStorage.getItem("botToken") || "";
  secretEl.value = sessionStorage.getItem("webhookSecret") || "";
  urlEl.value = window.location.origin + "/webhook";

  tokenEl.addEventListener("input", () => sessionStorage.setItem("botToken", tokenEl.value));
  secretEl.addEventListener("input", () => sessionStorage.setItem("webhookSecret", secretEl.value));

  document.getElementById("generate-secret").addEventListener("click", () => {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    const random = Array.from(bytes, (b) => b.toString(36)).join("").slice(0, 16);
    secretEl.value = random;
    sessionStorage.setItem("webhookSecret", random);
  });

  document.getElementById("copy-url").addEventListener("click", async () => {
    await navigator.clipboard.writeText(urlEl.value);
    const btn = document.getElementById("copy-url");
    const original = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = original), 1200);
  });

  function requireToken() {
    const token = tokenEl.value.trim();
    if (!token) {
      alert("Enter your bot token in step 1 first.");
      return null;
    }
    return token;
  }

  function addLogEntry(title, ok, data) {
    const entry = document.createElement("div");
    entry.className = "log-entry " + (ok ? "ok" : "err");
    const time = new Date().toLocaleTimeString();
    entry.innerHTML =
      '<div class="log-title">' + title + ' <span class="status">' + (ok ? "succeeded" : "failed") + " · " + time + '</span></div>' +
      "<pre></pre>";
    entry.querySelector("pre").textContent = JSON.stringify(data, null, 2);
    logEl.prepend(entry);
  }

  async function callTelegram(token, method, params) {
    const url = new URL("https://api.telegram.org/bot" + token + "/" + method);
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
    const resp = await fetch(url.toString());
    const data = await resp.json();
    return { ok: resp.ok && data.ok, data };
  }

  function setBusy(button, busy) {
    button.disabled = busy;
  }

  document.getElementById("set-webhook").addEventListener("click", async () => {
    const token = requireToken();
    if (!token) return;
    const button = document.getElementById("set-webhook");
    setBusy(button, true);
    try {
      const { ok, data } = await callTelegram(token, "setWebhook", {
        url: urlEl.value,
        secret_token: secretEl.value.trim(),
      });
      addLogEntry("Set webhook", ok, data);
    } catch (e) {
      addLogEntry("Set webhook", false, { error: String(e) });
    } finally {
      setBusy(button, false);
    }
  });

  document.getElementById("check-status").addEventListener("click", async () => {
    const token = requireToken();
    if (!token) return;
    const button = document.getElementById("check-status");
    setBusy(button, true);
    try {
      const { ok, data } = await callTelegram(token, "getWebhookInfo", {});
      addLogEntry("Webhook status", ok, data.result || data);
    } catch (e) {
      addLogEntry("Webhook status", false, { error: String(e) });
    } finally {
      setBusy(button, false);
    }
  });

  document.getElementById("stop-bot").addEventListener("click", async () => {
    const token = requireToken();
    if (!token) return;
    if (!confirm("This stops your bot and drops any queued messages. Continue?")) return;
    const button = document.getElementById("stop-bot");
    setBusy(button, true);
    try {
      const { ok, data } = await callTelegram(token, "deleteWebhook", {
        drop_pending_updates: "true",
      });
      addLogEntry("Stop bot", ok, data);
    } catch (e) {
      addLogEntry("Stop bot", false, { error: String(e) });
    } finally {
      setBusy(button, false);
    }
  });
})();
</script>
</body>
</html>
"""
