from collections import defaultdict
from scipy.stats import beta  # <-- Only new import

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.DiscreteValueSet import DiscreteValueSet
from geniusweb.issuevalue.Domain import Domain
from geniusweb.issuevalue.Value import Value


class OpponentModel:
    """
    Models the opponent's preferences across negotiation issues using Bayesian learning.

    This class maintains a separate BayesianIssueEstimator for each issue in the domain. 
    Each estimator tracks the value preferences of the opponent based on observed bids,
    allowing the agent to estimate the opponent's utility for any given bid.

    Attributes:
        offers (list): History of all bids received from the opponent.
        domain (Domain): The negotiation domain, containing all issues and their values.
        issue_estimators (dict): A mapping from issue IDs to their corresponding 
                                 BayesianIssueEstimator instances.

    Methods:
        update(bid): Updates all issue estimators with the values from a newly received bid.
        get_predicted_utility(bid): Estimates the opponent's utility for a given bid 
                                    based on current value and issue weight predictions.
    """
    def __init__(self, domain: Domain):
        self.offers = []
        self.domain = domain
        self.issue_estimators = {
            i: BayesianIssueEstimator(v) for i, v in domain.getIssuesValues().items()  # <-- Changed to Bayesian
        }

    def update(self, bid: Bid):
        self.offers.append(bid)
        for issue_id, issue_estimator in self.issue_estimators.items():
            issue_estimator.update(bid.getValue(issue_id))

    def get_predicted_utility(self, bid: Bid):
        if len(self.offers) == 0 or bid is None:
            return 0

        total_issue_weight = 0.0
        value_utilities = []
        issue_weights = []

        for issue_id, issue_estimator in self.issue_estimators.items():
            value: Value = bid.getValue(issue_id)
            value_utilities.append(issue_estimator.get_value_utility(value))
            issue_weights.append(issue_estimator.weight)
            total_issue_weight += issue_estimator.weight

        # Normalization remains identical
        if total_issue_weight == 0.0:
            issue_weights = [1 / len(issue_weights) for _ in issue_weights]
        else:
            issue_weights = [iw / total_issue_weight for iw in issue_weights]

        return sum([iw * vu for iw, vu in zip(issue_weights, value_utilities)])


class BayesianIssueEstimator:
    """
    Tracks and estimates the importance of a single issue in the negotiation 
    using Bayesian updating based on observed opponent bids.

    This class manages multiple BayesianValueEstimators (one per value in the issue)
    and updates them based on incoming bids. It also estimates the relative weight 
    of the issue, reflecting how important it appears to be for the opponent.

    Attributes:
        bids_received (int): Total number of bids observed for this issue.
        max_value_count (float): Highest observed count (alpha) for any value.
        num_values (int): Total number of discrete values in this issue.
        value_trackers (defaultdict): Maps each value to a BayesianValueEstimator.
        weight (float): Estimated weight of this issue for the opponent.
    
    Methods:
        update(value): Updates internal estimators based on the value selected in the opponent's bid.
        get_value_utility(value): Returns the estimated utility of a specific value.
    """  
    def __init__(self, value_set: DiscreteValueSet):
        if not isinstance(value_set, DiscreteValueSet):
            raise TypeError("This estimator only supports discrete values")

        self.bids_received = 0
        self.max_value_count = 0
        self.num_values = value_set.size()
        self.value_trackers = defaultdict(BayesianValueEstimator)  # <-- Changed to Bayesian
        self.weight = 0

    def update(self, value: Value):
        self.bids_received += 1
        
        # Update all value trackers (mark current value as "chosen")
        for val, tracker in self.value_trackers.items():
            tracker.update(chosen=(val == value))  # <-- Bayesian update

        # Track most frequent value (unchanged logic)
        current_count = self.value_trackers[value].alpha  # using alpha as count
        self.max_value_count = max(self.max_value_count, current_count)

        # Weight calculation remains identical
        equal_shares = self.bids_received / self.num_values
        self.weight = (self.max_value_count - equal_shares) / (
            self.bids_received - equal_shares
        )

    def get_value_utility(self, value: Value):
        if value in self.value_trackers:
            return self.value_trackers[value].get_utility()
        return 0


class BayesianValueEstimator:  # <-- Replaces ValueEstimator
    def __init__(self):
        self.alpha = 1  # Beta prior (successes)
        self.beta = 1   # Beta prior (failures)

    def update(self, chosen: bool):
        if chosen:
            self.alpha += 1
        else:
            self.beta += 1

    def get_utility(self):
        return self.alpha / (self.alpha + self.beta)  # Expected utility