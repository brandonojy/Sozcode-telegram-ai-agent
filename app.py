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

If the agent generates a file (e.g. code_interpreter building a
spreadsheet), we download it from OpenAI and forward it to Telegram
as a document.

For learning purposes, we also stream the agent's tool calls (and
its reasoning, if the model supports it) to Telegram as separate
messages *while the agent is still working*, rather than batching
them into one message at the end. Set SHOW_AGENT_TRACE=false in
your environment variables to turn this off.
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


def _describe_tool_call(raw_item) -> str:
    """Best-effort human-readable description of a tool call.

    Custom @function_tool calls, and OpenAI's hosted tools (web
    search, code interpreter, ...), don't share the same shape --
    each is described using whatever fields it actually has, instead
    of falling back to a generic (and useless) "tool()".
    """
    raw_type = getattr(raw_item, "type", None)

    if raw_type == "function_call":
        return f"{raw_item.name}({raw_item.arguments})"

    if raw_type == "web_search_call":
        action = raw_item.action
        if action.type == "search":
            query = action.query or ", ".join(action.queries or [])
            return f'web_search("{query}")'
        if action.type == "open_page":
            return f"web_search.open_page({action.url})"
        if action.type == "find_in_page":
            return f'web_search.find("{action.pattern}" on {action.url})'
        return "web_search(...)"

    if raw_type == "code_interpreter_call":
        code = (raw_item.code or "").strip()
        if len(code) > 150:
            code = code[:150] + "..."
        return f"code_interpreter:\n{code}"

    # Fallback for any other hosted tool type (computer use, MCP, ...):
    # use whatever name/arguments we can find, or at least the raw type,
    # so we never show a bare, unhelpful "tool()".
    name = getattr(raw_item, "name", None) or raw_type or "tool"
    args = getattr(raw_item, "arguments", None)
    return f"{name}({args or ''})"


def _stream_event_to_message(event) -> str | None:
    """Turn one live streaming event into a Telegram message, or None to
    skip it. Called as the agent works, not after it's done -- this is
    what makes the trace show up as separate messages in real time.

    "Thinking" lines only appear if agent.py uses a reasoning-capable
    model with reasoning summaries turned on -- see the note in
    agent.py. Tool call lines appear for any model.
    """
    if event.type != "run_item_stream_event":
        return None

    if event.name == "tool_called":
        return f"🔧 {_describe_tool_call(event.item.raw_item)}"

    if event.name == "tool_output":
        preview = str(event.item.output)
        if len(preview) > 200:
            preview = preview[:200] + "..."
        return f"   -> {preview}"

    if event.name == "reasoning_item_created":
        summaries = [summary.text for summary in event.item.raw_item.summary]
        return "\n".join(f"🧠 {text}" for text in summaries) if summaries else None

    return None


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
            result = Runner.run_streamed(agent, [{"role": "user", "content": content}])

            # We always drain the full stream (the run doesn't actually
            # execute otherwise) -- SHOW_AGENT_TRACE just controls whether
            # we send what we see as separate Telegram messages while it
            # happens, or stay quiet until the final reply.
            async for event in result.stream_events():
                if not SHOW_AGENT_TRACE:
                    continue
                text = _stream_event_to_message(event)
                if text:
                    # Sent as plain text (no Markdown parsing) since tool
                    # output can contain characters that would otherwise
                    # break Telegram's formatting.
                    await client.post(
                        f"{TELEGRAM_API_URL}/sendMessage",
                        json={"chat_id": chat_id, "text": text},
                    )

            reply_text = result.final_output or "..."

        await client.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text},
        )

        if is_supported:
            for container_id, file_id, filename in _extract_generated_files(result.new_items):
                file_content = await openai_client.containers.files.content.retrieve(file_id, container_id=container_id)
                await _send_telegram_document(client, chat_id, filename, await file_content.aread())

    return {"ok": True}
