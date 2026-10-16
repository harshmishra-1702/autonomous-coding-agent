import json
from types import SimpleNamespace as NS
import agent.graph as gr

def reply(content=None, calls=()):
    tcs = [NS(id=f"c{i}", function=NS(name=n, arguments=a)) for i, (n, a) in enumerate(calls)]
    return NS(content=content, tool_calls=tcs or None)

def test_finishes_when_brain_answers_in_words(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gr, "chat_with_tools", lambda m, t: reply("all done"))
    assert gr.run_agent_graph("task") == "all done"

def test_executes_tool_then_finishes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    script = iter([reply(calls=[("write_file", json.dumps({"path": "x.txt", "content": "hi"}))]),
                   reply("done")])
    monkeypatch.setattr(gr, "chat_with_tools", lambda m, t: next(script))
    assert gr.run_agent_graph("task") == "done"
    assert (tmp_path / "workspace" / "x.txt").read_text() == "hi"

def test_repeated_identical_call_aborts_after_three(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    def fake(m, t):
        calls.append(1)
        return reply(calls=[("run_command", '{"cmd": "cat nope.txt"}')])
    monkeypatch.setattr(gr, "chat_with_tools", fake)
    assert gr.run_agent_graph("task", max_steps=10) is None
    assert len(calls) == 3
    assert '"abort"' in next((tmp_path / "logs").glob("*.jsonl")).read_text()

def test_step_limit_stops_the_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    def fake(m, t):
        calls.append(1)
        return reply(calls=[("run_command", json.dumps({"cmd": f"echo {len(calls)}"}))])
    monkeypatch.setattr(gr, "chat_with_tools", fake)
    assert gr.run_agent_graph("task", max_steps=3) is None
    assert len(calls) == 3

def test_graph_has_agent_and_tools_nodes():
    app = gr.build_graph(None, lambda **e: None, 10)
    diagram = app.get_graph().draw_mermaid()
    assert "agent" in diagram and "tools" in diagram