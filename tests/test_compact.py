from agent.common import compact, _size

def make(n, size=3000):
    msgs = [{"role": "system", "content":"s"},{"role": "user","content":"task"}]
    for i in range (n):
        msgs.append({"role": "assistant","content":"","tool_calls": [
            {"id": f"c{i}","type":"functions", "function":{"name":"run_command", "arguments": "{}"}}]})
        msgs.append({"role": "tool", "tool_call_id": f"c{i}", "content": "exit_code=1\n" + "x" * size})
    return msgs

def test_small_history_untouched():
    msgs = make(2,100)
    before = [m.copy() for m in msgs]
    assert compact(msgs) == 0 and msgs == before

def test_old_trimmed_recent_kept():
    msgs = make(10)
    assert compact(msgs, budget=24000, keep_last=4) >0
    tools = [m for m in msgs if m["role"] == "tool"]
    assert _size(msgs) <= 24000
    assert tools[0]["content"].startswith("[trimmed")
    assert "exit_code=1" in tools[0]["content"]
    assert not any(t["content"].startswith("[trimmed") for t in tools[-4:])


def test_every_tool_call_keep_its_result():
    msgs = make(10)
    compact(msgs)
    calls = [tc["id"] for m in msgs if m.get("tool_calls") for tc in m["tool_calls"]]
    results = [m["tool_call_id"] for m in msgs if m["role"] == "tool"]
    assert calls == results

