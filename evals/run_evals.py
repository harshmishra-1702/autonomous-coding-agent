import contextlib, io, os, shutil, sys, time
from agent.graph import run_agent_graph
from agent.sandbox import Sandbox

def out(sb, cmd):
    return sb.exec(cmd)[1].strip()

TASKS = [
    {"name": "fizzbuzz",
     "task": "Create fizzbuzz.py that prints FizzBuzz for 1 to 15, one item per line, then run it.",
     "setup": {},
     "check": lambda sb: out(sb, "python fizzbuzz.py").splitlines() == [
         "1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"]},
    {"name": "stdin_sum",
     "task": "Create sum.py that reads a list like [2,3] from stdin and prints the sum. Test it with [2,3].",
     "setup": {},
     "check": lambda sb: out(sb, "echo '[2,3,5]' | python sum.py") == "10"},
    {"name": "fix_bug",
     "task": "bug.py is broken. Fix it so it prints 42.",
     "setup": {"bug.py": "print(undefined_var)\n"},
     "check": lambda sb: out(sb, "python bug.py") == "42"},
    {"name": "small_edit",
     "task": "In config.py change PORT to 9000. Leave every other line exactly as it is.",
     "setup": {"config.py": "DEBUG = True\nPORT = 8000\nHOST = 'localhost'\n"},
     "check": lambda sb: out(sb, "cat config.py").splitlines() == ["DEBUG = True", "PORT = 9000", "HOST = 'localhost'"]},
    {"name": "add_with_test",
     "task": "Create calc.py with a function add(a, b) and test_calc.py that tests it with plain asserts. Run the test.",
     "setup": {},
     "check": lambda sb: out(sb, "python -c \"from calc import add; print(add(2, 3))\"") == "5"
                         and sb.exec("python test_calc.py")[0] == 0},
]

def run_task(t, root):
    d = os.path.join(root, "evals", "runs",t["name"])
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "workspace"))
    for fname, text in t["setup"].items():
        with open(os.path.join(d, "workspace", fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    os.chdir(d)
    start = time.time()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            run_agent_graph(t["task"], max_steps=10)
        with Sandbox() as sb:
            ok = bool(t["check"](sb))
    except Exception as e:
        ok = False
        print(f"  error: {type(e).__name__}: {str(e)[:120]}")
    finally:
        os.chdir(root)
    return ok, time.time() - start


if __name__ == "__main__":
    root = os.getcwd()
    names = sys.argv[1:]
    results = []
    for t in TASKS:
        if names and t["name"] not in names:
            continue
        ok, secs = run_task(t,root)
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'} {t['name']:<15} {secs:5.0f}s")
    print(f"\nScore: {sum(results)}/{len(results)}")