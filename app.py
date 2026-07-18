"""
Telegram <-> OpenAI Agents SDK bridge.

This is infrastructure code -- you do NOT need to edit this file
for the course. Your agent lives in agent.py.

What this does:
  1. Vercel deploys this file as a web server (Vercel auto-detects
     the `app` variable below as an ASGI app).
  2. Telegram sends every new message to POST /webhook.
  3. We turn the message (text, and/or a photo/document) into input
     for your agent and send its reply back to Telegram.

Photos and documents (e.g. PDFs) are uploaded to OpenAI's Files API
and passed to the agent by reference (file_id) -- the model reads
them directly, so we never have to parse file contents ourselves.

For learning purposes, we also send a second message showing the
agent's tool calls (and its reasoning, if the model supports it)
before the actual reply. Set SHOW_AGENT_TRACE=false in your
environment variables to turn this off.
"""

import os

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from openai import AsyncOpenAI

from agents import Runner

from agent import agent

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"
SHOW_AGENT_TRACE = os.environ.get("SHOW_AGENT_TRACE", "true").lower() != "false"

openai_client = AsyncOpenAI()


@app.get("/")
async def health_check():
    """Visit your deployed URL in a browser to confirm it's alive."""
    return {"status": "ok", "agent": agent.name}


async def _download_telegram_file(client: httpx.AsyncClient, file_id: str) -> tuple[bytes, str]:
    """Resolve a Telegram file_id to its raw bytes and filename."""
    resp = await client.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]

    file_resp = await client.get(f"{TELEGRAM_FILE_URL}/{file_path}")
    file_resp.raise_for_status()

    filename = file_path.rsplit("/", 1)[-1]
    return file_resp.content, filename


async def _build_input_content(client: httpx.AsyncClient, message: dict) -> list[dict]:
    """Turn a Telegram message (text, photo, and/or document) into agent input content."""
    content: list[dict] = []

    caption_or_text = message.get("text") or message.get("caption") or ""
    if caption_or_text:
        content.append({"type": "input_text", "text": caption_or_text})

    if "photo" in message:
        # Telegram sends the same photo at several resolutions; the
        # last entry is the largest.
        file_id = message["photo"][-1]["file_id"]
        file_bytes, filename = await _download_telegram_file(client, file_id)
        uploaded = await openai_client.files.create(file=(filename, file_bytes), purpose="vision")
        content.append({"type": "input_image", "file_id": uploaded.id, "detail": "auto"})

    if "document" in message:
        file_id = message["document"]["file_id"]
        filename = message["document"].get("file_name", "document")
        file_bytes, _ = await _download_telegram_file(client, file_id)
        uploaded = await openai_client.files.create(file=(filename, file_bytes), purpose="user_data")
        content.append({"type": "input_file", "file_id": uploaded.id, "filename": filename})

    return content


def _format_agent_trace(new_items: list) -> str | None:
    """Turn a run's reasoning and tool calls into a readable trace, for learning purposes.

    "Thinking" lines only appear if agent.py uses a reasoning-capable
    model with reasoning summaries turned on -- see the note in
    agent.py. Tool call lines appear for any model.
    """
    lines = []
    for item in new_items:
        if item.type == "reasoning_item":
            for summary in item.raw_item.summary:
                lines.append(f"🧠 {summary.text}")
        elif item.type == "tool_call_item":
            name = item.tool_name or "tool"
            args = getattr(item.raw_item, "arguments", None)
            lines.append(f"🔧 {name}({args or ''})")
        elif item.type == "tool_call_output_item":
            preview = str(item.output)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            lines.append(f"   -> {preview}")

    return "\n".join(lines) if lines else None


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Reject anything that isn't really from Telegram.
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret token")

    update = await request.json()
    message = update.get("message")

    if not message:
        # Ignore anything that isn't a regular message (edited messages,
        # channel posts, etc.) so Telegram doesn't keep retrying it.
        return {"ok": True}

    chat_id = message["chat"]["id"]
    is_supported = any(key in message for key in ("text", "photo", "document"))

    async with httpx.AsyncClient() as client:
        if not is_supported:
            # Stickers, voice notes, video, etc. aren't handled yet.
            reply_text = "I can only read text, photos, and documents (like PDFs) right now -- try sending one of those!"
        else:
            content = await _build_input_content(client, message)
            result = await Runner.run(agent, [{"role": "user", "content": content}])
            reply_text = result.final_output or "..."

            if SHOW_AGENT_TRACE:
                trace = _format_agent_trace(result.new_items)
                if trace:
                    # Sent as plain text (no Markdown parsing) since tool
                    # output can contain characters that would otherwise
                    # break Telegram's formatting.
                    await client.post(
                        f"{TELEGRAM_API_URL}/sendMessage",
                        json={"chat_id": chat_id, "text": trace},
                    )

        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text},
        )

    return {"ok": True}
