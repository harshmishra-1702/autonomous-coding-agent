import docker
from agent.sandbox import Sandbox

def test_exec_returns_output(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        assert sb.exec("echo hi") == (0,"hi\n")

def test_timeout_kills_command(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        assert sb.exec("sleep 5", timeout=1)[0] == 124

def test_network_disabled_by_default(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        code, _ = sb.exec("python -c \"import urlib.request s u; u.urlopen('http://example.com' , timeout=3)\"")
        assert code != 0

def test_workspace_is_shared_with_host(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        sb.exec("echo data > f.txt")
    assert (tmp_path / "f.txt").read_text().strip() == "data"

def test_container_removed_after_exit(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        cid = sb.container.id
    assert cid not in [c.id for c in docker.from_env().containers.list(all=True)]