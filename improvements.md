This is based on the ABiNeS paper.

# 1. Adaptive acceptance threshold with alpha (non exploitation point)
There is not a two-phase acceptance strategy: before alpha the agent will stay tough and have slow concessions and after alpha start accepting reasonable offers to avoid timeouts. This adapts to different opponents and avoids missing good deals near the deadline.

# 2. Opponent-aware greedy bid generation
Smart scoring function that considers both my utility for a bid, as well as the predicted utility for the opponent.
90% of the time the agent will offer the best scoring bid and 10% of the time it will randomly pick from the top 50.

# 3. Adaptive λ-point based on opponent behavior
Instead of using a fixed λ-point to switch from Boulware to conceding behavior, the agent adapts λ based on opponent concessions. It tracks the diversity of recent opponent offers (bid window), and updates λ accordingly:
- If the opponent is hardlining (repeating same bids), λ increases (stay tough longer).
- If the opponent is conceding (diverse bids), λ decreases (start conceding earlier).

# 4. Reservation-aware acceptance and offer filtering
The agent enforces a minimum reservation value. It never accepts or offers bids that fall below this threshold, ensuring it never concedes beyond an acceptable minimum utility, even near the deadline. This protects against exploitation and guarantees rational outcomes.

# 5. Smart early termination (currently disabled)
The agent can terminate early when it determines that all received offers are below the reservation value and no agreement is likely. This avoids wasting rounds in hopeless negotiations, especially against hardliners.

# 6. Full negotiation trace logging for post-analysis
Each round is logged with:
- Round number
- Bid sent or received
- Utility for the agent
- Predicted opponent utility (for sent bids)
This data is stored in a JSON file and can be visualized with plot_session.py.
