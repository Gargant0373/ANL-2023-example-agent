import json
import matplotlib.pyplot as plt
import numpy as np

# Load from file
with open("log.json") as f:
    data = json.load(f)

all_bids = []
agreements = []

# Normalize and collect utilities
for match in data:
    u1 = match.get("utility_1") or match.get("utility_3")
    u2 = match.get("utility_2") or match.get("utility_4")
    if u1 is not None and u2 is not None:
        all_bids.append((u1, u2))
        if match.get("result") == "agreement":
            agreements.append((u1, u2))

# Function to compute Pareto front
def compute_pareto(points):
    points = sorted(set(points), reverse=True)  # sort by utility A descending
    pareto = []
    max_b = -1
    for a, b in points:
        if b > max_b:
            pareto.append((a, b))
            max_b = b
    return pareto

pareto_front = compute_pareto(all_bids)

# Plot
x_all, y_all = zip(*all_bids)
x_agree, y_agree = zip(*agreements) if agreements else ([], [])
x_pareto, y_pareto = zip(*pareto_front)

plt.figure(figsize=(8, 6))
plt.scatter(x_all, y_all, color='blue', s=5, alpha=0.3, label="All Bids")
plt.scatter(x_agree, y_agree, color='green', s=100, label="Agreement")
plt.plot(x_pareto, y_pareto, color='red', linewidth=2, marker='o', label="Pareto Front")

plt.xlabel("Utility A")
plt.ylabel("Utility B")
plt.title("Negotiation Outcomes in Bid Space")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
