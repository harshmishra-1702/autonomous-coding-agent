import json, os, time
from typing import TypedDict, Optional
from groq import BadRequestError
from langgraph.graph import StateGraph, START, END
from agent.llm import chat_with_tools
from agent.sandbox import Sandbox
from agent.tools import Tools, TOOL_SCHEMAS
from agent.common import SYSTEM, _assistant_dict, compact  

class State(TypedDict):
    messages: list            
    step: int                 
    seen: dict                
    result: Optional[str]     
    stop: Optional[str]       

def build_graph(tools, log, max_steps):
    def agent(state):                                   
        step = state["step"] + 1
        if step > max_steps:
            log(type="abort", reason="step limit reached")
            return {"stop": "step limit reached"}
        messages = state["messages"]
        if max_steps - step == 2:
            messages.append({"role": "user", "content":
                "[NOTE : 2 steps left. Finish what is essential, then reply with a short summary and no tool call.]"})
        n = compact(messages)
        if n:
            log(type="compact", step=step, trimmed=n)
        try:
            msg = chat_with_tools(messages, TOOL_SCHEMAS)
        except BadRequestError as e:
            if "tool_use_failed" not in str(e):
                raise
            messages.append({"role": "user", "content":
                "Your last tool call was invalid. Use the exact parameter names from the schema "
                "(write_file needs 'path' and 'content')."})
            return {"messages": messages, "step": step}
        messages.append(_assistant_dict(msg))
        if not msg.tool_calls:                          
            log(type="done", step=step, summary=msg.content)
            return {"messages": messages, "step": step, "result": msg.content}
        return {"messages": messages, "step": step}

    def run_tools(state):                               
        messages, seen, step = state["messages"], dict(state["seen"]), state["step"]
        for tc in messages[-1]["tool_calls"]:
            name, args = tc["function"]["name"], {}
            try:
                args = json.loads(tc["function"]["arguments"])
                print(f"\n[{step}] {name}({args})")
                result = tools.call(name, args)
            except json.JSONDecodeError:
                result = "error: arguments were not valid JSON"
            sig = (name, json.dumps(args, sort_keys=True), result)
            seen[sig] = seen.get(sig, 0) + 1
            if seen[sig] == 2:
                result += "\n[NOTE: you already made this exact call with the same result. Try a different approach.]"
            elif seen[sig] >= 3:
                log(type="abort", step=step, reason="repeating with no progress")
                return {"stop": "repeating with no progress"}
            print(result[:500])
            log(type="tool", step=step, tool=name, args=args, result=result)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
        return {"messages": messages, "seen": seen}

    def route(state):                                   
        if state["stop"] or state["result"] is not None:
            return END
        return "tools" if state["messages"][-1].get("tool_calls") else "agent"

    g = StateGraph(State)
    g.add_node("agent", agent)
    g.add_node("tools", run_tools)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, ["tools", "agent", END])
    g.add_conditional_edges("tools", route, ["agent", END])
    return g.compile()

def run_agent_graph(task, max_steps=15):
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    def log(**event):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    log(type="task", task=task)

    init = {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": task}],
            "step": 0, "seen": {}, "result": None, "stop": None}
    with Sandbox() as sb:
        app = build_graph(Tools(sb), log, max_steps)
        final = app.invoke(init, {"recursion_limit": max_steps * 2 + 5})

    if final["result"] is not None:
        print(f"\nDONE: {final['result']}\n(log: {log_path})")
    else:
        print(f"\nStopped: {final['stop']}\n(log: {log_path})")
    return final["result"]

