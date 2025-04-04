from collections import defaultdict

import numpy as np
from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.DiscreteValueSet import DiscreteValueSet
from geniusweb.issuevalue.Domain import Domain
from geniusweb.issuevalue.Value import Value


class OpponentModel:
    def __init__(self, domain: Domain):
        # Offers received from the oponent
        self.offers = []
        self.domain = domain

        self.issue_estimators = {
            i: IssueEstimator(v, self.offers) for i, v in domain.getIssuesValues().items()
        }

    def update(self, bid: Bid):
        # Keep track of all bids received
        self.offers.append(bid)

        # Update all issue estimators with the value that is offered for that issue
        for issue_id, issue_estimator in self.issue_estimators.items():
            issue_estimator.update(bid.getValue(issue_id))

        # Normalize the issue weights after the individual updates
        total_weight = 0
        for issue in self.issue_estimators.values():
            total_weight += issue.weight

        if total_weight != 0:
            for issue in self.issue_estimators.values():
                # Update the estimated value of the issue weight with the normalized value
                issue.set_normalized_weight(issue.weight / total_weight)
        else:
            for issue in self.issue_estimators.values():
                # Update the estimated value of the issue weight with the normalized value
                issue.set_normalized_weight(1.0 / len(self.issue_estimators))

    def get_predicted_utility(self, bid: Bid):
        if len(self.offers) == 0 or bid is None:
            return 0

        # Retrieve the current estimates of the issue weights and value utilities
        value_utilities = []
        issue_weights = []

        for issue_id, issue_estimator in self.issue_estimators.items():
            # Get the value that is set for this issue in the bid
            value: Value = bid.getValue(issue_id)

            # Collect both the estimated weight for the issue and
            # estimated utility of the value within this issue
            value_utilities.append(issue_estimator.get_value_utility(value))
            issue_weights.append(issue_estimator.weight)

        # calculate predicted utility by multiplying all value utilities with their issue weight
        predicted_utility = sum(
            [iw * vu for iw, vu in zip(issue_weights, value_utilities)]
        )

        return predicted_utility


class IssueEstimator:
    def __init__(self, value_set: DiscreteValueSet, offers):
        if not isinstance(value_set, DiscreteValueSet):
            raise TypeError(
                "This issue estimator only supports issues with discrete values"
            )

        self.bids_received = 0
        # Tracker for the highest recorded count of an individual value of the issue
        self.max_value_count = 0
        self.num_values = value_set.size()
        self.value_before = None
        self.offers = offers
        self.value_trackers = defaultdict(ValueEstimator)

        # Parameter used for constructing the estimate of the issue weight
        # Value is used to quantify the frequency of the most occuring value
        # This reflects the fact that the importance of an issue is determined by the unwillingness
        # of the opponent to concede on the issue.
        self.frequency_weight = 0
        # Parameter used for constructing the estimate of the issue weight
        # Value quantifies the insistence of the opponent on a single value for the issue
        self.streak_weight = 0.0
        # Currently estimated weight of the issue
        self.weight = 0

    def get_value_utility(self, value: Value):
        if value in self.value_trackers:
            return self.value_trackers[value].utility

        return 0

    def update(self, value: Value):
        self.bids_received += 1

        # If the current value is the same as the last received value then increase the streak value
        if self.value_before is not None:
            if self.value_before == value:
                if self.streak_weight < 0.5:
                    # Increase the streak weight, as the opponent insists on a single value
                    self.update_streak_weight(self.streak_weight + 0.025)
            else:
                # Reset the streak component
                self.update_streak_weight(0)
        self.value_before = value

        # Get the value tracker of the value that is offered
        value_tracker = self.value_trackers[value]

        # Register that this value was offered i.e. update its counter
        value_tracker.update()

        # Update the count of the most common offered value
        self.max_value_count = max([value_tracker.count, self.max_value_count])

        max_count_squared = self.max_value_count ** 2
        bids_received_squared = self.bids_received ** 2
        base_frequency_weight = max_count_squared / bids_received_squared

        inverse_entropy_weight = self.calculate_inverse_entropy()

        # Adjust the frequency weight, such that given a high diversity of values reduces the frequency weight (and vice-versa)
        adjusted_frequency_weight = base_frequency_weight * inverse_entropy_weight

        self.update_frequency_weight(adjusted_frequency_weight)

        # Recalculate all estimates of the value utilities
        for value_tracker in self.value_trackers.values():
            value_tracker.recalculate_utility(self.max_value_count, self.frequency_weight)

    def calculate_inverse_entropy(self):
        """
        In order to account for the diversity of values received so far for the issue, we compute Shannon entropy for
        the issue based on the distribution of the currently recorded values.
        A higher value of the Shannon entropy would correspond to a higher diversity of values which would reflect
        a lower importance of the issue to the opponent.
        In order to create the correlation between a lower diveristy (lower entropy) and a higher importance of the issue (certainty of the opponent)
        we invert and additionally normalise it to the [0,1] range.
        """
        if self.bids_received == 0:
            return 1

        # Compute the probability for each recorded value
        probabilities = [
            value_tracker.count / self.bids_received
            for value_tracker in self.value_trackers.values()
            if value_tracker.count > 0
        ]
        # Compute the Shanon entropy
        entropy = -sum(p * np.log2(p) for p in probabilities)
        # Maximum value possible for the Shannon entropy (every value is equally likely)
        max_entropy = np.log2(len(self.value_trackers)) if len(self.value_trackers) > 1 else 1

        return 1 - (entropy / max_entropy)

    def update_frequency_weight(self, new_frequency_weight):
        """
        Update the frequency-based weight of an issue
        :param new_frequency_weight: new value
        """
        self.frequency_weight = new_frequency_weight
        self.update_weight()

    def update_streak_weight(self, new_streak_weight):
        """
        Update the streak-based weight of an issue
        :param new_streak_weight: new value
        """
        self.streak_weight = new_streak_weight
        # Update the the estimate of the issue weight given the updated streak weight
        self.update_weight()

    def update_weight(self):
        """
        Update the predicted weight of the issue given the current values of the frequency and streak weight
        """
        self.weight = self.frequency_weight + self.streak_weight

    def set_normalized_weight(self, normalized_weight):
        """
        Update the predicted weight of the issue with the normalized value
        """
        self.weight = normalized_weight


class ValueEstimator:
    def __init__(self):
        self.count = 0
        self.utility = 0

    def update(self):
        self.count += 1

    def recalculate_utility(self, max_value_count: int, weight: float):
        if weight < 1:
            mod_value_count = ((self.count + 1) ** (1 - weight)) - 1
            mod_max_value_count = ((max_value_count + 1) ** (1 - weight)) - 1

            self.utility = mod_value_count / mod_max_value_count
        else:
            self.utility = 1
