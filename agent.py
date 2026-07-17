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

from agents import Agent, function_tool


# ---------------------------------------------------------------
# STEP 1: Give your agent tools (optional)
#
# A tool is just a normal Python function with a @function_tool
# decorator on it. The docstring and type hints matter -- the
# agent reads them to decide when and how to call the function.
#
# Add as many of these as you like, then list them in `tools=`
# below.
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


# ---------------------------------------------------------------
# STEP 2: Define your agent
#
# - name: shows up in logs, not shown to the user
# - instructions: this is your agent's personality + rulebook.
#   Be specific. Tell it who it is, how to behave, and anything
#   it should never do.
# - tools: the list of @function_tool functions above that you
#   want this agent to be able to use.
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
    tools=[get_current_time, roll_dice],
    # STEP 3 (optional): uncomment to pin a specific model.
    # If you leave this out, the SDK uses its default model.
    # model="gpt-4.1-mini",
)
