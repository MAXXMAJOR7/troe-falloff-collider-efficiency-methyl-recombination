# Task 42: Pressure-Dependent Radical Recombination in a Mixed Bath Gas (Troe Fall-off + Collider Efficiency)

**Domain:** Chemistry (gas-phase chemical kinetics / combustion chemistry)
**Tier:** Low (2h): floor is 1 twist and 3 steps. This design has **2 twists and 5 pipeline steps**.

**Reviewer description (the algorithm is not named):**
A hidden function maps three real-valued inputs to one scalar through a pressure-dependent chemical rate calculation. The calculation uses a published kinetic parameter set. The expected behaviour includes limiting regimes, a crossover between them, and a composition-dependent term whose effect depends on the other inputs. Solving it takes working knowledge of unimolecular-reaction theory at research level and systematic probing across several decades of one input.

---

## 1. Domain & Algorithm
Gas-phase kinetics. The oracle returns the effective bimolecular rate constant of the radical recombination **H + CH₃ (+M) → CH₄ (+M)**. The reaction sits in the fall-off regime between its low- and high-pressure limits. The bath gas is a variable N₂/H₂O mixture, and H₂O is a much more efficient third body than N₂. The output is log₁₀ k (k in cm³ mol⁻¹ s⁻¹).

## 2. Core Method
- Lindemann–Hinshelwood fall-off: k = k∞ · Pr/(1+Pr) · F, with Pr = k₀[M]/k∞.
- Modified-Arrhenius limiting rate constants k = A Tᵇ exp(−E/RT).
- Parameters: GRI-Mech 3.0 (Smith et al. 1999), reaction `H+CH3(+M)<=>CH4(+M)`, units mol·cm·s·cal.

## 3. Twists
1. **Troe broadening factor with temperature-dependent F_cent** (Gilbert, Luther & Troe 1983). The fall-off curve is broader and flatter than the Lindemann form, with F_cent(T) = (1−α)e^(−T/T***) + αe^(−T/T*) + e^(−T**/T). Plain Lindemann overpredicts by up to 0.39 dex in the domain.
2. **Collider-weighted third-body concentration.** [M]_eff = [M]·(6.00·x_H₂O + 1.00·(1−x_H₂O)). This gives up to a 6× enhancement at low pressure, and the effect saturates toward zero at high pressure. The composition effect is therefore non-separable from pressure.

Both twists are genuine: neither is definitional, and neither disappears under algebraic simplification. The broadening factor enters inside a nested rational function of log Pr, and the efficiency effect moves the operating point along that curve.

## 4. Multi-Step Pipeline
| Step | Computation | Driven by |
|---|---|---|
| 1 | Total concentration [M] = P/(RT). Collider-weighted [M]_eff | value_a, value_b, value_c |
| 2 | k∞(T), k₀(T) from modified Arrhenius (E in cal/mol, R = 8.314462618/4.184) | value_a |
| 3 | Reduced pressure Pr = k₀[M]_eff/k∞ | all |
| 4 | Troe: F_cent(T); c = −0.4−0.67 log F_cent; n = 0.75−1.27 log F_cent; f₁ = (log Pr + c)/(n − 0.14(log Pr + c)); log F = log F_cent/(1+f₁²) | value_a, Pr |
| 5 | log₁₀ k = log₁₀ k∞ + log₁₀(Pr/(1+Pr)) + log₁₀ F, rounded to 4 d.p. | all |

Honest count: steps 1, 2, 4 and 5 are substantive, and step 3 is a ratio that links them. That gives **4 substantive steps**, above the Low floor of 3.

## 5. Input Schema
```json
{
  "value_a": "float  [300, 2500]",   // temperature, K
  "value_b": "float  [0.01, 100]",   // total pressure, atm (probe log-uniformly)
  "value_c": "float  [0, 1]"         // H2O mole fraction in N2 diluent
}
```
Each input can be probed on its own. Setting value_c = 0 switches twist 2 off exactly. Large value_b switches twist 1 off approximately (it is within 0.003 dex at 300 K, 100 atm). Note: at low T and high P, large value_c is a formal composition. Phase equilibrium is not modelled, as is standard in a kinetics rate evaluation.

## 6. Output Schema
```json
{ "output": "float, 4 decimals, observed range 9.66 – 14.45" }
```

## 7. Hardness & Twists
Measured baselines use the same probe-and-fit harness as `solution/example_solver.py`, with 200 probes, graded on 48 golden cases at tolerance 0.002:

| Solver | Model form | Score | Mean abs err |
|---|---|---|---|
| Example solver | Lindemann + Troe + efficiency | **48/48 (100 %)** | 6 × 10⁻⁶ |
| Naive A | Lindemann only (F = 1), efficiency fitted | 0/48 (0 %) | 0.042 |
| Naive B | Troe, but H₂O treated like N₂ | 1/48 (2 %) | 0.142 |

- **What exposes the twists.** Sweeping value_b over 4 decades at fixed value_a shows a sigmoidal log–log fall-off. Its width and asymmetry are not those of Lindemann, which reveals twist 1. At value_b ≈ 0.01, switching value_c from 0 to 1 shifts the output by +0.76 dex. At value_b = 100 the same switch shifts it by only +0.25 dex. That pressure dependence reveals twist 2.
- **Why a textbook approach fails.** Plain Lindemann cannot reproduce the broadened curve, and a mole-fraction-blind [M] misses up to 0.74 dex.
- **Why generic regression struggles.** The response is a rational function of log Pr with T-dependent coefficients. Pr itself is exponential in 1/T and multiplicative in P·(1+5x), so linear or additive models fail the non-separability check.
- **Deep knowledge needed.** Recognising the fall-off shape and choosing the Troe functional form, with its fixed c, n, d constants, is the main barrier. Once the form is chosen, all 11 parameters can be identified from 200 probes (shown above). The task is therefore deducible, and it is hard only through the structure-identification step. An expert might recognise the specific GRI-Mech reaction from the fitted k∞ ≈ 1.39×10¹⁶ T^−0.534, but that recognition is optional.

## 8. Constants & Citations
Every numeric literal in `oracle/implement.py` is inventoried and checked automatically by `scripts/verify_task.py`.

| Constant | Value | Source | Status |
|---|---|---|---|
| R | 8.314462618 J mol⁻¹ K⁻¹ | CODATA 2018 (NIST) | exact |
| cal_th | 4.184 J | NIST SP 811, App. B.9 | exact |
| atm | 101325 Pa | NIST SP 811, App. B.9 | exact |
| A∞, b∞, E∞ | 13.90E+15, −0.534, 536.00 | GRI-Mech 3.0, grimech30.dat line 83 | cited |
| A₀, b₀, E₀ | 2.620E+33, −4.760, 2440.00 | GRI-Mech 3.0, line 84 (LOW) | cited |
| α, T***, T*, T** | 0.7830, 74.00, 2941.00, 6964.00 | GRI-Mech 3.0, line 85 (TROE) | cited |
| ε(H₂O) | 6.00 | GRI-Mech 3.0, line 86 | cited |
| ε(N₂) | 1.00 | Chemkin/Cantera default for unlisted colliders | cited |
| c₀, c₁, n₀, n₁, d | −0.4, −0.67, 0.75, −1.27, 0.14 | Gilbert, Luther & Troe (1983); Cantera docs | cited |
| 1e-6 | m³ → cm³ | unit conversion | exact |
| 4 | output decimals | task spec | input spec |

### Citations fetched & verified (one quote per source, each under 15 words)
| Source | Where | Quote | Grounds |
|---|---|---|---|
| GRI-Mech 3.0 `grimech30.dat` (downloaded 2026-09-25) | line 83–86 | "H+CH3(+M)<=>CH4(+M)  13.90E+15  -.534  536.00" | A∞, b∞, E∞; lines 84–86 checked byte-for-byte against the code |
| Cantera docs, *Rate constants* (cantera.org/stable/reference/kinetics/rate-constants.html) | Troe falloff section | "f_1 = (log_10 P_r + C) / (N - 0.14 (log_10 P_r + C))" | Troe c, n, d and the F_cent form |
| NIST CODATA (physics.nist.gov/cgi-bin/cuu/Value?r) | R entry | "8.314 462 618... J mol⁻¹ K⁻¹" (exact) | R |
| NIST SP 811 App. B.9 | calorie / atmosphere rows | "calorieth (calth) … joule (J) 4.184 E+00" | cal_th (the same table gives atm = 1.013 25 E+05 Pa, exact) |
| Cantera 3.2.0 `ck2yaml.py` | line 748 | "self.energy_units = 'cal/mol'  # for the current REACTIONS section" | Chemkin default energy units. Cantera's GRI-Mech 3.0 object also reports default_efficiency = 1.0 |

**Citation–code match (independent).** The oracle was compared with Cantera 3.2.0 (`gri30.yaml`, reaction `CH3 + H (+M) <=> CH4 (+M)`) at 300 random points across the whole domain. The maximum |Δ log₁₀ k| was 5.0 × 10⁻⁵, which equals the 4-decimal rounding floor.

The primary Troe paper (Gilbert, Luther & Troe 1983) is behind a paywall. It was confirmed bibliographically, and the formula was verified against Cantera's documented implementation, which follows it.

## 9. Edge Cases
| ID | Input (a, b, c) | Expected | Category | Rationale |
|---|---|---|---|---|
| edge_control_1 | 300, 100, 0 | 14.4234 | control | Near high-P limit, pure N₂: both twists ~neutral (Lindemann 14.4294) |
| edge_control_2 | 1500, 1, 0 | 12.7132 | control | Pure N₂: efficiency twist exactly neutral |
| edge_control_3 | 300, 100, 1 | 14.4273 | control | High-P limit: pure H₂O shifts only 0.004 dex |
| edge_discrim_1 | 1500, 0.01, 1 | 11.5607 | discriminating | 6× collider efficiency: +0.76 dex vs N₂ (10.8001) |
| edge_discrim_2 | 1000, 10, 0.5 | 14.1731 | discriminating | Centre of fall-off (Pr ≈ 6.5): Troe −0.19 dex vs Lindemann (14.3615) |
| edge_discrim_3 | 2000, 1, 1 | 12.8030 | discriminating | Both twists fire (Lindemann 12.9815, no-eff 12.1031) |
| edge_boundary_1 | 2500, 0.01, 0 | 9.6612 | boundary | Deep low-P limit (Pr ≈ 3×10⁻⁵): output ∝ log value_b |
| edge_boundary_2 | 300, 0.01, 1 | 13.9020 | boundary | Opposite domain corner |

`golden/test_data.json` contains these 8 cases plus 40 seeded random cases (seed 42, value_b log-uniform).

---

## GATE 1: Screening
| Test | Result |
|---|---|
| Algebraic collapse | **PASS.** Non-separable: the value_c effect depends on value_b (0.76 vs 0.25 dex) |
| Domain recall | **CONCERN.** A combustion kineticist who has identified fall-off behaviour will recognise "Troe fall-off with third-body efficiencies", and that is the standard Chemkin evaluation for one reaction. It cannot be named from the neutral schema, and the specific composition (this reaction + N₂/H₂O bath + log output) is not a published method. For a Low tier, which needs 1 twist, this is acceptable |
| Twist survives | **PASS.** Both twists persist after simplification (verified numerically) |
| Genuine twist | **PASS.** 2 genuine twists |
| Two-trap | **PASS.** value_c can be probed on its own (value_c = 0 exactly disables twist 2) |
| Tier fit | **PASS.** 4 substantive steps ≥ 3; 2 twists ≥ 1 |
| PhD authenticity | **PASS.** Real mechanism parameters and real unimolecular-reaction theory |

**Verdict: PASS (with the domain-recall concern noted above)**

## GATE 2: Verification
| Check | Result |
|---|---|
| Twist integrity (freeze one, vary others) | **PASS.** Troe on/off up to 0.39 dex; efficiency on/off up to 0.74 dex; each isolable |
| No invented constant | **PASS.** AST inventory of all literals, each mapped to a source |
| Recall-reconstructability | **PASS.** Cannot be named from the schema; full recovery with 200 probes (≥ 50) |
| Citations fetched & verified | **PASS.** 5 sources fetched, quotes above; primary Troe paper confirmed bibliographically only |
| Citation–code match | **PASS.** Matches Cantera to the rounding floor |
| Output/schema neutralisation | **PASS.** Key "output", scalar float, neutral input names |
| Tier floor | **PASS** |
| Edge cases ≥ 5 | **PASS.** 3 control, 3 discriminating, 2 boundary |
| PhD-level QA | **PASS** for Low tier |

**Verdict: PASS**

**Not verified here:** the "≥ 10 % variance across 8 evaluation runs" criterion. It needs model evaluation runs, which are outside the scope of this repo.

---

## References
- Smith, G. P., Golden, D. M., Frenklach, M., et al. (1999). *GRI-Mech 3.0*. http://combustion.berkeley.edu/gri-mech/version30/
- Gilbert, R. G., Luther, K., & Troe, J. (1983). Theory of thermal unimolecular reactions in the fall-off range. II. Weak collision rate constants. *Ber. Bunsenges. Phys. Chem.* 87, 169–177.
- Troe, J. (1983). Theory of thermal unimolecular reactions in the fall-off range. I. Strong collision rate constants. *Ber. Bunsenges. Phys. Chem.* 87. https://doi.org/10.1002/bbpc.19830870217
- Kee, R. J., Rupley, F. M., & Miller, J. A. (1989). *Chemkin-II*. Sandia Report SAND89-8009.
- Goodwin, D. G., et al. *Cantera* (v3.2.0). https://cantera.org
- NIST (2018). CODATA Recommended Values of the Fundamental Physical Constants. https://physics.nist.gov/cuu/Constants/
- Thompson, A., & Taylor, B. N. (2008). *Guide for the Use of the SI* (NIST SP 811), Appendix B.9.
