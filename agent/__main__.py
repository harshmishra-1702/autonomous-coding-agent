import sys
from agent.graph import run_agent_graph

task = " ".join(sys.argv[1:]) or "Create fizzbuzz.py that prints FizzBuzz for 1 to 15, then run it."
run_agent_graph(task)