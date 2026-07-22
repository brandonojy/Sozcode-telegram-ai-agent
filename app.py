"""
Telegram <-> OpenAI Agents SDK bridge.

This is infrastructure code -- you do NOT need to edit this file
for the course. Your agent lives in agent.py.

What this does, in two steps:
  1. POST /webhook -- Telegram calls this for every new message. It
     does the minimum possible work (parse the message, upload any
     photo/document to OpenAI) and immediately hands off to /process,
     then tells Telegram "got it" (HTTP 200) without waiting for the
     agent to actually run.
  2. POST /process -- does the real work: runs the agent (streaming
     tool-call/reasoning trace messages to Telegram as it goes, for
     learning purposes -- set SHOW_AGENT_TRACE=false to turn that
     off), sends the final reply, and forwards any file the agent
     generated (e.g. code_interpreter building a spreadsheet).

Why split it this way: Telegram gives up waiting on a slow webhook
and retries the *entire* message -- independently of whether we
eventually would have answered correctly. A model working through a
few tool calls can easily take longer than Telegram's patience, so
the only reliable fix is to never make Telegram wait on the agent at
all. /webhook responds in well under a second every time, regardless
of how long the agent takes; /process is free to take as long as it
needs (up to vercel.json's maxDuration), because nothing is waiting
on it. AGENT_TIMEOUT_SECONDS is a separate, unrelated safety net --
it bounds worst-case OpenAI API spend if a run gets stuck, not
Telegram's patience.

/process is triggered by a plain HTTPS call from /webhook to this
same deployment (using Vercel's automatic VERCEL_URL) -- not a
background task tacked onto /webhook's own execution. Vercel doesn't
kill a function just because whoever called it stopped listening
(that's opt-in via "supportsCancellation" in vercel.json, which we
don't set), so /process keeps running to completion independently.
"""

import asyncio
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI

from agents import Runner

from admin import ADMIN_PAGE_HTML
from agent import agent
from chat_ui import render_chat_page
from trace_utils import run_chat_turn, stream_event_to_message

# Only affects local runs -- Vercel injects real environment variables
# directly, and load_dotenv() is a no-op if there's no .env file (as
# there won't be on Vercel, since .env is gitignored and never
# deployed).
load_dotenv()

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"
SHOW_AGENT_TRACE = os.environ.get("SHOW_AGENT_TRACE", "true").lower() != "false"
AGENT_TIMEOUT_SECONDS = 270  # keep under vercel.json's maxDuration (300s)

openai_client = AsyncOpenAI()


def _process_url() -> str:
    """This deployment's own URL, for /webhook to call /process on.

    VERCEL_URL is set automatically by Vercel at runtime. If it's
    somehow unavailable, set APP_URL yourself as a fallback (same
    format: your-project.vercel.app, no https://).
    """
    base = os.environ.get("APP_URL") or os.environ.get("VERCEL_URL")
    if not base:
        raise RuntimeError(
            "Can't determine this app's own URL to call /process. Enable "
            "'System Environment Variables' in your Vercel project's "
            "Environment Variables settings (provides VERCEL_URL "
            "automatically), or set an APP_URL environment variable "
            "yourself."
        )
    base = base.removeprefix("https://").removeprefix("http://")
    return f"https://{base}/process"


@app.get("/")
async def health_check():
    """Visit your deployed URL in a browser to confirm it's alive."""
    return {"status": "ok", "agent": agent.name}


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """A browser-based helper for registering/checking/stopping your
    Telegram webhook -- see your-deployed-url.vercel.app/setup.
    """
    return ADMIN_PAGE_HTML


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """A simple web chat UI talking to the exact same agent as your
    Telegram bot. Safe to deploy alongside Telegram -- no shell
    access, same agent either way.
    """
    return render_chat_page(
        title="Web Chat",
        subtitle="Talking to the same agent as your Telegram bot.",
        badge="🌐 Web",
        badge_color="#2563eb",
    )


@app.post("/chat")
async def chat_send(request: Request):
    """Handles one message from the /chat page above. Runs
    synchronously (unlike /webhook) -- a browser tab just waits for
    the response, it doesn't retry on its own the way Telegram does,
    so there's no need for the /webhook+/process split here.
    """
    body = await request.json()
    return await run_chat_turn(agent, body["message"], body.get("history", []))


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


def _extract_generated_files(new_items: list) -> list[tuple[str, str, str]]:
    """Find files the agent generated (e.g. a spreadsheet built with
    code_interpreter) so we can download and forward them.

    When code_interpreter creates a file, the model's reply text
    carries a "container_file_citation" annotation pointing at it --
    that's a more reliable signal than listing everything in the
    sandbox, which would also include any input files we uploaded.
    """
    files = []
    for item in new_items:
        if item.type != "message_output_item":
            continue
        for content in item.raw_item.content:
            for annotation in getattr(content, "annotations", None) or []:
                if getattr(annotation, "type", None) == "container_file_citation":
                    files.append((annotation.container_id, annotation.file_id, annotation.filename))
    return files


async def _send_telegram_document(client: httpx.AsyncClient, chat_id: int, filename: str, file_bytes: bytes) -> None:
    await client.post(
        f"{TELEGRAM_API_URL}/sendDocument",
        data={"chat_id": chat_id},
        files={"document": (filename, file_bytes)},
    )


async def _run_agent(client: httpx.AsyncClient, chat_id: int, content: list[dict]) -> tuple[str, list]:
    """Run the agent, streaming trace messages to Telegram as it works.

    Returns (reply_text, new_items). max_turns=10 (the SDK's own
    default) is just a cost/sanity cap now, not a race against
    Telegram's patience -- see the module docstring.
    """
    result = Runner.run_streamed(agent, [{"role": "user", "content": content}], max_turns=10)

    async for event in result.stream_events():
        if not SHOW_AGENT_TRACE:
            continue
        text = stream_event_to_message(event)
        if text:
            # Sent as plain text (no Markdown parsing) since tool output
            # can contain characters that would otherwise break
            # Telegram's formatting.
            await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )

    return result.final_output or "...", result.new_items


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
            await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "I can only read text, photos, and documents (like PDFs) right now -- try sending one of those!",
                },
            )
            return {"ok": True}

        # Uploading photos/documents to OpenAI happens here, before we
        # hand off -- it's fast (seconds, not minutes), unlike the
        # agent run itself.
        content = await _build_input_content(client, message)

        # Hand off to /process and return to Telegram right away. We
        # don't wait for /process to finish (that's the whole point) --
        # just long enough to be confident the request actually got
        # sent. The read timeout firing is expected, not an error.
        try:
            await client.post(
                _process_url(),
                json={"chat_id": chat_id, "content": content},
                headers={"X-Internal-Secret": TELEGRAM_WEBHOOK_SECRET or ""},
                timeout=httpx.Timeout(connect=5.0, read=3.0, write=5.0, pool=5.0),
            )
        except httpx.TimeoutException:
            pass

    return {"ok": True}


@app.post("/process")
async def process_message(
    request: Request,
    x_internal_secret: str | None = Header(default=None),
):
    """Does the actual agent work. Only callable by /webhook (on this
    same deployment) -- not part of the public API surface.
    """
    if TELEGRAM_WEBHOOK_SECRET and x_internal_secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal secret")

    body = await request.json()
    chat_id = body["chat_id"]
    content = body["content"]

    async with httpx.AsyncClient() as client:
        new_items = []
        try:
            reply_text, new_items = await asyncio.wait_for(
                _run_agent(client, chat_id, content),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            # A safety net against unbounded OpenAI API spend, not
            # against Telegram retries -- those are already handled by
            # /webhook responding immediately, before this ever runs.
            reply_text = "Sorry, that took too long and I had to stop. Try a smaller or more specific request."

        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text},
        )

        for container_id, file_id, filename in _extract_generated_files(new_items):
            file_content = await openai_client.containers.files.content.retrieve(file_id, container_id=container_id)
            await _send_telegram_document(client, chat_id, filename, await file_content.aread())

    return {"ok": True}
