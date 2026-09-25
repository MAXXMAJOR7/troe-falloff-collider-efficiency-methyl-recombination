"""Example solver: probe the black box, then fit a hypothesised model.

Strategy (what an expert would do after exploratory probing):
  1. Sweep value_b over 4 decades at fixed value_a: output rises ~1:1 in
     log-log at small value_b and saturates at large value_b -> a fall-off
     curve (value_b behaves like pressure, value_a like temperature).
  2. At small value_b, value_c shifts the output by a near-constant offset
     that vanishes at large value_b -> value_c scales the third-body
     concentration (a collision-efficiency mixing rule).
  3. The curve is broader than Lindemann-Hinshelwood -> add a Troe
     broadening factor with a temperature-dependent F_cent.
  4. Fit all parameters to the probes with Nelder-Mead in log10 space.

This solver is illustrative and not guaranteed optimal. It only uses the
standard library.
"""
import math
import random

PROBE_BUDGET = 200
_R_CAL = 8.314462618 / 4.184
_ATM = 101325.0

# Parameter vector:
# [log10 A_inf, b_inf, E_inf/1000, log10 A_0, b_0, E_0/1000,
#  a, log10 T3, log10 T1, log10 T2, eff]
_INIT = [16.0, -0.5, 0.5, 33.0, -4.5, 2.0, 0.7, 2.0, 3.5, 3.8, 5.0]

_params = None


def _model(p, t, p_atm, x):
    la_i, b_i, e_i, la_0, b_0, e_0, a, lt3, lt1, lt2, eff = p
    m = p_atm * _ATM / (8.314462618 * t) * 1e-6 * (x * eff + (1 - x))
    lk_inf = la_i + b_i * math.log10(t) - e_i * 1000 / (_R_CAL * t) / math.log(10)
    lk_0 = la_0 + b_0 * math.log10(t) - e_0 * 1000 / (_R_CAL * t) / math.log(10)
    if m <= 0:
        return float("nan")
    lpr = lk_0 + math.log10(m) - lk_inf
    fc = ((1 - a) * math.exp(-t / 10 ** lt3) + a * math.exp(-t / 10 ** lt1)
          + math.exp(-10 ** lt2 / t))
    if fc <= 0:
        return float("nan")
    lfc = math.log10(fc)
    c = -0.4 - 0.67 * lfc
    n = 0.75 - 1.27 * lfc
    lp = lpr + c
    f1 = lp / (n - 0.14 * lp)
    return lk_inf + lpr - math.log10(1 + 10 ** lpr)


def _loss(p, data):
    s = 0.0
    for (t, pa, x), y in data:
        try:
            d = _model(p, t, pa, x) - y
        except (OverflowError, ValueError, ZeroDivisionError):
            return 1e30
        if d != d:
            return 1e30
        s += d * d
    return s / len(data)


def _nelder_mead(f, x0, step, iters):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step[j] if j == i else 0) for j in range(n)] for i in range(n)]
    vals = [f(q) for q in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=vals.__getitem__)
        pts = [pts[i] for i in order]
        vals = [vals[i] for i in order]
        cen = [sum(q[j] for q in pts[:-1]) / n for j in range(n)]
        xr = [cen[j] + (cen[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [cen[j] + 2 * (cen[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [cen[j] + 0.5 * (pts[-1][j] - cen[j]) for j in range(n)]
            fcv = f(xc)
            if fcv < vals[-1]:
                pts[-1], vals[-1] = xc, fcv
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
    best = min(range(n + 1), key=vals.__getitem__)
    return pts[best], vals[best]


def fit(query):
    """query(dict) -> {"output": float}; called at most PROBE_BUDGET times."""
    global _params
    rng = random.Random(0)
    design = []
    for t in (300, 600, 1000, 1500, 2000, 2500):          # fall-off sweeps
        for lp in (-2, -1, 0, 1, 2):
            design.append((t, 10.0 ** lp, 0.0))
        for lp in (-2, 0, 2):
            design.append((t, 10.0 ** lp, 1.0))
    while len(design) < PROBE_BUDGET:
        design.append((rng.uniform(300, 2500), 10 ** rng.uniform(-2, 2), rng.random()))
    data = [((t, p, x), query({"value_a": t, "value_b": p, "value_c": x})["output"])
            for t, p, x in design[:PROBE_BUDGET]]

    step = [0.5, 0.3, 0.5, 0.5, 0.3, 0.5, 0.1, 0.2, 0.2, 0.2, 1.0]
    best, best_v = list(_INIT), _loss(_INIT, data)
    for restart in range(6):
        start = best if restart else _INIT
        cand, v = _nelder_mead(lambda q: _loss(q, data), start, step, 4000)
        if v < best_v:
            best, best_v = cand, v
        step = [s * 0.5 for s in step]
    _params = best
    return {"rmse": math.sqrt(best_v), "params": best}


def solve(inputs):
    if _params is None:
        raise RuntimeError("call fit(query) first")
    y = _model(_params, float(inputs["value_a"]), float(inputs["value_b"]), float(inputs["value_c"]))
    return {"output": round(y, 4)}
