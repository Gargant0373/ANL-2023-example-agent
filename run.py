import json
import time
from pathlib import Path
from utils.plot_trace import plot_trace
from utils.runners import run_session

# ========== 🔧 CONFIGURATION ==========
# Customize these:
NUM_MATCHES = 10
AGENT_NAME = "Dreamteam109"
AGENT_CLASS = "agents.ANL2022.dreamteam109_agent.partyclass"
YOUR_AGENT_CLASS = "agents.template_agent.template_agent.TemplateAgent"

DOMAIN = "domain01"  # just change to domain01, domain05, etc.
PROFILE_A = f"domains/{DOMAIN}/profileA.json"
PROFILE_B = f"domains/{DOMAIN}/profileB.json"
# ======================================

# Create output folder
RESULTS_DIR = Path("results", f"{NUM_MATCHES}_vs_{AGENT_NAME}_{DOMAIN}_" + time.strftime('%Y%m%d-%H%M%S'))
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Agent settings
settings = {
    "agents": [
        {
            "class": AGENT_CLASS,
            "parameters": {"storage_dir": f"agent_storage/{AGENT_NAME}"},
        },
        {
            "class": YOUR_AGENT_CLASS,
            "parameters": {"storage_dir": "agent_storage/TemplateAgent"},
        },
    ],
    "profiles": [PROFILE_A, PROFILE_B],
    "deadline_time_ms": 10000,
}

# Run loop
all_traces = []
all_summaries = []

for i in range(NUM_MATCHES):
    print(f"Running match {i+1}/{NUM_MATCHES}...")
    trace, summary = run_session(settings)
    all_traces.append(trace)
    all_summaries.append(summary)

    if not trace["error"]:
        plot_trace(trace, RESULTS_DIR.joinpath(f"trace_plot_{i+1}.html"))

# Save results
with open(RESULTS_DIR / "all_traces.json", "w") as f:
    json.dump(all_traces, f, indent=2)

with open(RESULTS_DIR / "all_summaries.json", "w") as f:
    json.dump(all_summaries, f, indent=2)

print(f"✅ Done! Results saved in {RESULTS_DIR}")
