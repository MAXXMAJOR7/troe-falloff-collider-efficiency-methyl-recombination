"""Automated GATE 2 checks. Exits non-zero on any failure."""
import ast
import json
import math
import random
import sys

from helpers import (GOLDEN_PATH, INPUT_KEYS, INPUT_RANGES, ORACLE_PATH, load_golden,
                     load_oracle, reduced_pressure, variant)

# Every numeric literal allowed in oracle/implement.py, with its justification.
ALLOWED_CONSTANTS = {
    8.314462618: "CODATA 2018 molar gas constant (exact)",
    4.184: "thermochemical calorie, NIST SP 811 (exact)",
    101325.0: "standard atmosphere, NIST SP 811 (exact)",
    13.90e15: "GRI-Mech 3.0 A_inf", -0.534: "GRI-Mech 3.0 b_inf", 536.00: "GRI-Mech 3.0 E_inf",
    2.620e33: "GRI-Mech 3.0 LOW A_0", -4.760: "GRI-Mech 3.0 LOW b_0", 2440.00: "GRI-Mech 3.0 LOW E_0",
    0.7830: "GRI-Mech 3.0 TROE alpha", 74.00: "GRI-Mech 3.0 TROE T***",
    2941.00: "GRI-Mech 3.0 TROE T*", 6964.00: "GRI-Mech 3.0 TROE T**",
    6.00: "GRI-Mech 3.0 H2O/6.00/", 1.00: "Chemkin default efficiency for unlisted colliders",
    -0.4: "Troe C0", -0.67: "Troe C1", 0.75: "Troe N0", -1.27: "Troe N1", 0.14: "Troe d",
    1e-6: "m^3 -> cm^3 unit conversion (exact)",
    0: "structural (domain check / round digits)", 0.0: "structural", 1.0: "structural (1 + Pr, 1 - x)",
    4: "4-decimal output rounding (task spec)",
}

failures = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        failures.append(name)


def numeric_literals(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    vals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            if isinstance(node.operand.value, (int, float)) and not isinstance(node.operand.value, bool):
                vals.append(-node.operand.value)
                node.operand.value = None  # avoid double counting the positive literal
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            vals.append(node.value)
    return vals


def main():
    o = load_oracle()
    rng = random.Random(7)

    # Determinism
    pts = [(rng.uniform(300, 2500), 10 ** rng.uniform(-2, 2), rng.random()) for _ in range(200)]
    check("deterministic", all(o.compute(*p) == o.compute(*p) for p in pts))

    # Output schema
    out = o.oracle({"value_a": 1000.0, "value_b": 1.0, "value_c": 0.2})
    check("output key is 'output' and scalar float",
          list(out) == ["output"] and isinstance(out["output"], float))
    check("4-decimal precision", all(round(o.compute(*p), 4) == o.compute(*p) for p in pts))

    # No invented constants
    unknown = [v for v in numeric_literals(ORACLE_PATH)
               if not any(v == k or (isinstance(v, float) and math.isclose(v, k, rel_tol=0, abs_tol=0))
                          for k in ALLOWED_CONSTANTS)]
    check("every oracle numeric literal is justified", not unknown, f"unjustified: {unknown}" if unknown else "")

    # Twist integrity: freezing each twist changes output, and each is I/O-isolable
    troe_diff = max(abs(o.compute(*p) - variant(*p, troe=False)) for p in pts)
    eff_diff = max(abs(o.compute(*p) - variant(*p, efficiency=False)) for p in pts)
    check("Troe twist changes output (> 10x tolerance)", troe_diff > 0.02, f"max diff {troe_diff:.4f}")
    check("efficiency twist changes output (> 10x tolerance)", eff_diff > 0.02, f"max diff {eff_diff:.4f}")
    # Isolation: value_c = 0 freezes efficiency twist exactly
    check("efficiency twist neutral at value_c = 0",
          all(o.compute(p[0], p[1], 0.0) == variant(p[0], p[1], 0.0, efficiency=False) for p in pts))
    # Isolation: Troe twist ~neutral deep in either limit, strong mid fall-off
    lo = abs(o.compute(300, 100, 1.0) - variant(300, 100, 1.0, troe=False))
    mid = abs(o.compute(1000, 10, 0.5) - variant(1000, 10, 0.5, troe=False))
    check("Troe twist small near high-P limit, large mid fall-off", lo < 0.01 and mid > 0.1,
          f"high-P diff {lo:.4f}, mid diff {mid:.4f}")
    # Efficiency effect saturates with pressure (not a separable additive offset)
    d_low = o.compute(1500, 0.01, 1.0) - o.compute(1500, 0.01, 0.0)
    d_high = o.compute(1500, 100, 1.0) - o.compute(1500, 100, 0.0)
    check("value_c effect depends on value_b (non-separable)", d_low - d_high > 0.3,
          f"low-P shift {d_low:.4f}, high-P shift {d_high:.4f}")
    # Fall-off present across domain (not collapsible to either limit)
    prs = [reduced_pressure(*p) for p in pts]
    check("domain spans both fall-off limits", min(prs) < 1e-3 and max(prs) > 1e2,
          f"Pr range {min(prs):.2e} .. {max(prs):.2e}")

    # Golden data
    g = load_golden()
    cats = [c["category"] for c in g["cases"]]
    check(">=2 discriminating edge cases", cats.count("discriminating") >= 2)
    check(">=2 control edge cases", cats.count("control") >= 2)
    check(">=1 boundary edge case", cats.count("boundary") >= 1)
    check("golden inputs neutral and in range", all(
        sorted(c["input"]) == sorted(INPUT_KEYS)
        and all(INPUT_RANGES[k][0] <= c["input"][k] <= INPUT_RANGES[k][1] for k in INPUT_KEYS)
        for c in g["cases"]))
    check("golden expected outputs match oracle",
          all(o.oracle(c["input"]) == c["expected"] for c in g["cases"]), GOLDEN_PATH)

    print(json.dumps({"failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
