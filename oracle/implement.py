"""Reference oracle (hidden from solver).

Effective bimolecular rate constant for H + CH3 (+M) -> CH4 (+M) in an
N2/H2O bath, via collider-weighted third-body concentration and Troe
fall-off broadening. Parameters are taken verbatim from GRI-Mech 3.0.

Inputs (neutral names):
    value_a : temperature, K                      [300, 2500]
    value_b : total pressure, atm                 [0.01, 100]
    value_c : H2O mole fraction in N2 diluent     [0, 1]
Output:
    output  : log10(k_eff / (cm^3 mol^-1 s^-1)), rounded to 4 decimals
"""
import math

# --- Exact / CODATA constants -------------------------------------------
R_J = 8.314462618            # J mol^-1 K^-1, CODATA 2018 (exact)
CAL = 4.184                  # J per thermochemical calorie, NIST SP 811 (exact)
ATM = 101325.0               # Pa per standard atmosphere, NIST SP 811 (exact)
R_CAL = R_J / CAL            # cal mol^-1 K^-1 (Chemkin activation-energy units)

# --- GRI-Mech 3.0, reaction "H+CH3(+M)<=>CH4(+M)" (units: mol, cm, s, cal) --
A_INF, B_INF, E_INF = 13.90e15, -0.534, 536.00      # high-pressure limit
A_0, B_0, E_0 = 2.620e33, -4.760, 2440.00           # LOW (low-pressure limit)
TROE_A, TROE_T3, TROE_T1, TROE_T2 = 0.7830, 74.00, 2941.00, 6964.00
EFF_H2O = 6.00                                       # H2O/6.00/
EFF_N2 = 1.00                                        # unlisted species -> 1

# --- Troe (Gilbert, Luther & Troe 1983) fixed coefficients -----------------
C_0, C_1 = -0.4, -0.67
N_0, N_1 = 0.75, -1.27
D_TROE = 0.14


def _arrhenius(a, b, e_cal, t):
    return a * t ** b * math.exp(-e_cal / (R_CAL * t))


def compute(value_a, value_b, value_c):
    t = float(value_a)
    p_atm = float(value_b)
    x_h2o = float(value_c)
    if not (t > 0 and p_atm > 0 and 0.0 <= x_h2o <= 1.0):
        raise ValueError("inputs out of domain")

    # Step 1: collider-weighted third-body concentration [M]_eff (mol cm^-3)
    c_total = p_atm * ATM / (R_J * t) * 1e-6
    m_eff = c_total * (x_h2o * EFF_H2O + (1.0 - x_h2o) * EFF_N2)

    # Step 2: modified-Arrhenius limiting rate constants
    k_inf = _arrhenius(A_INF, B_INF, E_INF, t)
    k_0 = _arrhenius(A_0, B_0, E_0, t)

    # Step 3: reduced pressure
    pr = k_0 * m_eff / k_inf

    # Step 4: Troe broadening factor
    f_cent = ((1.0 - TROE_A) * math.exp(-t / TROE_T3)
              + TROE_A * math.exp(-t / TROE_T1)
              + math.exp(-TROE_T2 / t))
    log_fc = math.log10(f_cent)
    c = C_0 + C_1 * log_fc
    n = N_0 + N_1 * log_fc
    lp = math.log10(pr) + c
    f1 = lp / (n - D_TROE * lp)
    log_f = log_fc / (1.0 + f1 * f1)

    # Step 5: fall-off rate constant, reported in log10
    log_k = math.log10(k_inf) + math.log10(pr / (1.0 + pr)) + log_f
    return round(log_k, 4)


def oracle(inputs):
    return {"output": compute(inputs["value_a"], inputs["value_b"], inputs["value_c"])}


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(oracle(json.loads(sys.stdin.read()))))
