import json
import matplotlib.pyplot as plt

def pareto_frontier(points):
    pareto = []
    for point in sorted(points, key=lambda x: (-x[0], x[1])):
        if not pareto or point[1] > pareto[-1][1]:
            pareto.append(point)
    return pareto

# Load data
with open(r"results\\1_vs_BoulwareAgent_domain00_20250402-142819\\all_traces.json", "r") as f:
    data = json.load(f)

round = data[0]
actions = round["actions"]
agent1, agent2 = round["connections"]

# Gather all (u1, u2) offers
points = []
for action in actions:
    act = list(action.values())[0]
    if "utilities" in act:
        u1 = act["utilities"].get(agent1)
        u2 = act["utilities"].get(agent2)
        if u1 is not None and u2 is not None:
            points.append((u1, u2))

# Compute frontier and key outcomes
pareto = pareto_frontier(points)
nash = max(points, key=lambda x: x[0] * x[1])
social_welfare = max(points, key=lambda x: x[0] + x[1])
kalai = max(points, key=lambda x: min(x[0], x[1]))
agreement = points[-1]  # Last offer is usually accepted

# Plot
x, y = zip(*points)
px, py = zip(*pareto)

plt.figure(figsize=(8, 6))
plt.scatter(x, y, c='blue', s=8, alpha=0.5, label="All Bids")
plt.plot(px, py, 'r-', linewidth=2, label="Pareto Front")

plt.scatter(*social_welfare, color='blue', marker='s', s=100, label="Social Welfare")
plt.scatter(*nash, color='orange', marker='D', s=100, label="Nash")
plt.scatter(*kalai, color='green', marker='^', s=100, label="Kalai-Smorodinsky")
plt.scatter(*agreement, color='green', marker='o', s=100, label="Agreement")

plt.xlabel(f"Utility A: {agent1}")
plt.ylabel(f"Utility B: {agent2}")
plt.title("Negotiation Outcomes in Bid Space")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("negotiation_outcomes_plot.png", dpi=300)
plt.show()
