import json
import matplotlib.pyplot as plt

with open("agent_storage/TemplateAgent/data.json") as f:
    data = json.load(f)

received = data["received_bids"]
sent = data["sent_bids"]

plt.figure(figsize=(10, 6))

plt.plot(
    [r["round"] for r in received],
    [r["utility"] for r in received],
    "ro-", label="Utility of Opponent's Offers to Agent"
)

plt.plot(
    [s["round"] for s in sent],
    [s["utility"] for s in sent],
    "bo-", label="Agent's Offers (Agent's Utility)"
)

if "predicted_opponent_utility" in sent[0]:
    plt.plot(
        [s["round"] for s in sent],
        [s["predicted_opponent_utility"] for s in sent],
        "go--", label="Agent's Offers (Predicted Opponent Utility)"
    )

plt.axhline(data["reservation_value"], color="gray", linestyle="--", label="Reservation Value")
plt.title("Negotiation Timeline")
plt.xlabel("Round")
plt.ylabel("Utility")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
