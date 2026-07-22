# Your Custom AI Agent -> Telegram

You're going to build an AI agent with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) and connect it to your own Telegram bot. By the end, you'll be able to message your agent from your phone, anywhere.

**The only file you will ever edit is [`agent.py`](agent.py).** Everything else is plumbing that's already wired up for you.

New to the Agents SDK? Work through [`notebooks/`](notebooks/) first -- it builds up every concept used here (agents, tools, multi-tool iteration, hosted tools, file handling, memory) step by step before you touch this repo.

## How it fits together

```
You message your bot on Telegram
        |
        v
Telegram calls your Vercel URL (app.py)
        |
        v
app.py hands your message to agent.py
        |
        v
Your agent (OpenAI Agents SDK) thinks, maybe uses a tool, replies
        |
        v
app.py sends the reply back to Telegram
        |
        v
You see the reply in the chat
```

`app.py` is the bridge. `agent.py` is your agent. You only customize the agent.

---

## Part 1 -- Build & test your agent locally

### 1. Get the code

If your instructor gave you a GitHub template link, click **"Use this template"** to get your own copy, then either:

- **Easiest, no install:** open your new repo on github.com and press the `.` key (period) -- this opens a full code editor in your browser (github.dev). Edit `agent.py` right there.
- **Or locally:** `git clone` your repo and open it in any editor.

### 2. Install dependencies

In a terminal, inside the project folder:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set your OpenAI API key

Copy `.env.example` to `.env` and fill in your key:

```bash
cp .env.example .env
```

That's it -- every local entry point (`local_chat.py`, `app.py`, `local_web.py`, `local_agent_chat.py`) automatically loads `.env` on startup, so nothing needs to be manually exported into your shell. `.env` is gitignored, so it never gets committed.

### 4. Customize your agent

Open [`agent.py`](agent.py) and edit:

- **`instructions`** -- your agent's personality and rules
- **`tools`** -- functions your agent can call (there are two examples already in there)

### 5. Chat with it in the terminal

```bash
python local_chat.py
```

Keep editing `agent.py` and re-running until you're happy with it. This is the fastest feedback loop -- no deployment needed yet.

---

## Part 2 -- Create your Telegram bot

1. Open Telegram, search for **`@BotFather`**, start a chat.
2. Send `/newbot`, follow the prompts (choose a name and a username ending in `bot`).
3. BotFather gives you a **token** that looks like `123456789:AAabc...`. Save it -- you'll need it below.

---

## Part 3 -- Deploy to Vercel (free)

We're using [Vercel](https://vercel.com) because its Python runtime is a real Python environment (not a sandboxed/limited one), so `openai-agents` just works, and its free "Hobby" tier gives function calls up to 5 minutes to run -- plenty for an agent that thinks and uses tools.

1. Push your repo to GitHub (skip if you used "Use this template" and already have one there).
2. Go to [vercel.com](https://vercel.com) and sign up (free, use your GitHub account).
3. Click **Add New -> Project**, then **Import** your repo.
4. Before deploying, open **Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `OPENAI_API_KEY` | your OpenAI key |
   | `TELEGRAM_BOT_TOKEN` | the token from BotFather |
   | `TELEGRAM_WEBHOOK_SECRET` | any random string you make up (e.g. `mango-tiger-42`) |

5. Click **Deploy**. When it finishes, copy your project's URL (something like `https://your-project.vercel.app`).

### Verify it's alive

Paste your URL into a browser. You should see:

```json
{"status": "ok", "agent": "My Telegram Assistant"}
```

---

## Part 4 -- Connect Telegram to your deployment

Telegram needs to know where to send messages. The easiest way: visit **`https://<YOUR_VERCEL_URL>/setup`** in your browser -- a small helper page (already built into this repo) that lets you connect, check the status of, or stop your bot with a few clicks instead of hand-building URLs. Paste in your bot token and a webhook secret of your choosing, and click **Set Webhook**. Every button on that page talks to Telegram directly from your browser -- your token never touches this app's own server.

<details>
<summary>Prefer to do it manually?</summary>

Paste this into your **browser address bar** (edit the two placeholders first):

```
https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<YOUR_VERCEL_URL>/webhook&secret_token=<YOUR_TELEGRAM_WEBHOOK_SECRET>
```

- `<YOUR_TELEGRAM_BOT_TOKEN>` -- from BotFather
- `<YOUR_VERCEL_URL>` -- your Vercel project URL, no trailing slash
- `<YOUR_TELEGRAM_WEBHOOK_SECRET>` -- the same string you set as `TELEGRAM_WEBHOOK_SECRET` in Vercel

You should see `{"ok":true,"result":true,"description":"Webhook was set"}`.

</details>

### Talk to your agent

Open Telegram, find the bot you created with BotFather, and send it a message. It's live!

---

## Making changes after deploying

1. Edit `agent.py` (in github.dev or locally).
2. Commit and push.
3. Vercel automatically redeploys -- no need to redo Part 4.

---

## Troubleshooting

**Bot doesn't respond at all**
- Recheck the `setWebhook` URL step -- a typo in the token or URL is the most common cause.
- Visit your Vercel URL in a browser -- if it doesn't return `{"status": "ok", ...}`, the deployment itself is broken. Check the **Logs** tab on your Vercel project.

**Bot responds with an error / gives a generic failure**
- Check Vercel's **Logs** tab for the actual Python error.
- Most common cause: `OPENAI_API_KEY` missing, mistyped, or out of quota.

**`{"ok":false,...}` when calling setWebhook**
- Your `TELEGRAM_BOT_TOKEN` is probably wrong, or the Vercel URL isn't reachable yet (wait for the deploy to finish).

**I changed `agent.py` but nothing changed**
- Make sure you pushed the commit -- check the **Deployments** tab on Vercel to see if a new deploy actually ran.

**The bot seems stuck in a loop, repeating the same tool calls**
- This shouldn't happen anymore. `/webhook` responds to Telegram immediately (well under a second), *before* the agent even starts running -- the actual work happens in a separate `/process` request that Telegram never waits on. Telegram only retries a message when it gets tired of waiting for a response, so there's no longer anything for it to wait on and no reason for it to retry. (Earlier versions of this template tried to fix this by racing a timeout instead -- that didn't fully work, because Telegram can give up waiting *before* the timeout even fires. Handing off to `/process` fixes the actual cause instead of a symptom.)
- `AGENT_TIMEOUT_SECONDS` in `app.py` (270s) still exists, but only as a cost safety net -- it stops a single run from burning unbounded OpenAI API spend if a model gets stuck, unrelated to Telegram at all.
- If you somehow still see repeated identical tool calls, check Vercel's **Logs** tab for `/webhook` -- it should show exactly one invocation per message, returning `200` in milliseconds. If you see more than one `/webhook` call for the same message, or any non-200 there, something's misconfigured (check `APP_URL`/`VERCEL_URL` below). If instead `/process` shows one long-running invocation, that's just the agent genuinely working through a complex request -- not a loop.
- To stop a bot immediately for any reason (e.g. it's burning through your OpenAI credits on something you don't want):
  1. Visit `https://<YOUR_VERCEL_URL>/setup` and click **Stop Bot**. (Or manually: `https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true`.)
  2. Once things are calm, use the **Set Webhook** button on the same page to resume.
- **Don't reach for Vercel's "Pause Project" button for this** -- pausing is the right tool for "I want my whole deployment offline for a while" (e.g. to avoid usage costs), not for stopping one bot -- the `/setup` page's Stop Bot button is.

**`/webhook` returns an error mentioning `VERCEL_URL` or `APP_URL`**
- `/webhook` needs to know this deployment's own URL to call `/process`. Vercel provides this automatically as `VERCEL_URL`, but it requires **"Enable access to System Environment Variables"** to be checked in your Vercel project's Environment Variables settings. If you'd rather not enable that, set an `APP_URL` environment variable yourself instead (same value as your Vercel URL, no `https://` prefix).

---

## What your bot can read

Your agent can already handle, out of the box:
- **Text** messages
- **Photos** (it can see and describe/reason about images)
- **Documents**, including PDFs (it reads the file directly)

It doesn't yet handle voice notes, video, or stickers -- it'll politely say so if you send one.

## Tools

`agent.py` starts with two kinds of tools already wired up:

**Custom tools** -- a normal Python function with `@function_tool` on it. `get_current_time`, `roll_dice`, `read_dynamic_webpage`, and `get_stock_fundamentals` (price + key ratios via [yfinance](https://pypi.org/project/yfinance/), no API key needed) are examples. Write your own the same way: docstring and type hints matter, since the agent reads them to decide when and how to call the function.

**Built-in hosted tools** -- pre-built by OpenAI, no code required, just add them to `tools=`:

- **`WebSearchTool()`** -- live web search.
- **`CodeInterpreterTool()`** -- runs real Python (pandas etc.) in a sandbox. This is what you want for spreadsheets: if someone sends your bot a CSV or Excel file, the model can open it in a real Python environment and compute exact answers instead of guessing. It works automatically with the photo/document upload already wired up in `app.py` -- nothing else to change.

### Chaining tools: data in, spreadsheet out

Try asking the bot: *"Give me a spreadsheet analysis of Nvidia fundamentals."* It'll chain tools on its own: call `get_stock_fundamentals("NVDA")` for the numbers, then use `code_interpreter` to actually build a `.xlsx` file from them (not just describe the numbers in the chat). Any file the agent generates this way is automatically downloaded and sent to you as a Telegram document, alongside its usual text reply.

This works because `agent.py`'s instructions explicitly tell it to build a real file for "spreadsheet"/"report" requests -- without that nudge, a model will often just summarize the numbers in text instead of reaching for code_interpreter's file-writing ability. The default agent loop already supports calling multiple tools in sequence before answering (see "Seeing the agent's tool calls" below to watch it happen) -- no extra configuration needed for that part.

### A note on dynamic websites

`CodeInterpreterTool` is a sandboxed Python VM -- it can run code, but it can't open a browser, click things, or wait for JavaScript to render a page. For that, OpenAI has a separate `ComputerTool` (a "computer-use" agent that sees screenshots and issues clicks/keystrokes), but it expects *you* to supply the actual browser it controls (typically via a hosted browser service) -- real infrastructure, well beyond a one-file course project.

For the common case -- reading content off a page that loads its content via JavaScript -- `read_dynamic_webpage` in `agent.py` is enough. It calls a free JS-rendering service ([r.jina.ai](https://jina.ai/reader/)) instead of fetching raw HTML, so it sees the same page a real browser would.

## Seeing the agent's tool calls (and thinking) -- live

For learning purposes, your bot streams what it's doing to Telegram as separate messages *while it's still working*, not batched into one message after the fact. Ask for something that needs a few steps and you'll see them arrive one at a time, in real time, something like:

```
🧠 I should check the current stock price.
🔧 get_stock_price({"ticker": "D05.SI"})
```
*(a moment later)*
```
   -> D05.SI: 71.96 SGD
```
*(then the actual reply, once it's ready)*

This uses the SDK's streaming mode (`Runner.run_streamed`, iterating `stream_events()`) rather than waiting for the whole run to finish -- each tool call, tool result, and reasoning step is sent to Telegram the moment it happens.

- 🔧 lines show every tool call and its arguments -- this works for any model, and is usually what you want to demonstrate in class.
- 🧠 lines show the model's reasoning summary. These **only** appear if `agent.py` is using a reasoning-capable model (a `gpt-5-thinking`- or `o`-series model) *and* has `model_settings=ModelSettings(reasoning={"summary": "auto"})` set -- see the commented-out example at the bottom of `agent.py`. Reasoning models are slower and cost more per message, so this is off by default; regular tool-call tracing works without it.

Turn the whole thing off (e.g. once you want the bot to feel more "finished") by setting `SHOW_AGENT_TRACE=false` in your Vercel environment variables -- no code changes needed.

## `local_agent.py` -- a separate agent with real shell access

`local_agent.py` and `local_agent_chat.py` are a **local-only** counterpart to your Telegram agent -- run `python local_agent_chat.py` to chat with an agent that has a similar toolset to your Telegram bot, plus a real shell tool that can run commands on your own machine.

**This is not part of the Telegram bot, and it's fully self-contained.** `app.py` never imports `local_agent.py` -- there's no path from a Telegram message to shell access. Its tools are also defined directly in `local_agent.py` rather than imported from `agent.py`, on purpose: editing your Telegram agent for the course never has any effect on this file, and vice versa.

**Read this before running it:** the shell tool is configured with `needs_approval=False` -- commands the model decides to run execute immediately, with no confirmation step, exactly as if you'd typed them into your own terminal. That's a reasonable choice *because* it's local-only and you're the only one who can trigger it, but it means real destructive commands (deleting files, etc.) are only prevented by the agent's own instructions telling it to be careful -- not by any code-level safeguard. If you want a confirmation step, `ShellTool(needs_approval=True, on_approval=...)` in `local_agent.py` is where to add it.

**No `code_interpreter` here, unlike the Telegram agent.** OpenAI's API rejects `code_interpreter` and `shell` in the same agent outright (`400: code_interpreter and shell with an OpenAI-managed container cannot be used together at the same time`) -- found this the hard way when the local web chat returned a bare 500 with a real API key. Not a problem in practice: with real shell access, `local_agent` can just run `python3 -c "..."` directly instead of reaching for a separate sandboxed tool.

## Web chat -- two separate pages, two separate agents

Besides Telegram, both agents also have a simple browser-based chat UI:

| Page | Agent | Run it with | Safe to deploy? |
|---|---|---|---|
| `/chat` on your deployed URL (or `http://127.0.0.1:8000/chat` locally) | The same `agent` your Telegram bot uses | Already part of `app.py` -- nothing extra to run | Yes -- no shell access, same agent either way |
| `http://127.0.0.1:8001/chat` | `local_agent` (shell-enabled) | `uvicorn local_web:app --port 8001 --reload` | **No -- local only.** Not deployed by Vercel (nothing in `vercel.json` references `local_web.py`); never expose this to a network you don't fully trust. |

Both pages are the same simple UI (`chat_ui.py`, shared between them, distinguished only by a color-coded badge) -- type a message, see the agent's tool-call trace above each reply, keep chatting. Conversation history is kept in the browser tab (lost on refresh), no database involved. The shared chat-handling logic lives in `trace_utils.py`.

## Extension ideas (if you finish early)

- Give your agent a second specialist agent and use `handoffs=[...]` to route between them.
- Add real conversation memory to the deployed bot (right now each message is stateless) using the SDK's [Sessions](https://openai.github.io/openai-agents-python/sessions/) with a small hosted database like Vercel KV or Upstash Redis.
- Add voice note support by transcribing with OpenAI's transcription API before handing the text to your agent.
- Swap Telegram for email (same `agent.py`, different bridge file).
