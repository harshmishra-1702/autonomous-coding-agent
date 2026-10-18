import os
import time
import docker

LABEL = "coding-agent-sandbox"
STALE_AFTER = 3600

class Sandbox:
    def __init__(self, image="python:3.11-slim", workspace="workspace",
                 mem="512m", network=False):
        self.client = docker.from_env()
        self.image, self.mem, self.network = image, mem, network
        self.workspace = os.path.abspath(workspace)
        os.makedirs(self.workspace, exist_ok=True)
        self.container = None

    def _cleanup_stale(self):
        for c in self.client.containers.list(all=True, filters={"label": LABEL}):
            if time.time() - float(c.labels.get(LABEL, 0)) > STALE_AFTER:
                try:
                    c.remove(force=True)
                except docker.errors.NotFound:
                    pass

    def start(self):
        self._cleanup_stale()
        self.container = self.client.containers.run(
            self.image, command="sleep infinity", detach=True,
            volumes={self.workspace: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace", mem_limit=self.mem,
            nano_cpus=1_000_000_000,
            network_disabled=not self.network,
            labels={LABEL: str(int(time.time()))},
            pids_limit=128,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"])

    def exec(self, cmd, timeout=30):
        r = self.container.exec_run(["timeout", str(timeout), "bash", "-c", cmd])
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