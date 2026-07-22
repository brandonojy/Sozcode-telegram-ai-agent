"""
A local-only agent with real shell access.

This is NOT the Telegram bot's agent, and app.py never imports this
file -- the deployed bot has no shell access, full stop. Use this
for local development only: a terminal chat (local_agent_chat.py),
or a web UI you run on your own machine.

Deliberately self-contained -- its tools are defined here rather
than imported from agent.py, so editing your Telegram agent never
has any effect on this file, and vice versa.

Shell commands here execute for real, on this computer, with no
approval step (needs_approval=False on the ShellTool below) -- the
equivalent of you typing them into a terminal yourself. That's a
deliberate choice for local use, where you're the only one who can
trigger it. Never reuse this pattern for anything reachable by
other people without adding an approval step back in.
"""

import asyncio

from agents import (
    Agent,
    ShellCallOutcome,
    ShellCommandOutput,
    ShellCommandRequest,
    ShellResult,
    ShellTool,
    WebSearchTool,
    function_tool,
)


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


class LocalShellExecutor:
    """Actually runs shell commands on this machine. No sandboxing,
    no allowlist -- whatever the model asks for, this runs.
    """

    async def __call__(self, request: ShellCommandRequest) -> ShellResult:
        action = request.data.action
        outputs = []

        for cmd in action.commands:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            outputs.append(
                ShellCommandOutput(
                    command=cmd,
                    stdout=stdout.decode(errors="replace"),
                    stderr=stderr.decode(errors="replace"),
                    outcome=ShellCallOutcome(type="exit", exit_code=proc.returncode),
                )
            )

        return ShellResult(output=outputs, max_output_length=action.max_output_length)


shell_tool = ShellTool(
    executor=LocalShellExecutor(),
    needs_approval=False,  # auto-approve -- see the module docstring
)

local_agent = Agent(
    name="Local Shell Assistant",
    instructions="""
    You are a helpful local assistant with real shell access on this
    machine. Use the shell tool to inspect files, run scripts, check
    versions, and so on -- including precise computation (e.g. run
    `python3 -c "..."` through the shell rather than doing math
    yourself). You also have a few other tools: time, dice, reading
    webpages, stock data, and web search.

    Shell commands you run execute for real, immediately, with no
    confirmation step. Don't run destructive commands (deleting files,
    formatting anything, modifying system settings) unless the user
    explicitly and unambiguously asks for exactly that.
    """,
    tools=[
        get_current_time,
        roll_dice,
        read_dynamic_webpage,
        get_stock_fundamentals,
        shell_tool,
        WebSearchTool(),
    ],
    model="gpt-5.6",
)
