import json
import time
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from utils.plot_trace import plot_trace
from utils.runners import run_session

# ========== 🔧 CONFIG ========== #
AGENT_1_NAME = "AgentFO2"
AGENT_1_CLASS = "agents.ANL2022.AgentFO2.partyclass"

AGENT_2_NAME = "TemplateAgent"
AGENT_2_CLASS = "agents.template_agent.template_agent.TemplateAgent"

DOMAIN = "domain00"
NUM_MATCHES = 2

PROFILE_A = f"domains/{DOMAIN}/profileA.json"
PROFILE_B = f"domains/{DOMAIN}/profileB.json"

timestamp = time.strftime('%Y%m%d-%H%M%S')
RESULTS_DIR = Path("results", f"{NUM_MATCHES}_vs_{AGENT_1_NAME}_{DOMAIN}_{timestamp}")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ========== 🔁 RUN MATCHES ========== #
settings = {
    "agents": [
        {"class": AGENT_1_CLASS, "parameters": {"storage_dir": f"agent_storage/{AGENT_1_NAME}"}},
        {"class": AGENT_2_CLASS, "parameters": {"storage_dir": f"agent_storage/{AGENT_2_NAME}"}},
    ],
    "profiles": [PROFILE_A, PROFILE_B],
    "deadline_time_ms": 10000,
}

all_traces = []
all_summaries = []

for i in range(NUM_MATCHES):
    print(f"▶ Match {i+1}/{NUM_MATCHES}")
    trace, summary = run_session(settings)
    all_traces.append(trace)
    all_summaries.append(summary)

    if not trace.get("error"):
        plot_trace(trace, RESULTS_DIR / f"trace_plot_{i+1}.html")

# ========== 💾 SAVE LOG FILES ========== #
with open(RESULTS_DIR / "all_traces.json", "w") as f:
    json.dump(all_traces, f, indent=2)

with open(RESULTS_DIR / "all_summaries.json", "w") as f:
    json.dump(all_summaries, f, indent=2)

print("✅ Negotiations done. Saved traces & summaries.")

# ========== 📊 STATS GENERATION ========== #
def extract_utilities(data, agent_name):
    utilities = []
    agreements = 0
    for entry in data:
        if entry.get("result") == "agreement":
            agreements += 1
        for key in entry:
            if key.startswith("agent_") and entry[key] == agent_name:
                index = key.split("_")[1]
                util_key = f"utility_{index}"
                if util_key in entry:
                    utilities.append(entry[util_key])
                break
    return utilities, agreements, len(data)

def compute_stats(utilities, agreement_count, total_runs):
    s = pd.Series(utilities)
    return {
        "count": s.count(),
        "min": s.min(),
        "max": s.max(),
        "mean": s.mean(),
        "median": s.median(),
        "std_dev": s.std(),
        "variance": s.var(),
        "25th_percentile": s.quantile(0.25),
        "75th_percentile": s.quantile(0.75),
        "agreement_rate (%)": (agreement_count / total_runs) * 100
    }

utils, agreed, total = extract_utilities(all_summaries, AGENT_2_NAME)
stats = compute_stats(utils, agreed, total)

stats_path = RESULTS_DIR / "utility_stats.csv"
pd.DataFrame([stats]).to_csv(stats_path, index=False)
print(f"📄 Stats saved: {stats_path}")

# ========== 📈 PLOT OUTCOMES ========== #
def plot_bidspace(data, out_path):
    all_bids = []
    agreements = []

    for match in data:
        u1 = match.get("utility_1") or match.get("utility_3")
        u2 = match.get("utility_2") or match.get("utility_4")
        if u1 is not None and u2 is not None:
            all_bids.append((u1, u2))
            if match.get("result") == "agreement":
                agreements.append((u1, u2))

    def pareto(points):
        points = sorted(set(points), reverse=True)
        pf, max_b = [], -1
        for a, b in points:
            if b > max_b:
                pf.append((a, b))
                max_b = b
        return pf

    # Compute Pareto front
    pareto_front = pareto(all_bids)

    # Compute special points
    all_bids_arr = np.array(all_bids)
    social_welfare_point = max(all_bids, key=lambda x: x[0] + x[1])
    nash_point = max(all_bids, key=lambda x: x[0] * x[1])
    kalai_point = max(all_bids, key=lambda x: min(x[0], x[1]))

    # Unzip points
    x_all, y_all = zip(*all_bids)
    x_agr, y_agr = zip(*agreements) if agreements else ([], [])
    x_pf, y_pf = zip(*pareto_front)

    # Plot
    plt.figure(figsize=(8, 6))
    plt.scatter(x_all, y_all, s=5, alpha=0.3, color="blue", label="All Bids")
    plt.scatter(x_agr, y_agr, s=100, color="green", label="Agreement")
    plt.plot(x_pf, y_pf, marker='o', color='red', linewidth=2, label="Pareto Front")
    plt.scatter(*social_welfare_point, s=100, marker='s', color='dodgerblue', label="Social Welfare")
    plt.scatter(*nash_point, s=100, marker='D', color='orange', label="Nash")
    plt.scatter(*kalai_point, s=100, marker='^', color='limegreen', label="Kalai-Smorodinsky")

    plt.xlabel("Utility A")
    plt.ylabel("Utility B")
    plt.title("Negotiation Outcomes in Bid Space")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"📊 Plot saved: {out_path}")

plot_bidspace(all_summaries, RESULTS_DIR / "negotiation_plot.png")



# import json
# import time
# from pathlib import Path
# from utils.plot_trace import plot_trace
# from utils.runners import run_session

# # ========== 🔧 CONFIGURATION ==========
# # Customize these:
# NUM_MATCHES = 30
# AGENT_NAME = "AgentFO2"
# # AGENT_CLASS = "agents.ANL2022.super_agent.partyclass"
# # AGENT_CLASS = "agents.ANL2022.dreamteam109_agent.partyclass"
# # AGENT_CLASS = "agents.linear_agent.linear_agent.LinearAgent"
# # AGENT_CLASS = "agents.boulware_agent.boulware_agent.BoulwareAgent"
# AGENT_CLASS = "agents.ANL2022.AgentFO2.partyclass"
# YOUR_AGENT_CLASS = "agents.template_agent.template_agent.TemplateAgent"

# DOMAIN = "domain00"  # just change to domain01, domain05, etc.
# PROFILE_A = f"domains/{DOMAIN}/profileA.json"
# PROFILE_B = f"domains/{DOMAIN}/profileB.json"
# # ======================================

# # Create output folder
# RESULTS_DIR = Path("results", f"{NUM_MATCHES}_vs_{AGENT_NAME}_{DOMAIN}_" + time.strftime('%Y%m%d-%H%M%S'))
# RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# # Agent settings
# settings = {
#     "agents": [
#         {
#             "class": AGENT_CLASS,
#             "parameters": {"storage_dir": f"agent_storage/{AGENT_NAME}"},
#         },
#         {
#             "class": YOUR_AGENT_CLASS,
#             "parameters": {"storage_dir": "agent_storage/TemplateAgent"},
#         },
#     ],
#     "profiles": [PROFILE_A, PROFILE_B],
#     "deadline_time_ms": 10000,
# }

# # Run loop
# all_traces = []
# all_summaries = []

# for i in range(NUM_MATCHES):
#     print(f"Running match {i+1}/{NUM_MATCHES}...")
#     trace, summary = run_session(settings)
#     all_traces.append(trace)
#     all_summaries.append(summary)

#     if not trace["error"]:
#         plot_trace(trace, RESULTS_DIR.joinpath(f"trace_plot_{i+1}.html"))

# # Save results
# with open(RESULTS_DIR / "all_traces.json", "w") as f:
#     json.dump(all_traces, f, indent=2)

# with open(RESULTS_DIR / "all_summaries.json", "w") as f:
#     json.dump(all_summaries, f, indent=2)

# print(f"✅ Done! Results saved in {RESULTS_DIR}")
