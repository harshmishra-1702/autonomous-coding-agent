import argparse, contextlib, io, os, shutil, time
from agent.graph import run_agent_graph
from agent.sandbox import Sandbox

CALC_TEST = ("from calc import add, is_even\n"
             "assert add(2, 3) == 5\n"
             "assert add(-1, 1) == 0\n"
             "assert is_even(4)\n"
             "assert not is_even(7)\n"
             "print('ok')\n")
SETTINGS = 'NAME = "app"\nRETRIES = 3\nTIMEOUT = 30\nDEBUG = False\nRETRY_DELAY = 3\n'
SALES = "region,amount\nnorth,120\nsouth,80\nnorth,50\neast,25\n"

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
    {"name": "fix_failing_test",
     "task": "test_calc.py is failing. Run it, find the bugs in calc.py, and fix calc.py. Do not change test_calc.py.",
     "setup": {"calc.py": "def add(a, b):\n    return a - b\n\ndef is_even(n):\n    return n % 2 == 1\n",
               "test_calc.py": CALC_TEST},
     "check": lambda sb: out(sb, "python test_calc.py") == "ok"
                         and out(sb, "cat test_calc.py") == CALC_TEST.strip()},
    {"name": "rename_across_files",
     "task": "Rename the function greet to welcome in utils.py and update main.py so it still prints Hello, World.",
     "setup": {"utils.py": 'def greet(name):\n    return f"Hello, {name}"\n',
               "main.py": 'from utils import greet\nprint(greet("World"))\n'},
     "check": lambda sb: out(sb, "python main.py") == "Hello, World"
                         and sb.exec("grep -l greet *.py")[0] == 1},
    {"name": "csv_total",
     "task": "Write total.py that reads sales.csv and prints the total of the amount column, then run it.",
     "setup": {"sales.csv": SALES},
     "check": lambda sb: out(sb, "python total.py") in ("275", "275.0")},
    {"name": "distinct_words",
     "task": "Create words.py that reads text from stdin and prints only the number of distinct words, ignoring case. Test it.",
     "setup": {},
     "check": lambda sb: out(sb, "echo 'the cat The dog a cat' | python words.py") == "4"},
    {"name": "edit_similar_lines",
     "task": "In settings.py change RETRIES to 5. Do not change any other line.",
     "setup": {"settings.py": SETTINGS},
     "check": lambda sb: out(sb, "cat settings.py").splitlines() == [
         'NAME = "app"', "RETRIES = 5", "TIMEOUT = 30", "DEBUG = False", "RETRY_DELAY = 3"]},
]

def run_task(t, root, i):
    d = os.path.join(root, "evals", "runs", f"{t['name']}-{i}")
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
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="run only these tasks")
    ap.add_argument("--runs", type=int, default=1, help="runs per task")
    args = ap.parse_args()
    root = os.getcwd()
    rows = []
    for t in TASKS:
        if args.names and t["name"] not in args.names:
            continue
        results = [run_task(t, root, i) for i in range(1, args.runs + 1)]
        passed = sum(ok for ok, _ in results)
        avg = sum(s for _, s in results) / len(results)
        rows.append((t["name"], passed, args.runs, avg))
        print(f"{passed}/{args.runs}  {t['name']:<20} {avg:4.0f}s avg")
    print(f"\nScore: {sum(r[1] for r in rows)}/{sum(r[2] for r in rows)}")
    print("\n| Task | Passed | Avg time |\n|---|---|---|")
    for name, p, n, s in rows:
        print(f"| {name} | {p}/{n} | {s:.0f}s |")