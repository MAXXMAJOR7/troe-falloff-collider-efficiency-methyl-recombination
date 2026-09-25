"""Test runner: verify the task, grade the oracle (must be 100 %), then grade the example solver."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(label, args):
    print(f"\n=== {label} ===", flush=True)
    return subprocess.run([sys.executable] + args, cwd=ROOT).returncode


def main():
    sys.path.insert(0, HERE)
    from helpers import load_golden, load_oracle

    rc = run("verify_task", [os.path.join(HERE, "verify_task.py")])

    print("\n=== oracle self-grade ===")
    o = load_oracle()
    cases = load_golden()["cases"]
    bad = [c["id"] for c in cases if o.oracle(c["input"]) != c["expected"]]
    print(f"oracle reproduces {len(cases) - len(bad)}/{len(cases)} golden cases")
    rc |= bool(bad)

    run("example solver", [os.path.join(ROOT, "grader", "grade_submission.py"),
                           os.path.join(ROOT, "solution", "example_solver.py")])
    print("\nOVERALL:", "PASS" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main())
