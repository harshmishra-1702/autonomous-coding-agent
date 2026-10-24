import json, os
from evals.report import load, summarize

EVENTS = [
    {"type": "task", "task": "t"},
    {"type": "tool", "step": 1, "tool": "write_file",
     "args": {"path": "a.py", "content": "x" * 100}, "result": "exit_code=0\nwrote a.py"},
    {"type": "tool", "step": 3, "tool": "run_command",
     "args": {"cmd": "python a.py"}, "result": "exit_code=1\nTraceback\nNameError: x"},
    {"type": "tool", "step": 4, "tool": "read_file", "args": {"path": "a.py", "line_end": 9},
     "result": "exit_code=0\n 1\tx\n\n[note: ignored unknown arguments ['line_end']]\n"
               "[NOTE: you already made this exact call with the same result. Try a different approach.]"},
    {"type": "abort", "reason": "step limit reached"},
]

def test_tool_lines_show_exit_code_and_error_tail():
    out = "\n".join(summarize(EVENTS))
    assert "write_file(path='a.py', content='" + "x" * 30 + "') -> exit_code=0" in out
    assert "run_command(cmd='python a.py') -> exit_code=1 | NameError: x" in out

def test_gap_between_steps_is_reported():
    assert "no tool logged for step 2" in "\n".join(summarize(EVENTS))

def test_repeat_and_ignored_args_are_flagged():
    out = "\n".join(summarize(EVENTS))
    assert "(repeat)" in out and "(ignored args)" in out

def test_summary_line_reports_outcome():
    assert summarize(EVENTS)[-1].startswith("summary: 3 tool calls")
    assert summarize(EVENTS)[-1].endswith("abort (step limit reached)")
    done = summarize([{"type": "done", "step": 2, "summary": "ok"}])
    assert done[-1].endswith("done at step 2")

def test_load_reads_newest_log_in_a_run_folder(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    old = logs / "run-1.jsonl"
    old.write_text(json.dumps({"type": "task", "task": "old"}) + "\n")
    os.utime(old, (1, 1))
    (logs / "run-2.jsonl").write_text(json.dumps({"type": "task", "task": "new"}) + "\n")
    assert load(str(tmp_path))[0]["task"] == "new"