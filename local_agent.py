"""
A local-only agent with real shell access.

This is NOT the Telegram bot's agent, and app.py never imports this
file -- the deployed bot has no shell access, full stop. Use this
for local development only: a terminal chat (local_agent_chat.py),
or a web UI you run on your own machine.

Shell commands here execute for real, on this computer, with no
approval step (needs_approval=False on the ShellTool below) -- the
equivalent of you typing them into a terminal yourself. That's a
deliberate choice for local use, where you're the only one who can
trigger it. Never reuse this pattern for anything reachable by
other people without adding an approval step back in.
"""

import asyncio

from agents import Agent, ShellCallOutcome, ShellCommandOutput, ShellCommandRequest, ShellResult, ShellTool

from agent import get_current_time, get_stock_fundamentals, hosted_tools, read_dynamic_webpage, roll_dice


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
    versions, and so on. You also have the same tools as the Telegram
    bot: time, dice, reading webpages, stock data, web search, and
    code interpreter.

    Shell commands you run execute for real, immediately, with no
    confirmation step. Don't run destructive commands (deleting files,
    formatting anything, modifying system settings) unless the user
    explicitly and unambiguously asks for exactly that.
    """,
    tools=[get_current_time, roll_dice, read_dynamic_webpage, get_stock_fundamentals, shell_tool, *hosted_tools],
    model="gpt-5.6",
)
