"""
Chat with your agent in the terminal -- no Telegram or deployment
required. Great for testing changes to agent.py quickly.

Run it with:
    python local_chat.py
"""

import asyncio

from agents import Runner

from agent import agent


async def main():
    print(f"Chatting with '{agent.name}'. Type 'quit' to exit.\n")

    history = []
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"quit", "exit"}:
            break
        if not user_text:
            continue

        history.append({"role": "user", "content": user_text})
        result = await Runner.run(agent, history)
        print(f"{agent.name}: {result.final_output}\n")
        history = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())
