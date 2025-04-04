import logging
from random import randint
from time import time
from typing import cast

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

from .utils.opponent_model import OpponentModel

from decimal import Decimal


class Group42Agent(DefaultParty):
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

        self.last_received_bid: Bid = None
        self.opponent_model: OpponentModel = None
        self.logger.log(logging.INFO, "party is initialized")

        # Needed for conflict-based strategy
        self.O_opp = []
        self.O_cbom = []

        # For keeping track of bids
        self.oponent_bid_history = []
        # For keeping track of the trend, used for flag on if trend has increased
        self.has_increased = False

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
        return "Agent 42, Only accepting the best it can get!"

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

            # update opponent model with bid
            self.opponent_model.update(bid)
            # set bid as last received
            self.last_received_bid = bid

            # Add to O_opp for conflict-based strategy
            self.O_opp.append(bid)

    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        # check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
        else:
            # if not, find a bid to propose as counter offer
            bid = self.find_bid()
            action = Offer(self.me, bid)
            # Add to O_chem for conflict-based strategy
            self.O_cbom.append(bid)

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
        # We accept bids only if
        if bid is None:
            return False

        # progress of the negotiation session between 0 and 1 (1 is deadline)
        progress = self.progress.get(time() * 1000)
        current_utility = self.profile.getUtility(bid)

        self.oponent_bid_history.append(current_utility)

        # Define thresholds used in code
        utility_threshold = 0.75
        time_threshold = 0.98
        hard_utility_threshold = 0.5

        # Only run analysis if we have enough data points
        if len(self.oponent_bid_history) > 5:
            recent_avg = sum(self.oponent_bid_history[-5:]) / 5
            overall_avg = sum(self.oponent_bid_history) / len(self.oponent_bid_history)

            # Calculate oponent trend for offers,
            # we take the average of the last bids to see if the trend is going up or down.
            # if trend is going down don't accept. if trend is going up consider accepting

            if recent_avg < (overall_avg * Decimal("0.95")):  # Opponent is making worse offers
                return False  # Reject worsening offers

            # Calculate recent trend using last 5 offers
            recent_trend = [
                self.oponent_bid_history[i] - self.oponent_bid_history[i - 1]
                for i in range(-4, 0)
            ]

            increasing_trend = all(change > 0 for change in recent_trend)
            trend_flat = all(abs(change) < 0.02 for change in recent_trend)

            # If the trend was increasing but has now flattened, accept
            if self.has_increased and trend_flat:
                return True

            # If we seen a increasing trend. we keep the bool true
            self.has_increased = increasing_trend or self.has_increased

        # Fallback to basic acceptance criteria
        return current_utility > utility_threshold or (progress > time_threshold and current_utility > hard_utility_threshold)

    def find_bid(self) -> Bid:
        domain = self.profile.getDomain()
        O_space = AllBidsList(domain)
        n = 100 # Should be changed

        U_cbom = self.profile.getUtility
        U_opp = None
        epsilon = 0
        TU_Hybrid = self._calculate_TU_Hybrid(U_cbom)

        O_potential = []
        while (len(O_potential) < 1):
            for o in O_space:
                utility = float(U_cbom(o))
                if(utility >= TU_Hybrid - epsilon and utility <= TU_Hybrid + epsilon and o not in self.O_cbom):
                    O_potential.append(o)
            epsilon += 0.01

        Utility_O_potential = [U_cbom(O) for O in O_potential]
        O_t_cbom = np.argmax(Utility_O_potential)
        if (len(self.O_opp) >= n):
            if self.opponent_model is not None:
                U_opp = self.opponent_model.get_predicted_utility
                Utility_O_potential = [U_cbom(O) * U_opp(O) for O in O_potential]
                O_t_cbom = np.argmax(Utility_O_potential)

        return O_potential[O_t_cbom]

    def _calculate_TU_Hybrid(self, U_cbom):
        # Fix this condition check
        if (len(self.O_opp) < 2 or len(self.O_cbom) < 1):
            return 0.8

        P_0 = 0.9
        P_1 = 0.7
        P_2 = 0.4
        P_3 = 0.1 # Not defined in the paper

        t = self.progress.get(time() * 1000)
        mu = P_3 + t * P_3
        n = len(self.O_opp)

        Delta_U = 0
        for i in range(1, n):
            Delta_U += U_cbom(self.O_opp[i]) - U_cbom(self.O_opp[i-1])
        Delta_U = float(Delta_U)

        TU_Behaviour = float(U_cbom(self.O_cbom[-1])) - mu * Delta_U
        TU_Times = ((1-t) ** 2) * P_0 + (2 * (1-t) * t * P_1) + (t ** 2) * P_2
        TU_Hybrid = (t**2) * TU_Times + (1-t**2) * TU_Behaviour

        return TU_Hybrid
