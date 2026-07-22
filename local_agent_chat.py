"""
Chat with the local shell-enabled agent in the terminal.

Unlike local_chat.py (which tests the same agent your Telegram bot
uses), this one has real shell access on this machine -- see the
warning in local_agent.py before running it.

Run it with:
    python local_agent_chat.py
"""

import asyncio

from agents import Runner

from local_agent import local_agent


async def main():
    print(f"Chatting with '{local_agent.name}'. Type 'quit' to exit.\n")
    print("Heads up: this agent can run real shell commands on this machine, with no confirmation step.\n")

    history = []
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"quit", "exit"}:
            break
        if not user_text:
            continue

        history.append({"role": "user", "content": user_text})
        result = await Runner.run(local_agent, history)
        print(f"{local_agent.name}: {result.final_output}\n")
        history = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())
