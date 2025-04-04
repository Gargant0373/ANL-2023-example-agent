import decimal
import logging
from random import randint
from time import time
from typing import cast, Dict

from geniusweb.actions.Accept import Accept
from geniusweb.actions.Action import Action
from geniusweb.actions.Offer import Offer
from geniusweb.actions.PartyId import PartyId
from geniusweb.bidspace.AllBidsList import AllBidsList
from geniusweb.inform.ActionDone import ActionDone
from geniusweb.inform.Finished import Finished
from geniusweb.inform.Inform import Inform
from geniusweb.inform.Settings import Settings
from geniusweb.inform.YourTurn import YourTurn
from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.Domain import Domain
from geniusweb.party.Capabilities import Capabilities
from geniusweb.party.DefaultParty import DefaultParty
from geniusweb.profile.utilityspace.DiscreteValueSetUtilities import DiscreteValueSetUtilities
from geniusweb.profile.utilityspace.LinearAdditiveUtilitySpace import (
    LinearAdditiveUtilitySpace,
)
from geniusweb.profileconnection.ProfileConnectionFactory import (
    ProfileConnectionFactory,
)
from geniusweb.progress.ProgressTime import ProgressTime
from geniusweb.references.Parameters import Parameters
import numpy as np
from tudelft_utilities_logging.ReportToLogger import ReportToLogger

from .utils.helper_class import Helper
from .utils.opponent_model import OpponentModel
from geniusweb.issuevalue.Value import Value


class Group17Agent(DefaultParty):
    """
    Template of a Python geniusweb agent.
    """

    def __init__(self):
        super().__init__()
        self.logger: ReportToLogger = self.getReporter()

        self.domain: Domain = None
        self.parameters: Parameters = None
        self.profile: LinearAdditiveUtilitySpace = None
        self.progress: ProgressTime = None
        self.me: PartyId = None
        self.other: str = None
        self.settings: Settings = None
        self.storage_dir: str = None
        self.my_bids = []
        self.helper_class = None
        self.agreed_issues = {}
        self.projected_bid: Bid = None
        self.iso_level = 0.95 # Initialize with high utitility for self
        self.iso_increment = 0.05
        self.minimum_utility = 0.90 # initial value
        self.last_received_bid: Bid = None
        self.received_bids = []
        self.all_bids_sorted = []
        self.opponent_model: OpponentModel = None
        self.logger.log(logging.INFO, "party is initialized")

    def notifyChange(self, data: Inform):
        """MUST BE IMPLEMENTED
        This is the entry point of all interaction with your agent after is has been initialised.
        How to handle the received data is based on its class type.

        Args:
            info (Inform): Contains either a request for action or information.
        """

        # a Settings message is the first message that will be send to your
        # agent containing all the information about the negotiation session.
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()

            # progress towards the deadline has to be tracked manually through the use of the Progress object
            self.progress = self.settings.getProgress()

            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")

            # the profile contains the preferences of the agent over the domain
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            self.helper_class = Helper(self.domain, self.profile)
            all_bids = AllBidsList(self.domain)
            for b in all_bids:
                # Cache utilities of bids
                bid = {"bid": b, "utility": self.profile.getUtility(b)}
                self.all_bids_sorted.append(bid)
            self.all_bids_sorted = sorted(self.all_bids_sorted, key = lambda bid: bid['utility'], reverse=True)
            profile_connection.close()

        # ActionDone informs you of an action (an offer or an accept)
        # that is performed by one of the agents (including yourself).
        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()

            # ignore action if it is our action
            if actor != self.me:
                # obtain the name of the opponent, cutting of the position ID.
                self.other = str(actor).rsplit("_", 1)[0]

                # process action done by opponent
                self.opponent_action(action)
        # YourTurn notifies you that it is your turn to act
        elif isinstance(data, YourTurn):
            # execute a turn
            self.my_turn()

        # Finished will be send if the negotiation has ended (through agreement or deadline)
        elif isinstance(data, Finished):
            self.save_data()
            # terminate the agent MUST BE CALLED
            self.logger.log(logging.INFO, "party is terminating:")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))

    def getCapabilities(self) -> Capabilities:
        """MUST BE IMPLEMENTED
        Method to indicate to the protocol what the capabilities of this agent are.
        Leave it as is for the ANL 2022 competition

        Returns:
            Capabilities: Capabilities representation class
        """
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )

    def send_action(self, action: Action):
        """Sends an action to the opponent(s)

        Args:
            action (Action): action of this agent
        """
        self.getConnection().send(action)

    # give a description of your agent
    def getDescription(self) -> str:
        """MUST BE IMPLEMENTED
        Returns a description of your agent. 1 or 2 sentences.

        Returns:
            str: Agent description
        """
        return "Template agent for the ANL 2022 competition"

    def opponent_action(self, action):
        """Process an action that was received from the opponent.

        Args:
            action (Action): action of opponent
        """
        # if it is an offer, set the last received bid
        if isinstance(action, Offer):
            # create opponent model if it was not yet initialised
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)

            bid = cast(Offer, action).getBid()

            # Update opponent model with the information from the new bid
            self.opponent_model.update(bid)

            # Save all received bids
            self.received_bids.append({"bid": bid, "utility": self.profile.getUtility(bid)})

            # Extract the issues and their corresponding values from the bid made by the opponent
            for issue, value in bid.getIssueValues().items():
                # If the offered value of the issue equals the highest value offered for this issue by the agent itself or it is the last value that we offered
                # we mark that we have an `agreement` on this issue and record the `agreement` value
                if value.getValue() == self.helper_class.get_highest_value_for_issue(issue).getValue() or len(self.my_bids) > 0 and value.getValue() == self.my_bids[-1]['bid'].getValue(issue):
                    self.agreed_issues[issue] = value
                # Else if the equality condition does not hold then we remove the issue from the
                # list of issues that we have an agreement for
                elif issue in self.agreed_issues:
                    self.agreed_issues.pop(issue)
            # set bid as last received
            self.last_received_bid = bid

    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        # Recompute min acceptance based on time
        self.time_pressure()

        # Decrease offer if stuck
        self.decrease_offer()

        self.projected_bid = self.find_bid_2_0()
        
        # Check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # if not, find a bid to propose as counteroffer
            bid = self.projected_bid

            self.my_bids.append(bid)
            # Given the new bid, update the information stored within the helper object
            #self.helper_class.update_offers_with_bid(bid)
            action = Offer(self.me, bid['bid'])

        # send the action
        self.send_action(action)

    def save_data(self):
        """This method is called after the negotiation is finished. It can be used to store data
        for learning capabilities. Note that no extensive calculations can be done within this method.
        Taking too much time might result in your agent being killed, so use it for storage only.
        """
        data = "Data for learning (see README.md)"
        with open(f"{self.storage_dir}/data.md", "w") as f:
            f.write(data)

    ###########################################################################################
    ################################## Example methods below ##################################
    ###########################################################################################

    def accept_condition(self, bid: Bid) -> bool:
        if bid is None:
            return False

        # progress of the negotiation session between 0 and 1 (1 is deadline)
        progress = self.progress.get(time() * 1000)

        reservation_bid = self.profile.getReservationBid()
        # reservation_utility = 1.0
        # if reservation_bid is not None:
        #     reservation_utility = self.profile.getUtility(reservation_bid)
        # #TODO - accept issue with projected offer

        projected_utility = self.projected_bid['utility']
        current_utility = self.profile.getUtility(bid)

        # very basic approach that accepts if the offer is valued above 0.7 and
        # 95% of the time towards the deadline has passed
        conditions = [
            current_utility > self.minimum_utility and progress > 0.8,
            progress > 0.99, # accept something
            projected_utility <= self.profile.getUtility(self.last_received_bid), # better bid than offerd so accept
           #  current_utility * decimal.Decimal(1.0 - progress) >= reservation_utility and progress > 0.85
        ]
        return any(conditions)

    # OBSOLETE - kept for reference
    # def find_bid(self) -> Bid:
    #     # compose a list of all possible bids
    #     domain = self.profile.getDomain()
    #     all_bids_sorted = AllBidsList(domain)
    #
    #     best_bid_score = 0.0
    #     best_bid = None
    #
    #     # take 500 attempts to find a bid according to a heuristic score
    #     for _ in range(500):
    #         bid = all_bids_sorted.get(randint(0, all_bids_sorted.size() - 1))
    #         bid_score = self.score_bid(bid)
    #         if bid_score > best_bid_score:
    #             best_bid_score, best_bid = bid_score, bid
    #
    #     return best_bid

    def decrease_offer(self):
         # Already below minimum acceptance
         if self.iso_level <= self.minimum_utility:
            return

         # If already sent more than 3 bids
         if len(self.my_bids) > 3:
            UtilPast = self.my_bids[-1]['utility']
            UtilPreviousThree = self.my_bids[-4]['utility']
            OpponentUtilPast = self.received_bids[-1]['utility']
            OpponentUtilPreviousThree = self.received_bids[-2]['utility']
            

            if UtilPast >= UtilPreviousThree and OpponentUtilPast <= OpponentUtilPreviousThree:
                self.iso_level = self.minimum_utility


    # Boulware time concession strategy
    def time_pressure(self):
         progress = self.progress.get(time() * 1000)
         self.minimum_utility = np.exp(1/-(10.0-progress*7.0))
    
    def find_bid_2_0(self, max_search = 10) -> Bid:
        # If no bids yet send bid with maximum utility value
        if self.last_received_bid is None or len(self.my_bids) == 0:
            return self.all_bids_sorted[0]
        
        best_bid = None
        max_util = 0.0
        viable_bids = 0

        for bid in self.all_bids_sorted:

            # Do not send same bid twice
            if bid in self.my_bids:
                continue

            bid_utility = bid['utility']

            # Don't consider bids below min utility
            if viable_bids > max_search or float(bid_utility) <= self.iso_level - self.iso_increment:
                break
            
            # If bid is on the same ISO_Level consider it
            if np.abs(float(bid_utility) - self.iso_level) < self.iso_increment:
                
                # Make sure to keep agreed issue values
                for issue, value in self.agreed_issues.items():
                    if bid['bid'].getValue(issue) != value:
                        continue

                opponent_util = self.opponent_model.get_predicted_utility(bid['bid'])
    
                # Choose bid with maximum utility for opponent withing ISO-Level 
                if opponent_util > max_util:
                    viable_bids += 1
                    best_bid = bid
                    max_util = opponent_util

        # If no suitable bid found decerease iso-level
        if best_bid is None:
            self.iso_level -= self.iso_increment
            return self.find_bid_2_0()

        #print(self.opponent_model.get_predicted_utility(best_bid['bid']))
        return best_bid

    # def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
    #     """Calculate heuristic score for a bid

    #     Args:
    #         bid (Bid): Bid to score
    #         alpha (float, optional): Trade-off factor between self interested and
    #             altruistic behaviour. Defaults to 0.95.
    #         eps (float, optional): Time pressure factor, balances between conceding
    #             and Boulware behaviour over time. Defaults to 0.1.

    #     Returns:
    #         float: score
    #     """
    #     progress = self.progress.get(time() * 1000)

    #     our_utility = float(self.profile.getUtility(bid))

    #     time_pressure = 1.0 - progress ** (1 / eps)
    #     score = alpha * time_pressure * our_utility

    #     if self.opponent_model is not None:
    #         opponent_utility = self.opponent_model.get_predicted_utility(bid)
    #         opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
    #         score += opponent_score

    #     return score
