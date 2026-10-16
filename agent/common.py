import json

SYSTEM=(
    "You are a highly intelligent coding agent. Complete the task using the tools. Files live in /workspace. "
    "Always run your code to verify it's working. Program cannot read keyboard input(s) here, "
    "so pipe input in (e.g. echo '[2,3]' | python sum.py) "
    " If a command fails, read the error and fix it. "
    "when the task is done, reply with a short summary and no tool call."
)

def _tc_dict(tc):
    if hasattr(tc, "model_dump"):
        return tc.model_dump(exclude_none=True)
    return {"id": tc.id, "type": "function",
            "function":{"name" : tc.function.name, "arguments": tc.function.arguments}}

def _assistant_dict(msg):
    d = {"role":"assistant", "content": msg.content or ""}
    if msg.tool_calls:
        d["tool_calls"] = [_tc_dict(tc) for tc in msg.tool_calls]
    return d

MAX_CONTEXT_CHARS = 1500

def _size(messages):
    return sum(len(m.get("content") or "") + len(json.dumps(m.get("tool_calls", []))) for m in messages)

def compact(messages, budget=MAX_CONTEXT_CHARS, keep_last=4):
    """Shrink the oldest tool outputs until under budget. Returns how many were trimmed."""
    if _size(messages) <= budget:
        return 0
    tool_idx = [i for i, m in enumerate(messages) if m["role"] == "tool"]
    trimmed = 0
    for i in tool_idx[:-keep_last]:
        content = messages[i]["content"]
        if content.startswith("[trimmed"):
            continue
        first = (content.splitlines() or [""])[0][:80]
        messages[i]["content"] = f"[trimmed old output, {len(content)} chars. {first}]"
        trimmed += 1
        if _size(messages) <= budget:
            break
    return trimmed

