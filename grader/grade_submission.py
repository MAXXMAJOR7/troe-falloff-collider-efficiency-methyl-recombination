"""Grade a submission against golden/test_data.json.

Usage:
    python grader/grade_submission.py path/to/solver.py
        solver module exposes solve(inputs) -> {"output": float};
        if it also exposes fit(query), fit is called first with a
        budget-limited oracle query function (PROBE_BUDGET, default 200).
    python grader/grade_submission.py path/to/predictions.json
        JSON list of {"id": ..., "output": float} matching golden ids.

A case passes when |output - expected| <= TOLERANCE (0.002, absolute).
Score = passed / total. Exit code 0 always; the JSON report is printed.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from helpers import INPUT_KEYS, TOLERANCE, load_golden, load_module, load_oracle  # noqa: E402

DEFAULT_BUDGET = 200


class BudgetExceeded(RuntimeError):
    pass


def _budgeted_query(budget):
    oracle = load_oracle()
    used = [0]

    def query(inputs):
        if used[0] >= budget:
            raise BudgetExceeded(f"probe budget of {budget} exhausted")
        used[0] += 1
        return oracle.oracle({k: inputs[k] for k in INPUT_KEYS})

    return query, used


def _predictions_from_module(path, cases):
    mod = load_module(path, "submission")
    info = {}
    if hasattr(mod, "fit"):
        budget = int(getattr(mod, "PROBE_BUDGET", DEFAULT_BUDGET))
        budget = min(budget, DEFAULT_BUDGET)
        query, used = _budgeted_query(budget)
        mod.fit(query)
        info["probes_used"] = used[0]
    preds = {}
    for c in cases:
        out = mod.solve(dict(c["input"]))
        preds[c["id"]] = out["output"] if isinstance(out, dict) else out
    return preds, info


def _predictions_from_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    return {r["id"]: r["output"] for r in rows}, {}


def grade(preds, cases):
    rows, passed, abs_err = [], 0, []
    for c in cases:
        exp = c["expected"]["output"]
        got = preds.get(c["id"])
        ok = isinstance(got, (int, float)) and not isinstance(got, bool) and math.isfinite(got)
        err = abs(got - exp) if ok else None
        hit = ok and err <= TOLERANCE
        passed += hit
        if ok:
            abs_err.append(err)
        rows.append({"id": c["id"], "expected": exp, "got": got, "abs_err": err, "pass": bool(hit)})
    return {
        "score": passed / len(cases),
        "passed": passed,
        "total": len(cases),
        "tolerance": TOLERANCE,
        "mean_abs_err": sum(abs_err) / len(abs_err) if abs_err else None,
        "cases": rows,
    }


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    cases = load_golden()["cases"]
    path = argv[1]
    if path.endswith(".json"):
        preds, info = _predictions_from_json(path)
    else:
        preds, info = _predictions_from_module(path, cases)
    report = grade(preds, cases)
    report.update(info)
    verbose = os.environ.get("GRADER_VERBOSE") == "1"
    if not verbose:
        report["cases"] = [r for r in report["cases"] if not r["pass"]]
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
