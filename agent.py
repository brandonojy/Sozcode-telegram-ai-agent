"""
==============================================================
 ✏️  THIS IS THE ONLY FILE YOU NEED TO EDIT FOR THE COURSE.
==============================================================

Customize your agent below:
  1. Give it tools (things it can DO, not just say)
  2. Write its instructions (its personality + rules)
  3. Optionally pick a specific model

Everything else in this project (app.py, local_chat.py, etc.)
is plumbing that connects your agent to Telegram. You don't
need to touch it, but you're welcome to look.
"""

from agents import Agent, CodeInterpreterTool, WebSearchTool, function_tool


# ---------------------------------------------------------------
# STEP 1: Give your agent tools (optional)
#
# There are two kinds of tools below:
#
# (a) Custom tools -- just a normal Python function with a
#     @function_tool decorator. The docstring and type hints
#     matter: the agent reads them to decide when and how to
#     call the function.
#
# (b) Built-in hosted tools -- pre-built by OpenAI, no code
#     required. You just add them to the `tools=` list below.
# ---------------------------------------------------------------

@function_tool
def get_current_time() -> str:
    """Return the current date and time."""
    from datetime import datetime

    return datetime.now().strftime("%A, %d %B %Y, %H:%M")


@function_tool
def roll_dice(sides: int = 6) -> str:
    """Roll a dice and return the result.

    Args:
        sides: How many sides the dice has.
    """
    import random

    return f"You rolled a {random.randint(1, sides)} (out of {sides})."


@function_tool
def read_dynamic_webpage(url: str) -> str:
    """Fetch a webpage's content after its JavaScript has run.

    Use this for sites that load their content dynamically (most
    modern web apps) -- a plain fetch would only see an empty page.

    Args:
        url: The full URL of the page to read.
    """
    import httpx

    resp = httpx.get(f"https://r.jina.ai/{url}", headers={"X-No-Cache": "true"}, timeout=20)
    return resp.text[:4000]


# Built-in hosted tools -- these run on OpenAI's side, no extra
# Python packages needed:
#
#   WebSearchTool()       -- search the live web
#   CodeInterpreterTool()  -- run real Python in a sandbox, e.g. to
#                             precisely analyze a spreadsheet someone
#                             sends. Works with the photo/document
#                             upload support already wired up in
#                             app.py -- no changes needed there.

hosted_tools = [
    WebSearchTool(),
    CodeInterpreterTool(tool_config={"type": "code_interpreter", "container": {"type": "auto"}}),
]


# ---------------------------------------------------------------
# STEP 2: Define your agent
#
# - name: shows up in logs, not shown to the user
# - instructions: this is your agent's personality + rulebook.
#   Be specific. Tell it who it is, how to behave, and anything
#   it should never do.
# - tools: the list of tools above that you want this agent to
#   be able to use.
# ---------------------------------------------------------------

agent = Agent(
    name="My Telegram Assistant",
    instructions="""
    You are a friendly, helpful assistant chatting with your creator
    over Telegram. Keep replies short and conversational -- this is
    a chat app, not an essay.

    Use your tools when they're actually useful. Don't mention that
    you "have tools"; just use them naturally.
    """,
    tools=[get_current_time, roll_dice, read_dynamic_webpage, *hosted_tools],
    # STEP 3 (optional): uncomment to pin a specific model.
    # If you leave this out, the SDK uses its default model.
    # model="gpt-4.1-mini",
)
