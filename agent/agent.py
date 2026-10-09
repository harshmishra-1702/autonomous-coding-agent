import json, os, sys, time
from agent.llm import chat_with_tools
from agent.sandbox import Sandbox
from agent.tools import Tools, TOOL_SCHEMAS
from groq import BadRequestError

SYSTEM=(
    "You are a highly intelligent coding agent. Complete the task using the tools. Files live in /workspace. "
    "Always run your code to verify it's working. Program cannot read keyboard input(s) here, "
    "so pipe input in (e.g. echo '[2,3]' | python sum.py) "
    " If a command fails, read the error and fix it. "
    "when the task is done, reply with a short summary and no tool call."
)

def _assistant_dict(msg):
    d = {"role":"assistant", "content": msg.content or ""}
    if msg.tool_calls:
        d["tool_calls"] = [{"id": tc.id, "type": "function",
                            "function":{"name": tc.function.name,
                                        "arguments": tc.function.arguments}}
                                        for tc in msg.tool_calls]
    return d

def run_agent(task, max_steps=10):
    messages = [{"role": "system","content":SYSTEM},
                {"role": "user","content":task}]

    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    def log(**event):
        with open(log_path, "a",encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    log(type="task", task=task)
    seen = {}

    with Sandbox() as sb:
        tools = Tools(sb)
        for step in range(1, max_steps+1):
            try:
                msg = chat_with_tools(messages, TOOL_SCHEMAS)
            except BadRequestError as e:
                if "tool_USE_failed" not in str(e):
                    raise
                messages.append({"role":"user","content":
                                "Your last tool call was invalid. Use the exact parameter names from the schema "
                                "(write_file needs 'path' and 'content')."})
                continue
            messages.append(_assistant_dict(msg))

            if not msg.tool_calls:
                log(type="done",step=step, summary=msg.content)
                print(f"\nDONE: {msg.content}\n(log: {log_path})")
                return msg.content

            for tc in msg.tool_calls:
                name, args = tc.function.name,{}
                try:
                    args = json.loads(tc.function.arguments)
                    print(f"\n[{step}] {name}({args})")
                    result = tools.call(name, args)
                except json.JSONDecodeError:
                    result = "error: arguments were not valid JSON"

                sig = (name, json.dumps(args, sort_keys=True),result)
                seen[sig] = seen.get(sig, 0)+1
                if seen[sig] == 2:
                    result += "\n[NOTE: you already made this exact call with the same result. Try a different approach.]"
                elif seen[sig] >= 3:
                    log(type="abort", step=step, reason="repeating with no progress")
                    print("\nStopped: agent is repeating itself")
                    return
                print(result[:500])
                log(type="tool", step=step, tool=name, args=args, result=result)
                messages.append({"role":"tool","tool_call_id": tc.id,"content":result})

    log(type="abort", reason="step limit reached")
    print("\nStopped: step limit reached")

if __name__== "__main__":
    task = " ".join(sys.argv[1:]) or "Create fizzbuzz.py that prints FizzBuzz for 1 to 15, then run it."
    run_agent(task)
