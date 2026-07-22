"""
Shared helpers for describing/running an agent turn, used by both
app.py (Telegram) and local_web.py (local web chat) so the same
formatting logic isn't duplicated between them.
"""

from agents import Runner


def _field(raw_item, key, default=None):
    """Some hosted tool call raw_items are Pydantic-style objects
    (function_call, web_search_call, code_interpreter_call); others
    (shell_call, confirmed live) are plain dicts. getattr() silently
    returns the default for a dict instead of finding the key, so
    this checks both -- same pattern the SDK's own ToolCallItem.tool_name
    property uses internally.
    """
    if isinstance(raw_item, dict):
        return raw_item.get(key, default)
    return getattr(raw_item, key, default)


def describe_tool_call(raw_item) -> str:
    """Best-effort human-readable description of a tool call.

    Custom @function_tool calls, and OpenAI's hosted tools (web
    search, code interpreter, shell, ...), don't share the same
    shape -- each is described using whatever fields it actually
    has, instead of falling back to a generic (and useless) "tool()".
    """
    raw_type = _field(raw_item, "type")

    if raw_type == "function_call":
        return f"{_field(raw_item, 'name')}({_field(raw_item, 'arguments')})"

    if raw_type == "web_search_call":
        action = _field(raw_item, "action")
        action_type = _field(action, "type")
        if action_type == "search":
            query = _field(action, "query") or ", ".join(_field(action, "queries") or [])
            return f'web_search("{query}")'
        if action_type == "open_page":
            return f"web_search.open_page({_field(action, 'url')})"
        if action_type == "find_in_page":
            return f'web_search.find("{_field(action, "pattern")}" on {_field(action, "url")})'
        return "web_search(...)"

    if raw_type == "code_interpreter_call":
        code = (_field(raw_item, "code") or "").strip()
        if len(code) > 150:
            code = code[:150] + "..."
        return f"code_interpreter:\n{code}"

    if raw_type == "shell_call":
        action = _field(raw_item, "action")
        commands = _field(action, "commands") or []
        return f"shell: {' && '.join(commands)}"

    # Fallback for any other hosted tool type (computer use, MCP, ...):
    # use whatever name/arguments we can find, or at least the raw type,
    # so we never show a bare, unhelpful "tool()".
    name = _field(raw_item, "name") or raw_type or "tool"
    args = _field(raw_item, "arguments")
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
    reply, a readable trace of what happened, the updated history to
    send back on the next turn, and the raw new_items (for callers
    that want to do more with the run, e.g. extracting generated
    files -- new_items is NOT JSON-serializable, so pop it before
    returning an HTTP response if you don't need it).
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
        "new_items": result.new_items,
    }
