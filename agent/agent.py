import json
from agent.llm import chat_with_tools
from agent.sandbox import Sandbox
from agent.tools import Tools, TOOL_SCHEMAS

SYSTEM ="You are a coding agent. Use the tools to complete the task. Files live in /workspace."

def one_step(task):
    messages = [{"role": "system","content": SYSTEM},
                {"role": "user", "content":task}]

    msg = chat_with_tools(messages, TOOL_SCHEMAS)

    if not msg.tool_calls:
        print("Brain said:", msg.content)
        return

    with Sandbox() as sb:
        tools = Tools(sb)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"Brain chose: {tc.function.name}({args})")
            print("Result: ",tools.call(tc.function.name, args))

if __name__=="__main__":
    one_step("Create hello.py that prints hello and run it.")