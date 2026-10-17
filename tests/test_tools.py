import pytest
from agent.sandbox import Sandbox
from agent.tools import Tools, _trunc, MAX_OUT

@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    with Sandbox(workspace=str(tmp_path_factory.mktemp("ws"))) as sb:
        yield Tools(sb)

def test_write_then_read(tools):
    tools.write_file("sub/a.py" , "print('hi')")
    assert "print('hi')" in tools.read_file("sub/a.py")

def test_exit_codes(tools):
    assert "exit_code=0" in tools.run_command("true")
    assert "exit_code=1" in tools.run_command("false")

def test_timeout(tools):
    assert "exit_code=124" in tools.run_command("sleep 5", timeout=1)

def test_list_command_is_accepted(tools):
    assert "hello" in tools.run_command(["echo", "hello"])

def test_delete_files(tools):
    tools.write_file("del.txt", "x")
    assert "deleted" in tools.delete_file("del.txt")
    assert "exit_code=1" in tools.delete_file("del.txt")

def test_read_missing_file(tools):
    assert "exit_code=1" in tools.read_file("nope.txt")

def test_unknown_tool_returns_error_text(tools):
    assert tools.call("hack", {}).startswith("error")

def test_invented_arguments_are_ignored(tools):
    assert "ignored unknown arguments" in tools.call("list_dir", {"path": ".","recursive":True})

def test_truncation_keeps_head_and_tail():
    out = _trunc("A" * MAX_OUT + "B" * MAX_OUT)
    assert "truncated" in out and out.startswith("A") and out.endswith("B")

def test_edit_file_replaces_unique_text(tools):
    tools.write_file("e.py", "a = 1\nb = 2\n")
    assert "exit_code=0" in tools.edit_file("e.py", "b = 2", "b = 3")
    out = tools.read_file("e.py")
    assert "b = 3" in out and "a = 1" in out

def test_edit_file_rejects_missing_text(tools):
    tools.write_file("e2.py", "x = 1\n")
    out = tools.edit_file("e2.py", "zzz", "y")
    assert "exit_code=1" in out and "not found" in out

def test_edit_file_rejects_ambiguous_match(tools):
    tools.write_file("e3.py", "x = 1\nx = 1\n")
    out = tools.edit_file("e3.py", "x = 1", "x = 2")
    assert "exit_code=1" in out and "2 places" in out
    assert "x = 2" not in tools.read_file("e3.py")      # file left untouched

def test_edit_file_handles_quotes_and_newlines(tools):
    tools.write_file("e4.py", "print('hi')\nprint(\"yo\")\n")
    tools.edit_file("e4.py", "print('hi')\nprint(\"yo\")", "print(\"both\")")
    assert 'print("both")' in tools.read_file("e4.py")

