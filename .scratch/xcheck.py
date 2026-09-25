import sys, math, random
sys.path.insert(0, "oracle")
import cantera as ct
from implement import compute
g = ct.Solution("gri30.yaml")
idx = [i for i, r in enumerate(g.reactions()) if r.equation == "CH3 + H (+M) <=> CH4 (+M)"][0]
print("reaction", g.reactions()[idx].equation, g.reactions()[idx].rate)
random.seed(1); worst = 0
for _ in range(300):
    T = random.uniform(300, 2500); P = 10**random.uniform(-2, 2); x = random.random()
    g.TPX = T, P*ct.one_atm, {"N2": 1-x, "H2O": x} if x < 1 else {"H2O": 1}
    kf = g.forward_rate_constants[idx] * 1000.0  # m3/kmol/s -> cm3/mol/s
    d = abs(math.log10(kf) - compute(T, P, x)); worst = max(worst, d)
print("max |diff| over 300 random points:", worst)
