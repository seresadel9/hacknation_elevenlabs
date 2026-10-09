"""
P4(b) - Cloud computing: assign 1000 jobs to 20 machines at minimum energy.

Model:
    min   sum_i sum_j c_ij * x_ij
    s.t.  sum_j x_ij = 1        for every job i       (each job fully processed)
          sum_i x_ij <= C_j     for every machine j   (machine capacity)
          x_ij >= 0
"""
import pandas as pd
import pulp

# ---------- Load data ----------
energy = pd.read_csv("energy.csv", index_col=0)      # rows = jobs, columns = machines
capacity = pd.read_csv("capacity.csv", index_col=0)  # one capacity per machine

c = energy.values                  # c[i, j] = energy of job i on machine j
C = capacity["capacity"].values    # C[j]    = capacity of machine j

n_jobs, n_machines = c.shape
jobs = range(n_jobs)
machines = range(n_machines)

# ---------- Build the LP ----------
model = pulp.LpProblem("cloud_computing", pulp.LpMinimize)

# x[i, j] = fraction of job i processed on machine j
x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
     for i in jobs for j in machines}

# Objective: total energy consumption
model += pulp.lpSum(c[i, j] * x[i, j] for i in jobs for j in machines)

# Each job must be fully processed
for i in jobs:
    model += pulp.lpSum(x[i, j] for j in machines) == 1, f"job_{i}"

# Each machine can process at most C_j jobs
for j in machines:
    model += pulp.lpSum(x[i, j] for i in jobs) <= C[j], f"capacity_{j}"

# ---------- Solve ----------
model.solve(pulp.PULP_CBC_CMD(msg=False))
print("Status:", pulp.LpStatus[model.status])

# (i) Optimal energy consumption
optimal_energy = pulp.value(model.objective)
print(f"(i)   Optimal energy consumption: {optimal_energy:.2f}")

# (ii) Without capacities, each job simply goes to its cheapest machine
uncapacitated_energy = sum(min(c[i, :]) for i in jobs)
print(f"(ii)  Energy without capacity constraints: {uncapacitated_energy:.2f}")

# (iii) Jobs not fully assigned to their lowest-energy machine
not_on_best = 0
for i in jobs:
    best_machine = c[i, :].argmin()
    if x[i, best_machine].value() < 0.999:   # small tolerance for rounding
        not_on_best += 1
print(f"(iii) Jobs not fully assigned to their cheapest machine: {not_on_best}")

# Check whether the solution is integral (relevant for part a)
fractional = sum(1 for v in x.values() if 0.001 < v.value() < 0.999)
print(f"Number of fractional x_ij values: {fractional}")
