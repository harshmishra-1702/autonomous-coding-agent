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
        if isinstance(cmd, list):
            cmd=shlex.join(cmd)
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

    def call(self, name, args):
        if name not in {s["function"]["name"] for s in TOOL_SCHEMAS}:
            return f"error: unknown tool {name}"
        try:
            return getattr(self, name)(**args)
        except Exception as e:
            return f"error: {e}"

def _schema(name, desc, props, required):
    return {
        "type":"function", "function": {"name" : name, "description" : desc,
        "parameters": {"type" : "object", "prperties" : props, "required" : required}}}

def P(desc, t="string"):
    return {"type": t, "description": desc}

PATH = P("File path, relative to /workspace")

TOOL_SCHEMAS = [
    _schema("run_command", "Run a shell command in the sandbox (cwd /workspace). Returns exit code and output.",
            {"cmd": P("Shell command to run"), "timeout": P("Seconds before kill, default 30", "integer")}, ["cmd"]),
    _schema("read_file", "Read a file, with line numbers.", {"path": PATH}, ["path"]),
    _schema("write_file", "Create or overwrite a file.",
            {"path": PATH, "content": P("Full text to write to the file")}, ["path", "content"]),
    _schema("list_dir", "List files in a directory.", {"path": PATH}, []),
    _schema("delete_file", "Delete a single file.", {"path": PATH}, ["path"]),
]

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
    