import base64
import shlex
import inspect
from agent.sandbox import Sandbox

MAX_OUT =4000

def _trunc(s):
    if len(s) <= MAX_OUT:
        return s 
    h = MAX_OUT //2
    return s[:h] + f"\n...[{len(s)-MAX_OUT} chars truncated]...\n" + s[-h:]


EDIT_PY = """
import sys, base64
path = sys.argv[1]
old = base64.b64decode(sys.argv[2]).decode()
new = base64.b64decode(sys.argv[3]).decode()
text = open(path, encoding='utf-8').read()
if not old:
    sys.exit('error: old text is empty')
n = text.count(old)
if n == 0:
    sys.exit('error: old text not found. Re-read the file and copy it exactly.')
if n > 1:
    sys.exit(f'error: old text matches {n} places. Include more surrounding lines to make it unique.')
open(path, 'w', encoding='utf-8').write(text.replace(old, new))
print('edited', path)
"""

class Tools:
    """Agent-Computer Interface: every tool runs inside the sandbox(FR-3,4)"""

    def __init__(self,sandbox):
        self.sb=sandbox

    def run_command(self,cmd,timeout=30):
        if isinstance(cmd, list):
            cmd=shlex.join(cmd)
        timeout = max(1, min(int(timeout), 120))
        code, out = self.sb.exec(cmd, timeout)
        return _trunc(f"exit_code={code}\n{out}")

    def edit_file(self, path, old , new):
        enc = lambda s: base64.b64encode(s.encode()).decode()
        return self.run_command(
            f"python -c {shlex.quote(EDIT_PY)} {shlex.quote(path)} {enc(old)} {enc(new)}")

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
        fn = getattr(self, name)
        allowed = inspect.signature(fn).parameters
        extra = sorted(set(args) - set(allowed))
        try:
            out = fn(**{k: v for k, v in args.items() if k in allowed})
        except Exception as e:
            return f"error: {e}"
        return out + (f"\n[note: ignored unknown arguments {extra}]" if extra else "")

def _schema(name, desc, props, required):
    params = {"type": "object", "properties": props}
    if required:                     
        params["required"] = required
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": params}}

def P(desc, t="string"):
    return {"type": t, "description": desc}

PATH = P("File path, relative to /workspace")

TOOL_SCHEMAS = [
    _schema("run_command", "Run a shell command in the sandbox (cwd /workspace). Returns exit code and output.",
            {"cmd": P("Shell command to run"), "timeout": P("Seconds before kill (max 120), default 30", "integer")}, ["cmd"]),
    _schema("read_file", "Read a file, with line numbers.", {"path": PATH}, ["path"]),
    _schema("write_file", "Create or overwrite a file.",
            {"path": PATH, "content": P("Full text to write to the file")}, ["path", "content"]),
    _schema("list_dir", "List files in a directory.", {"path": PATH}, []),
    _schema("delete_file", "Delete a single file.", {"path": PATH}, ["path"]),
    _schema("edit_file", "Replace one exact piece of text in an existing file. 'old' must match exactly once. Prefer this over write_file for small changes.",
        {"path": PATH, "old": P("Exact existing text to replace (must be unique in the file)"),
        "new": P("Replacement text")}, ["path", "old", "new"]),
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
    