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

