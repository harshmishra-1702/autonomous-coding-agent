import os
import docker

class Sandbox:
    """Ephemeral Docker container for running agent-generated code."""

    def __init__(self,image ="python:3.11-slim", workspace="workspace",mem="512m", network=False):
        self.client = docker.from_env()
        self.image, self.mem, self.network = image, mem, network
        self.workspace = os.path.abspath(workspace)
        os.makedirs(self.workspace, exist_ok=True)
        self.container = None

    def start(self):
        self.container = self.client.containers.run(
            self.image, command="sleep infinity", detach=True,
            volumes={self.workspace : {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace", mem_limit=self.mem,
            nano_cpus=1_000_000_000,
            network_disabled=not self.network
        )

    def exec(self, cmd, timeout=30):
        """Run a shell command in the container. Returns (exit_code, output)."""
        r = self.container.exec_run(["timeout",str(timeout), "bash","-c",cmd])
        return r.exit_code, r.output.decode(errors="replace")

    def stop(self):
        if self.container:
            self.container.remove(force=True)
            self.container = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

if __name__=="__main__":
    with Sandbox() as sb:
        print(sb.exec("python -c \"print('hi from sandbox')\""))
        print(sb.exec("echo 'print(2+2)' > t.py && python t.py"))
        print(sb.exec("sleep 5", timeout=2))

