import json
from agent.llm import chat_with_tools
from agent.sandbox import Sandbox
from agent.tools import Tools, TOOL_SCHEMAS

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

    with Sandbox() as sb:
        tools = Tools(sb)
        for step in range(1, max_steps+1):
            msg = chat_with_tools(messages, TOOL_SCHEMAS)
            messages.append(_assistant_dict(msg))

            if not msg.tool_calls:
                print(f"\nDONE: {msg.content}")
                return msg.content

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                    print(f"\n[{step}] {name}({args})")
                    result = tools.call(name, args)
                except json.JSONDecodeError:
                    result = "error !!! arguments are not valid JSON"
                print(result[:500])
                messages.append({"role":"tool","tool_call_id": tc.id,"content":result})

    print("\nStopped: step limit reached")

if __name__== "__main__":
    run_agent("Create sum.py that reads a list like [2,3] from input and prints the sum. "
              "Test it with [2,3] and confirm it prints 5.")
