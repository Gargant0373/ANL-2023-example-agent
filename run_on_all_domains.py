import json
import time
from pathlib import Path
from utils.plot_trace import plot_trace
from utils.runners import run_session

# ========== CONFIGURATION ========== #
NUM_MATCHES = 1
AGENT_NAME = "Dreamteam109"
AGENT_CLASS = "agents.ANL2022.dreamteam109_agent.partyclass"
YOUR_AGENT_CLASS = "agents.template_agent.template_agent.TemplateAgent"
DOMAIN_PREFIX = "domain"
DOMAIN_COUNT = 50  # domain00 to domain49
# ====================================== #

for i in range(DOMAIN_COUNT):
    domain_id = f"{DOMAIN_PREFIX}{i:02d}"
    profile_a = f"domains/{domain_id}/profileA.json"
    profile_b = f"domains/{domain_id}/profileB.json"

    print(f"\n[{domain_id}] Running {NUM_MATCHES} matches...")

    results_dir = Path("results", f"{NUM_MATCHES}_vs_{AGENT_NAME}_{domain_id}_" + time.strftime('%Y%m%d-%H%M%S'))
    results_dir.mkdir(parents=True, exist_ok=True)

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
        "profiles": [profile_a, profile_b],
        "deadline_time_ms": 10000,
    }

    all_traces = []
    all_summaries = []

    for match_index in range(NUM_MATCHES):
        print(f"[{domain_id}] Match {match_index + 1}/{NUM_MATCHES}...")
        trace, summary = run_session(settings)
        all_traces.append(trace)
        all_summaries.append(summary)

        if not trace["error"]:
            plot_trace(trace, results_dir.joinpath(f"trace_plot_{match_index + 1}.html"))

    # Save JSON results
    with open(results_dir / "all_traces.json", "w") as f:
        json.dump(all_traces, f, indent=2)

    with open(results_dir / "all_summaries.json", "w") as f:
        json.dump(all_summaries, f, indent=2)

    print(f"✅ Done with {domain_id}! Results saved in {results_dir}")
