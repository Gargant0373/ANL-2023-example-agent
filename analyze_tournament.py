import json
from collections import defaultdict
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# 📂 Set tournament folder
TOURNAMENT_FOLDER = Path("results/Tournaments/tournament14")  
RESULTS_FILE = TOURNAMENT_FOLDER / "tournament_results.json"
CSV_OUTPUT = TOURNAMENT_FOLDER / "avg_utilities.csv"
IMG_OUTPUT = TOURNAMENT_FOLDER / "avg_utilities.png"

# 📊 Load tournament results
with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

# 🧮 Accumulate per-agent stats
agent_utilities = defaultdict(list)
agent_social_welfare = defaultdict(list)
agent_nash_product = defaultdict(list)
agent_agreements = defaultdict(int)
agent_total_matches = defaultdict(int)

for match in results:
    agents = []
    utilities = []
    # Gather agent names and utilities
    for key, value in match.items():
        if key.startswith("agent_") and key.replace("agent_", "utility_") in match:
            agent = value
            utility_key = key.replace("agent_", "utility_")
            utility = match[utility_key]
            agent_utilities[agent].append(utility)
            agents.append(agent)
            utilities.append(utility)
            agent_total_matches[agent] += 1
            if match["result"] == "agreement":
                agent_agreements[agent] += 1

    # Shared values for both agents
    if match["result"] == "agreement":
        for agent in agents:
            agent_social_welfare[agent].append(match["social_welfare"])
            agent_nash_product[agent].append(match["nash_product"])

# 📋 Prepare DataFrame
data = {
    "Agent": [],
    "Avg Utility": [],
    "Avg Social Welfare": [],
    "Avg Nash Product": [],
    "Agreement Rate (%)": [],
    "Match Count": []
}

for agent in agent_utilities:
    match_count = agent_total_matches[agent]
    agreement_count = agent_agreements[agent]
    data["Agent"].append(agent)
    data["Avg Utility"].append(round(sum(agent_utilities[agent]) / match_count, 4))
    data["Avg Social Welfare"].append(round(sum(agent_social_welfare[agent]) / agreement_count, 4) if agreement_count else 0.0)
    data["Avg Nash Product"].append(round(sum(agent_nash_product[agent]) / agreement_count, 4) if agreement_count else 0.0)
    data["Agreement Rate (%)"].append(round((agreement_count / match_count) * 100, 2))
    data["Match Count"].append(match_count)

df = pd.DataFrame(data).sort_values(by="Avg Utility", ascending=False)

# 💾 Save as CSV
df.to_csv(CSV_OUTPUT, index=False)
print(f"✅ CSV saved: {CSV_OUTPUT}")

# 🖼️ Save as image table
fig, ax = plt.subplots(figsize=(10, 0.6 * len(df)))
ax.axis("off")
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="center",
    loc="center"
)
table.scale(1, 1.5)
plt.tight_layout()
plt.savefig(IMG_OUTPUT, bbox_inches="tight", dpi=300) 
plt.close()
print(f"🖼️ Image saved: {IMG_OUTPUT}")
