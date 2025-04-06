import json
import os
from pathlib import Path
import time

from utils.runners import run_tournament

base_dir = Path("results", "Tournaments")
base_dir.mkdir(parents=True, exist_ok=True)

# Find the next available tournament folder name
existing = [int(p.name.replace("tournament", "")) for p in base_dir.glob("tournament*") if p.name.replace("tournament", "").isdigit()]
next_num = max(existing, default=0) + 1
RESULTS_DIR = base_dir / f"tournament{next_num}"
RESULTS_DIR.mkdir(parents=True)

# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation. Parameters for the agent can be added as a dict (see example)
#   You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
#   You need to specify a time deadline (is milliseconds (ms)) we are allowed to negotiate before we end without agreement.
tournament_settings = {
    "agents": [
        {
            "class": "agents.group35_agent.group35_agent.Group35Agent",
            "parameters": {"storage_dir": "agent_storage/Group35Agent"},
        },
        # {
        #     "class": "agents.group35_agent_precompute_bids.group35_agent_precompute_bids.Group35AgentPrecomputeBids",
        #     "parameters": {"storage_dir": "agent_storage/Group35AgentPrecomputeBids"},
        # },
        # {
        #     "class": "agents.group35_agent_opponent_modelling.group35_agent_opponent_modelling.Group35AgentOpponentModelling",
        #     "parameters": {"storage_dir": "agent_storage/Group35AgentOpponentModelling"},
        # },
        {
            "class": "agents.charging_boul.charging_boul.ChargingBoul",
            "parameters": {"storage_dir": "agent_storage/ChargingBoul"},
        },
        {
            "class": "agents.dreamteam109_agent.dreamteam109_agent.DreamTeam109Agent",
            "parameters": {"storage_dir": "agent_storage/DreamTeam109Agent"},
        },
        {
            "class": "agents.super_agent.super_agent.SuperAgent",
            "parameters": {"storage_dir": "agent_storage/SuperAgent"},
        },
        {
            "class": "agents.group17_agent.group17_agent.Group17Agent",
            "parameters": {"storage_dir": "agent_storage/Group17Agent"},
        },
        {
            "class": "agents.group42_agent.group42_agent.Group42Agent",
            "parameters": {"storage_dir": "agent_storage/Group42Agent"},
        }
    ],
    "profile_sets": [
        ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
        ["domains/domain09/profileA.json", "domains/domain09/profileB.json"],
    ],
    "deadline_time_ms": 10000,
}

# run a session and obtain results in dictionaries
tournament_steps, tournament_results, tournament_results_summary = run_tournament(tournament_settings)

# save the tournament settings for reference
with open(RESULTS_DIR.joinpath("tournament_steps.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_steps, indent=2))
# save the tournament results
with open(RESULTS_DIR.joinpath("tournament_results.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_results, indent=2))
# save the tournament results summary
tournament_results_summary.to_csv(RESULTS_DIR.joinpath("tournament_results_summary.csv"))
