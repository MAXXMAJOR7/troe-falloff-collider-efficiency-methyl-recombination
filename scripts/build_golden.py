"""Regenerate golden/test_data.json from the oracle (deterministic, seeded)."""
import json
import math
import random

from helpers import GOLDEN_PATH, load_oracle

# (id, category, label, value_a, value_b, value_c)
EDGE_CASES = [
    ("edge_control_1", "control", "Near high-pressure limit, pure N2: both twists ~neutral", 300.0, 100.0, 0.0),
    ("edge_control_2", "control", "Pure N2 diluent: collider-efficiency twist neutral", 1500.0, 1.0, 0.0),
    ("edge_control_3", "control", "High-pressure limit, pure H2O: efficiency saturated (<0.004 dex vs N2)", 300.0, 100.0, 1.0),
    ("edge_discrim_1", "discriminating", "Low pressure, pure H2O: efficiency ~6x lifts output ~0.76 dex", 1500.0, 0.01, 1.0),
    ("edge_discrim_2", "discriminating", "Centre of fall-off (Pr~6): Troe broadening lowers output 0.19 dex vs Lindemann", 1000.0, 10.0, 0.5),
    ("edge_discrim_3", "discriminating", "High T, mid fall-off, pure H2O: both twists fire together", 2000.0, 1.0, 1.0),
    ("edge_boundary_1", "boundary", "Deep low-pressure limit at domain corner: output ~ linear in log value_b", 2500.0, 0.01, 0.0),
    ("edge_boundary_2", "boundary", "Opposite corner: lowest T, lowest P, pure H2O", 300.0, 0.01, 1.0),
]

N_RANDOM = 40
SEED = 42


def main():
    o = load_oracle()
    cases = []
    for cid, cat, label, a, b, c in EDGE_CASES:
        inp = {"value_a": a, "value_b": b, "value_c": c}
        cases.append({"id": cid, "category": cat, "label": label, "input": inp, "expected": o.oracle(inp)})
    rng = random.Random(SEED)
    for i in range(N_RANDOM):
        inp = {
            "value_a": round(rng.uniform(300.0, 2500.0), 2),
            "value_b": round(10 ** rng.uniform(-2.0, 2.0), 5),
            "value_c": round(rng.random(), 4),
        }
        cases.append({"id": f"rand_{i:02d}", "category": "random", "label": "log-uniform value_b sample",
                      "input": inp, "expected": o.oracle(inp)})
    doc = {
        "schema": {
            "input": {"value_a": "float [300, 2500]", "value_b": "float [0.01, 100]", "value_c": "float [0, 1]"},
            "output": {"output": "float, 4 decimals"},
        },
        "seed": SEED,
        "cases": cases,
    }
    assert all(math.isfinite(c["expected"]["output"]) for c in cases)
    with open(GOLDEN_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    print(f"wrote {len(cases)} cases to {GOLDEN_PATH}")


if __name__ == "__main__":
    main()
