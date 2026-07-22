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

from agents import Agent, CodeInterpreterTool, ModelSettings, WebSearchTool, function_tool


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


@function_tool
def get_stock_fundamentals(ticker: str) -> str:
    """Get a stock's price and key fundamental metrics, as JSON.

    Pairs well with the code interpreter tool: fetch the numbers here,
    then have the agent build an actual spreadsheet or chart from them.

    Args:
        ticker: The stock's ticker symbol, e.g. 'NVDA', or 'D05.SI' for DBS on SGX.
    """
    import json

    import yfinance as yf

    info = yf.Ticker(ticker).info
    fundamentals = {
        "name": info.get("longName"),
        "ticker": ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "current_price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "return_on_equity": info.get("returnOnEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "gross_margins": info.get("grossMargins"),
        "operating_margins": info.get("operatingMargins"),
        "profit_margins": info.get("profitMargins"),
        "total_revenue": info.get("totalRevenue"),
        "net_income": info.get("netIncomeToCommon"),
        "trailing_eps": info.get("trailingEps"),
        "debt_to_equity": info.get("debtToEquity"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "dividend_yield": info.get("dividendYield"),
    }
    return json.dumps(fundamentals, indent=2)


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

    If asked for a "spreadsheet", "report", or similar over data (e.g.
    stock fundamentals), don't just describe the numbers in the chat --
    fetch the data with the relevant tool, then use code_interpreter to
    actually build a real .xlsx file (pandas/openpyxl) with the data
    organized into a clean table. Any file you create in code_interpreter
    is automatically sent to the user, so just build it and briefly say
    what's in it.

    If asked for a "slide", "slides", "presentation", or "deck", use
    code_interpreter's python-pptx library to build a real .pptx file.
    Keep it simple -- a handful of slides with a title and a few bullet
    points each is enough; don't attempt charts or images unless asked.

    If a tool call fails or doesn't give you what you needed, try a
    different approach at most once more. If it still doesn't work,
    stop and tell the user what went wrong instead of repeating the
    same call over and over.
    """,
    tools=[get_current_time, roll_dice, read_dynamic_webpage, get_stock_fundamentals, *hosted_tools],
    # STEP 3 (optional): pin a specific model.
    # If you leave this out, the SDK uses its default model.
    model="gpt-5.6-sol",
    #
    # Want to see the agent's "thinking" (not just its tool calls) in
    # Telegram? That only exists for reasoning models, and only if you
    # explicitly ask for a summary of it. Uncomment the line below to
    # turn it on -- reasoning models are slower and cost more per
    # message, so this is off by default.
    # model_settings=ModelSettings(reasoning={"summary": "auto"}),
)
