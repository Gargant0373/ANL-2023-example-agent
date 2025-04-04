from ctypes import cast

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Domain import Domain
from geniusweb.profile.utilityspace.DiscreteValueSetUtilities import DiscreteValueSetUtilities
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import LinearAdditiveUtilitySpace


class Helper:
    def __init__(self, domain: Domain, profile: LinearAdditiveUtilitySpace):
        """
        Class which implements the logic for dynamically keeping track of the preference profile of the
        agent given the specific domain and the interaction with the opponent agent.
        :param domain: the domain of the negotiation
        :param profile: the preference profile model
        """
        self.profile = profile
        self.domain = domain

        # Data structure which keeps tracks of the offered values for each of the domain issue
        self.offered_values_for_issues: dict[str, set] = {}
        # Initialise the data structure defined above
        self.create_dictionary_for_issues()

        # Data structure that stores the values of all the issues (within the negotiation domain)
        # sorted (values) based on their utility (descending order)
        self.values_sorted_by_utility = {}
        # Initialize the data structure defined above
        self.create_values_sorted_by_utility()

    def create_dictionary_for_issues(self):
        for issue in self.domain.getIssues():
            self.offered_values_for_issues[issue] = set()

    def create_values_sorted_by_utility(self):
        # dict of str -> ValueSet
        dict_of_values = self.profile.getUtilities()
        for issue, values in self.profile.getUtilities().items():
            discrete_values = values
            # Get the utility of each value of the considered issue
            dict_of_values = discrete_values.getUtilities()
            self.values_sorted_by_utility[issue] = sorted(dict_of_values.items(), key=lambda item: item[1], reverse=True)


    def update_offers_with_bid(self, bid: Bid):
        for issue, value in bid.getIssueValues().items():
            self.offered_values_for_issues[issue].add(value)

    def is_value_in_bid(self, issue, value):
        """
        Utility method for checking whether a specific value was already offered for an issue
        :param issue: the issue considered
        :param value: the value to check
        """
        return value in self.offered_values_for_issues[issue]

    def get_highest_value_for_issue(self, issue):
        return self.values_sorted_by_utility[issue][0][0]