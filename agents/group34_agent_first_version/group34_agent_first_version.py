import logging
from random import randint
from time import time
from typing import cast
import json

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
from tudelft_utilities_logging.ReportToLogger import ReportToLogger

from .utils.opponent_model import OpponentModel


class Group34FirstVersion(DefaultParty):
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
        
        # Non exploitation point
        self.lambda_point = 0.9
        # Behavior pattern
        self.beta = 1.5
        self.opponent_bid_history = []
        
        self.reservation_value = 0.3
        self.best_received_utility = 0.0
        
        # logs
        self.received_bids = []
        self.sent_bids = []
        self.accepted_bid = None
        self.round_number = 0

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
            
            # update opponent model with bid
            self.opponent_model.update(bid)
            # set bid as last received
            self.last_received_bid = bid
            
            self.round_number += 1
            
            utility = float(self.profile.getUtility(bid))
            opponent_entry = {
                "round": self.round_number,
                "bid": str(bid),
                "utility": utility,
            }
            self.received_bids.append(opponent_entry)
            
            self.best_received_utility = max(self.best_received_utility, utility)
            
            # lambda adaptation
            self.opponent_bid_history.append(bid)
            window = self.opponent_bid_history[-10:]  # use the last 10 bids
            unique_bids = {str(b) for b in window}
            concession_ratio = len(unique_bids) / len(window) if window else 0
            
            # update lambda
            self.lambda_point = max(0.6, min(0.95, 0.9 - 0.3 * concession_ratio))

        if isinstance(action, Accept):
            self.accepted_bid = cast(Accept, action).getBid()
    def my_turn(self):
        """This method is called when it is our turn. It should decide upon an action
        to perform and send this action to the opponent.
        """
        if self.should_terminate():
            return
        
        # check if the last received offer is good enough
        if self.accept_condition(self.last_received_bid):
            # if so, accept the offer
            action = Accept(self.me, self.last_received_bid)
            self.accepted_bid = self.last_received_bid
        else:
            # if not, find a bid to propose as counter offer
            bid = self.find_bid()
            action = Offer(self.me, bid)
            utility = float(self.profile.getUtility(bid))
            opponent_utility = (
                self.opponent_model.get_predicted_utility(bid)
                if self.opponent_model else 0
            )
            
            self.sent_bids.append({
                "round": self.round_number,
                "bid": str(bid),
                "utility": utility,
                "predicted_opponent_utility": opponent_utility,
            })

        # send the action
        self.send_action(action)

    def save_data(self):
        """This method is called after the negotiation is finished. It can be used to store data
        for learning capabilities. Note that no extensive calculations can be done within this method.
        Taking too much time might result in your agent being killed, so use it for storage only.
        """
        data = {
            "received_bids": self.received_bids,
            "sent_bids": self.sent_bids,
            "accepted_bid": str(self.accepted_bid) if self.accepted_bid else None,
            "lambda_point": self.lambda_point,
            "reservation_value": self.reservation_value,
            }   
        with open(f"{self.storage_dir}/data.json", "w") as f:
            json.dump(data, f, indent=2)

    ###########################################################################################
    ################################## Example methods below ##################################
    ###########################################################################################

    def accept_condition(self, bid: Bid) -> bool:
        """ABiNeS acceptance check: 
        if utility(bid) < reservation -> reject,
        else if utility(bid) >= threshold -> accept,
        else -> reject
        """
        if not bid:
            return False
        utility = float(self.profile.getUtility(bid))
        if utility < self.reservation_value:
            return False
        
        threshold = self.get_acceptance_threshold()
        t = self.progress.get(time() * 1000)

        # Standard acceptance
        if utility >= threshold:
            return True

        # New logic: If we're very late in the game and stuck, accept weaker deals
        if t > 0.985 and utility >= 0.5:
            return True  # "Take what we can get" mode
        
        return False


    def find_bid(self) -> Bid:
        # compose a list of all possible bids
        domain = self.profile.getDomain()
        all_bids = AllBidsList(domain)

        epsilon = 0.1  # 10% chance to explore
        candidate_bids = []

        for _ in range(500):
            bid = all_bids.get(randint(0, all_bids.size() - 1))
            utility = float(self.profile.getUtility(bid))
            
            if utility < self.reservation_value:
                continue
            
            opponent_utility = (
                self.opponent_model.get_predicted_utility(bid)
                if self.opponent_model
                else 0
            )

            # combine using same alpha as before
            t = self.progress.get(time() * 1000)
            eps = 0.1
            alpha = 0.95
            time_pressure = 1.0 - t ** (1 / eps)

            score = alpha * time_pressure * utility + (1 - alpha * time_pressure) * opponent_utility
            candidate_bids.append((bid, score))

        # sort all bids by score descending
        candidate_bids.sort(key=lambda x: x[1], reverse=True)

        # greedy: explore or exploit
        if randint(1, 100) <= epsilon * 100:
            # explore: choose a random good bid from top 50
            return candidate_bids[randint(0, min(49, len(candidate_bids) - 1))][0]
        else:
            # exploit: choose best bid
            return candidate_bids[0][0]

    def score_bid(self, bid: Bid, alpha: float = 0.95, eps: float = 0.1) -> float:
        """Calculate heuristic score for a bid

        Args:
            bid (Bid): Bid to score
            alpha (float, optional): Trade-off factor between self interested and
                altruistic behaviour. Defaults to 0.95.
            eps (float, optional): Time pressure factor, balances between conceding
                and Boulware behaviour over time. Defaults to 0.1.

        Returns:
            float: score
        """
        progress = self.progress.get(time() * 1000)

        our_utility = float(self.profile.getUtility(bid))

        time_pressure = 1.0 - progress ** (1 / eps)
        score = alpha * time_pressure * our_utility

        if self.opponent_model is not None:
            opponent_utility = self.opponent_model.get_predicted_utility(bid)
            opponent_score = (1.0 - alpha * time_pressure) * opponent_utility
            score += opponent_score

        return score

    def get_acceptance_threshold(self) -> float:
        """
        Computes a time adaptive acceptance threshold
        """
        t = self.progress.get(time() * 1000) # progress between [0, 1]
        umax = 1.0 # maximum utility
        discount = 1.0
        
        if t <= self.lambda_point:
            # gradually reduce
            threshold = umax - (umax - umax * discount ** self.lambda_point) * (t / self.lambda_point) ** self.beta
        else:
            # accept any offer over discounted minimum
            threshold = umax * discount ** t
        
        return threshold
    
    def should_terminate(self) -> bool:
        """
        Determine if the agent should terminate the negotiation.
        """
        return False
        # t = self.progress.get(time() * 1000)
        # discount = 1.0
        
        # discounted_reservation = self.reservation_value * discount ** t
        
        # return self.best_received_utility < discounted_reservation