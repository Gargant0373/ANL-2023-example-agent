import json
from collections import defaultdict
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# 📂 Set tournament folder
TOURNAMENT_FOLDER = Path("results/Tournaments/tournament17")  
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
agent_num_offers = defaultdict(list)

for match in results:
    agents = []
    for key, value in match.items():
        if key.startswith("agent_") and key.replace("agent_", "utility_") in match:
            agent = value
            utility_key = key.replace("agent_", "utility_")
            utility = match[utility_key]
            agent_utilities[agent].append(utility)
            agents.append(agent)
            agent_total_matches[agent] += 1
            agent_num_offers[agent].append(match["num_offers"])
            if match["result"] == "agreement":
                agent_agreements[agent] += 1

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
    "Avg Num Offers": []
}

# 🔤 Agent name replacements
agent_name_map = {
    "DreamTeam109Agent": "DreamTeam109",
    "Group34AgentSecondVersion": "Group34Second",
    "Group34AgentFirstVersion": "Group34First"
}


for agent in agent_utilities:
    match_count = agent_total_matches[agent]
    agreement_count = agent_agreements[agent]
    name = agent_name_map.get(agent, agent)

    data["Agent"].append(name)
    data["Avg Utility"].append(round(sum(agent_utilities[agent]) / match_count, 4))
    data["Avg Social Welfare"].append(round(sum(agent_social_welfare[agent]) / agreement_count, 4) if agreement_count else 0.0)
    data["Avg Nash Product"].append(round(sum(agent_nash_product[agent]) / agreement_count, 4) if agreement_count else 0.0)
    data["Agreement Rate (%)"].append(round((agreement_count / match_count) * 100, 2))
    data["Avg Num Offers"].append(round(sum(agent_num_offers[agent]) / match_count, 2))


df = pd.DataFrame(data).sort_values(by="Avg Utility", ascending=False)

# 💾 Save as CSV
df.to_csv(CSV_OUTPUT, index=False)
print(f"✅ CSV saved: {CSV_OUTPUT}")

# 🖼️ Save as image table
fig, ax = plt.subplots(figsize=(12, 0.5 * len(df)))
ax.axis("off")
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="center",
    loc="center"
)

# 🔠 Font adjustments
table.auto_set_font_size(False)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_fontsize(14)  # Header font size
    elif col == 0:
        cell.set_fontsize(12)  # Smaller font for first column (Agent)
    else:
        cell.set_fontsize(14)  # Larger font for other cells

table.scale(1, 1.6)

plt.tight_layout()
plt.savefig(IMG_OUTPUT, bbox_inches="tight", dpi=300)
plt.close()
print(f"🖼️ Image saved: {IMG_OUTPUT}")
