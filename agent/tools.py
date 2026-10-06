import base64
import shlex
from agent.sandbox import Sandbox

MAX_OUT =4000

def _trunc(s):
    if len(s) <= MAX_OUT:
        return s 
    h = MAX_OUT //2
    return s[:h] + f"\n...[{len(s)-MAX_OUT} chars truncated]...\n" + s[-h:]

class Tools:
    """Agent-Computer Interface: every tool runs inside the sandbox(FR-3,4)"""

    def __init__(self,sandbox):
        self.sb=sandbox

    def run_command(self,cmd,timeout=30):
        code, out = self.sb.exec(cmd, timeout)
        return _trunc(f"exit_code={code}\n{out}")

    def read_file(self, path):
        return self.run_command(f"cat -n {shlex.quote(path)}")

    def write_file(self, path, content):
        b64 = base64.b64encode(content.encode()).decode()
        p = shlex.quote(path)
        return self.run_command(
            f"mkdir -p $(dirname {p}) && echo {b64} | base64 -d > {p} && echo 'wrote {path}'"
        )

    def list_dir(self, path="."):
        return self.run_command(f"ls -la {shlex.quote(path)}")

    def delete_file(self, path):
        return self.run_command(
            f"rm -- {shlex.quote(path)} && echo {shlex.quote('deleted '+ path)}"
        )


if __name__=="__main__":
    with Sandbox() as sb:
        t= Tools(sb)
        print(t.write_file("hello.py", "print('hi')\nprint(2+3)"))
        print(t.run_command("python hello.py"))
        print(t.read_file("hello.py"))
        print(t.list_dir())
        print(t.read_file("missing.txt"))
        print(t.delete_file("hello.py"))
        print(t.list_dir())
        print(t.delete_file("hello.py"))
        print(t.delete_file("t.py"))
    