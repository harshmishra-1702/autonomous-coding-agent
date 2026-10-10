import json
from types import SimpleNamespace as NS
import agent.agent as ag

def reply(content=None, calls=()):
    tcs = [NS(id=f"c{i}", function=NS(name=n, arguments=a)) for i, (n,a) in enumerate(calls)]
    return NS(content =content, tool_calls=tcs or None)

def test_finishes_when_brain_answers_in_words(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ag, "chat_with_tools", lambda m, t: reply("all done"))
    assert ag.run_agent("task") == "all done"

def test_executes_tool_then_finishes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    script = iter([reply(calls=[("write_file", json.dumps({"path": "x.txt", "content": "hi"}))]),
                   reply("done")])
    monkeypatch.setattr(ag, "chat_with_tools", lambda m,t: next(script))
    assert ag.run_agent("task")=="done"
    assert (tmp_path / "workspace" / "x.txt").read_text() == "hi"

def test_repeated_identical_call_aborts_after_three(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls =[]
    def fake(m,t):
        calls.append(1)
        return reply(calls=[("run_command", '{"cmd": "cat nope.txt"}')])
    monkeypatch.setattr(ag, "chat_with_tools", fake)
    assert ag.run_agent("task", max_steps=10) is None
    assert len(calls) == 3
    log = next((tmp_path / "logs").glob("*.jsonl")).read_text()
    assert '"abort"' in log