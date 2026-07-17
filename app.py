"""
Telegram <-> OpenAI Agents SDK bridge.

This is infrastructure code -- you do NOT need to edit this file
for the course. Your agent lives in agent.py.

What this does:
  1. Vercel deploys this file as a web server (Vercel auto-detects
     the `app` variable below as an ASGI app).
  2. Telegram sends every new message to POST /webhook.
  3. We hand the message text to your agent and send its reply
     back to Telegram.
"""

import os

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

from agents import Runner

from agent import agent

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@app.get("/")
async def health_check():
    """Visit your deployed URL in a browser to confirm it's alive."""
    return {"status": "ok", "agent": agent.name}


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

    if not message or "text" not in message:
        # Ignore anything that isn't a plain text message (stickers,
        # photos, edited messages, etc.) so Telegram doesn't retry it.
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user_text = message["text"]

    result = await Runner.run(agent, user_text)
    reply_text = result.final_output or "..."

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text},
        )

    return {"ok": True}
