import docker, time
from agent.sandbox import Sandbox

LABEL = "coding-agent-sandbox"  

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


def test_all_capabilities_dropped(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        out = sb.exec("grep CapEff /proc/self/status")[1]
        assert out.split()[-1] == "0000000000000000"

def test_no_new_privileges(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        out = sb.exec("grep NoNewPrivs /proc/self/status")[1]
        assert out.split()[-1] == "1"

def test_process_limit_is_set(tmp_path):
    with Sandbox(workspace=str(tmp_path)) as sb:
        sb.container.reload()
        assert sb.container.attrs["HostConfig"]["PidsLimit"] == 128

def test_start_removes_stale_labeled_containers(tmp_path):
    c = docker.from_env()
    stale = c.containers.run("python:3.11-slim", "sleep infinity", detach=True,
                             labels={LABEL: str(int(time.time()) - 7200)})  
    fresh = c.containers.run("python:3.11-slim", "sleep infinity", detach=True,
                             labels={LABEL: str(int(time.time()))})
    try:
        with Sandbox(workspace=str(tmp_path)):
            ids = [x.id for x in c.containers.list(all=True)]
            assert stale.id not in ids       
            assert fresh.id in ids           
    finally:
        fresh.remove(force=True)
        try:
            stale.remove(force=True)
        except docker.errors.NotFound:
            pass

