"""
Shared helpers for describing/running an agent turn, used by both
app.py (Telegram) and local_web.py (local web chat) so the same
formatting logic isn't duplicated between them.
"""

from agents import Runner


def describe_tool_call(raw_item) -> str:
    """Best-effort human-readable description of a tool call.

    Custom @function_tool calls, and OpenAI's hosted tools (web
    search, code interpreter, shell, ...), don't share the same
    shape -- each is described using whatever fields it actually
    has, instead of falling back to a generic (and useless) "tool()".
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

    if raw_type == "shell_call":
        commands = getattr(getattr(raw_item, "action", None), "commands", None) or []
        return f"shell: {' && '.join(commands)}"

    # Fallback for any other hosted tool type (computer use, MCP, ...):
    # use whatever name/arguments we can find, or at least the raw type,
    # so we never show a bare, unhelpful "tool()".
    name = getattr(raw_item, "name", None) or raw_type or "tool"
    args = getattr(raw_item, "arguments", None)
    return f"{name}({args or ''})"


def stream_event_to_message(event) -> str | None:
    """Turn one live streaming event into a readable trace line, or
    None to skip it.

    "Thinking" lines only appear for a reasoning-capable model with
    reasoning summaries turned on. Tool call lines appear for any
    model.
    """
    if event.type != "run_item_stream_event":
        return None

    if event.name == "tool_called":
        return f"🔧 {describe_tool_call(event.item.raw_item)}"

    if event.name == "tool_output":
        preview = str(event.item.output)
        if len(preview) > 200:
            preview = preview[:200] + "..."
        return f"   -> {preview}"

    if event.name == "reasoning_item_created":
        summaries = [summary.text for summary in event.item.raw_item.summary]
        return "\n".join(f"🧠 {text}" for text in summaries) if summaries else None

    return None


async def run_chat_turn(agent, message: str, history: list) -> dict:
    """Run one turn of a text chat against `agent`, returning the
    reply, a readable trace of what happened, and the updated
    history to send back on the next turn.
    """
    history = [*history, {"role": "user", "content": message}]
    result = Runner.run_streamed(agent, history, max_turns=10)

    trace = []
    async for event in result.stream_events():
        text = stream_event_to_message(event)
        if text:
            trace.append(text)

    return {
        "reply": result.final_output or "...",
        "trace": trace,
        "history": result.to_input_list(),
    }
