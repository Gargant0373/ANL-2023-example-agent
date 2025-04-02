import json
from collections import defaultdict
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# 📂 Set tournament folder
TOURNAMENT_FOLDER = Path("results/Tournaments/tournament5")  
RESULTS_FILE = TOURNAMENT_FOLDER / "tournament_results.json"
CSV_OUTPUT = TOURNAMENT_FOLDER / "avg_utilities.csv"
IMG_OUTPUT = TOURNAMENT_FOLDER / "avg_utilities.png"

# 📊 Load tournament results
with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

# 🧮 Accumulate utilities
agent_utilities = defaultdict(list)

for match in results:
    for key, value in match.items():
        if key.startswith("agent_") and key.replace("agent_", "utility_") in match:
            agent = value
            utility_key = key.replace("agent_", "utility_")
            utility = match[utility_key]
            agent_utilities[agent].append(utility)

# 📋 Prepare DataFrame
data = {
    "Agent": [],
    "Average Utility": [],
    "Match Count": []
}

for agent, utils in agent_utilities.items():
    data["Agent"].append(agent)
    data["Average Utility"].append(round(sum(utils) / len(utils), 4))
    data["Match Count"].append(len(utils))

df = pd.DataFrame(data).sort_values(by="Average Utility", ascending=False)

# 💾 Save as CSV
df.to_csv(CSV_OUTPUT, index=False)
print(f"✅ CSV saved: {CSV_OUTPUT}")

# 🖼️ Save as image table
fig, ax = plt.subplots(figsize=(8, 0.6 * len(df)))
ax.axis("off")
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="center",
    loc="center"
)
table.scale(1, 1.5)
plt.tight_layout()
plt.savefig(IMG_OUTPUT, bbox_inches="tight")
plt.close()
print(f"🖼️ Image saved: {IMG_OUTPUT}")
