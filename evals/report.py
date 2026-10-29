import glob, json, os, sys
from collections import Counter

def load(path):
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "logs", "*.jsonl")) or glob.glob(os.path.join(path, "*.jsonl"))
        path = max(files, key=os.path.getmtime)
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def _short(v, n=30):
    return repr(str(v)[:n])

def summarize(events):
    lines, tools, flags = [], Counter(), Counter()
    last, outcome = 0, "no outcome logged"
    for e in events:
        kind = e["type"]
        if kind == "tool":
            step = e["step"]
            if step > last + 1:
                gap = f"{last + 1}" if step == last + 2 else f"{last + 1}-{step - 1}"
                lines.append(f"    -- no tool logged for step {gap}")
            last = max(last, step)
            res = e["result"]
            rows = [r for r in res.splitlines() if r.strip()]
            note = ""
            if "[NOTE: you already made this exact call" in res:
                note += " (repeat)"
                flags["repeat"] += 1
            if "[note: ignored unknown arguments" in res:
                note += " (ignored args)"
                flags["ignored args"] += 1
            show_tail = len(rows) > 1 and (e["tool"] == "run_command" or rows[0] != "exit_code=0")
            tail = f" | {rows[-1][:60]}" if show_tail else ""
            args = ", ".join(f"{k}={_short(v)}" for k, v in e["args"].items())
            lines.append(f"{step:>3} {e['tool']}({args}) -> {rows[0] if rows else ''}{tail}{note}")
            tools[e["tool"]] += 1
        elif kind == "compact":
            lines.append(f"{e['step']:>3} -- compacted {e['trimmed']} old outputs")
        elif kind == "done":
            last = max(last, e["step"])
            outcome = f"done at step {e['step']}"
            text = " ".join(str(e.get("summary")).split())[:80]
            lines.append(f"{e['step']:>3} -- done: {text}")
        elif kind == "abort":
            outcome = f"abort ({e.get('reason')})"
            lines.append(f"    -- abort: {e.get('reason')}")
    calls = ", ".join(f"{n} x{c}" for n, c in tools.most_common())
    extra = "".join(f" | {k}: {c}" for k, c in flags.items())
    lines.append(f"summary: {sum(tools.values())} tool calls ({calls}){extra} | {outcome}")
    return lines

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    for line in summarize(load(target)):
        print(line)