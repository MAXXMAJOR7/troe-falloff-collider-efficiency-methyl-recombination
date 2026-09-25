"""Shared utilities for task scripts and grader."""
import importlib.util
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PATH = os.path.join(ROOT, "golden", "test_data.json")
ORACLE_PATH = os.path.join(ROOT, "oracle", "implement.py")

INPUT_KEYS = ("value_a", "value_b", "value_c")
INPUT_RANGES = {"value_a": (300.0, 2500.0), "value_b": (0.01, 100.0), "value_c": (0.0, 1.0)}
TOLERANCE = 0.002  # absolute, on the log10 output (~0.46 % relative in k)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_oracle():
    return load_module(ORACLE_PATH, "oracle_impl")


def load_golden(path=GOLDEN_PATH):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def variant(t, p_atm, x_h2o, troe=True, efficiency=True):
    """Oracle with individual twists frozen, for twist-integrity checks.

    troe=False       -> plain Lindemann-Hinshelwood (F = 1)
    efficiency=False -> every collider weighted 1 (H2O treated like N2)
    """
    o = load_oracle()
    c_total = p_atm * o.ATM / (o.R_J * t) * 1e-6
    eff = o.EFF_H2O if efficiency else o.EFF_N2
    m_eff = c_total * (x_h2o * eff + (1.0 - x_h2o) * o.EFF_N2)
    k_inf = o._arrhenius(o.A_INF, o.B_INF, o.E_INF, t)
    k_0 = o._arrhenius(o.A_0, o.B_0, o.E_0, t)
    pr = k_0 * m_eff / k_inf
    log_f = 0.0
    if troe:
        f_cent = ((1 - o.TROE_A) * math.exp(-t / o.TROE_T3)
                  + o.TROE_A * math.exp(-t / o.TROE_T1) + math.exp(-o.TROE_T2 / t))
        lfc = math.log10(f_cent)
        c = o.C_0 + o.C_1 * lfc
        n = o.N_0 + o.N_1 * lfc
        lp = math.log10(pr) + c
        f1 = lp / (n - o.D_TROE * lp)
        log_f = lfc / (1 + f1 * f1)
    return round(math.log10(k_inf) + math.log10(pr / (1 + pr)) + log_f, 4)


def reduced_pressure(t, p_atm, x_h2o):
    o = load_oracle()
    c_total = p_atm * o.ATM / (o.R_J * t) * 1e-6
    m_eff = c_total * (x_h2o * o.EFF_H2O + (1.0 - x_h2o) * o.EFF_N2)
    return o._arrhenius(o.A_0, o.B_0, o.E_0, t) * m_eff / o._arrhenius(o.A_INF, o.B_INF, o.E_INF, t)
