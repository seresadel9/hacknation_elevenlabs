"""P4(b): cloud computing job assignment LP."""
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import kron, eye, csr_matrix

# ---- Data ----
c = pd.read_csv("energy.csv", index_col=0).to_numpy()        # 1000 x 20, c_ij
C = pd.read_csv("capacity.csv", index_col=0).to_numpy().ravel()  # 20, C_j
n, m = c.shape

# Decision variable x_ij flattened row-major: index = i*m + j
cost = c.ravel()

# Each job fully processed: sum_j x_ij = 1   (n equality rows)
A_eq = kron(eye(n), np.ones((1, m)), format="csr")
b_eq = np.ones(n)

# Machine capacity: sum_i x_ij <= C_j        (m inequality rows)
A_ub = kron(np.ones((1, n)), eye(m), format="csr")
b_ub = C

res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
              bounds=(0, None), method="highs")
assert res.status == 0, res.message
x = res.x.reshape(n, m)

# (i) optimal energy consumption
print(f"(i)   Optimal energy consumption:            {res.fun:.4f}")

# (ii) no capacities: each job goes to its cheapest machine
uncap = c.min(axis=1).sum()
print(f"(ii)  Energy without capacity constraints:   {uncap:.4f}")

# (iii) jobs not (fully) assigned to their lowest-energy machine
best = c.argmin(axis=1)
not_best = np.sum(x[np.arange(n), best] < 1 - 1e-6)
print(f"(iii) Jobs not fully on cheapest machine:    {not_best}")

# Extras useful for parts (a)/(c)
frac = np.sum((x > 1e-6) & (x < 1 - 1e-6))
print(f"      Fractional x_ij entries:               {frac}")
print(f"      Duals of capacity constraints (<=0):   {np.round(res.ineqlin.marginals, 3)}")
