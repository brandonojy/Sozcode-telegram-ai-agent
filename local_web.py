"""
A local-only web chat for local_agent (the shell-enabled agent).

This is a completely separate FastAPI app from app.py -- it is
never deployed to Vercel (nothing in vercel.json references this
file, and its name doesn't match any Vercel Python entrypoint
pattern). Run it yourself, locally:

    uvicorn local_web:app --port 8001 --reload

Then open http://127.0.0.1:8001/chat in your browser.

Same warning as local_agent.py: the shell tool here has no approval
step. Only run this where you're the only one who can reach it
(i.e. on your own machine, not exposed to the network).
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from chat_ui import render_chat_page
from local_agent import local_agent
from trace_utils import run_chat_turn

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
    return "<p>This is the local shell agent's server. Go to <a href='/chat'>/chat</a>.</p>"


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return render_chat_page(
        title="Local Shell Chat",
        subtitle="Real shell access on this machine -- no confirmation step. Local only.",
        badge="⚠️ Local + Shell",
        badge_color="#dc2626",
    )


@app.post("/chat")
async def chat_send(request: Request):
    body = await request.json()
    return await run_chat_turn(local_agent, body["message"], body.get("history", []))
