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


class TemplateAgent(DefaultParty):
    """
    Implements an ABiNeS-like strategy with a 'termination condition' (TC)
    consistent with the paper by Hao et al. The reservation value is treated
    as an alternative offer. If the discounted reservation outperforms the
    agent's acceptance threshold, the agent terminates the negotiation.
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
        
        # Non-exploitation point λ
        self.lambda_point = 0.9
        # Boulware-like exponent (α>1 => Boulware, 0<α<1 => Conceder)
        self.beta = 1.5
        
        self.opponent_bid_history = []

        self.all_bids = None  # Will store AllBidsList
        self.bids_with_utilities = None  # Will store list of (bid, utility) tuples
        self.min_util = 0.5  # Minimum utility threshold for bids we'll consider
        
        self.reservation_value = 0.5   # fallback if no reservation bid is set
        self.best_received_utility = 0.0
        
        # logs
        self.received_bids = []
        self.sent_bids = []
        self.accepted_bid = None
        self.round_number = 0


    def notifyChange(self, data: Inform):
        """Entry point of all interaction with your agent."""
        if isinstance(data, Settings):
            self.settings = cast(Settings, data)
            self.me = self.settings.getID()
            self.progress = self.settings.getProgress()
            self.parameters = self.settings.getParameters()
            self.storage_dir = self.parameters.get("storage_dir")

            # Load profile
            profile_connection = ProfileConnectionFactory.create(
                data.getProfile().getURI(), self.getReporter()
            )
            self.profile = profile_connection.getProfile()
            self.domain = self.profile.getDomain()
            profile_connection.close()

            # Precompute all bids and their utilities
            self.all_bids = AllBidsList(self.domain)
            self.bids_with_utilities = []
            for i in range(self.all_bids.size()):
                bid = self.all_bids.get(i)
                utility = float(self.profile.getUtility(bid))
                if utility >= self.reservation_value:  # Only store bids above reservation
                    self.bids_with_utilities.append((bid, utility))
            
            # Sort bids by utility (highest first)
            self.bids_with_utilities.sort(key=lambda x: x[1], reverse=True)
            
            # Set minimum utility to the utility of the 100th best bid (or last if <100)
            num_top_bids = min(100, len(self.bids_with_utilities))
            if num_top_bids > 0:
                self.min_util = self.bids_with_utilities[num_top_bids-1][1]

            self.logger.log(logging.INFO, 
                f"Precomputed {len(self.bids_with_utilities)} bids. "
                f"Top utility: {self.bids_with_utilities[0][1] if self.bids_with_utilities else 'None'}"
            )

            # Attempt to set a more accurate reservation value if the profile has one
            if self.profile.getReservationBid() is not None:
                self.reservation_value = float(self.profile.getUtility(self.profile.getReservationBid()))

        elif isinstance(data, ActionDone):
            action = cast(ActionDone, data).getAction()
            actor = action.getActor()
            
            if actor != self.me:
                # Opponent's action
                self.other = str(actor).rsplit("_", 1)[0]
                self.opponent_action(action)

        elif isinstance(data, YourTurn):
            self.my_turn()

        elif isinstance(data, Finished):
            self.save_data()
            self.logger.log(logging.INFO, "party is terminating:")
            super().terminate()
        else:
            self.logger.log(logging.WARNING, "Ignoring unknown info " + str(data))


    def getCapabilities(self) -> Capabilities:
        """Agent capabilities."""
        return Capabilities(
            set(["SAOP"]),
            set(["geniusweb.profile.utilityspace.LinearAdditive"]),
        )

    def send_action(self, action: Action):
        """Sends an action to the opponent(s)."""
        self.getConnection().send(action)


    def getDescription(self) -> str:
        """A short description of your agent."""
        return "Template agent for the ANL 2022 competition, ABiNeS-inspired"


    def opponent_action(self, action: Action):
        """Process an action that was received from the opponent."""
        if isinstance(action, Offer):
            # Initialize model if needed
            if self.opponent_model is None:
                self.opponent_model = OpponentModel(self.domain)

            bid = cast(Offer, action).getBid()
            self.opponent_model.update(bid)
            self.last_received_bid = bid

            self.round_number += 1
            utility = float(self.profile.getUtility(bid))
            self.received_bids.append({
                "round": self.round_number,
                "bid": str(bid),
                "utility": utility
            })
            self.best_received_utility = max(self.best_received_utility, utility)

            # λ adaptation based on concession ratio
            self.opponent_bid_history.append(bid)
            window = self.opponent_bid_history[-10:]
            unique_bids = {str(b) for b in window}
            concession_ratio = len(unique_bids)/len(window) if window else 0.0
            self.lambda_point = max(0.6, min(0.95, 0.9 - 0.3*concession_ratio))

        elif isinstance(action, Accept):
            # Opponent accepted something
            self.accepted_bid = cast(Accept, action).getBid()


    def my_turn(self):
        """
        Our turn: 
        1) Check the paper's Termination Condition (TC).
        2) If not terminating, check if we accept last offer.
        3) Otherwise propose a new bid.
        """
        # 1) Termination Condition => "Algorithm 3" from the paper
        # DO NOTHING, NEVER TERMINATE

        # if self.should_terminate():
        #     # we "terminate" => no agreement: 
        #     # in many frameworks, you can simply do nothing or forcibly end. 
        #     # We'll do a logging message and return.
        #     self.logger.log(logging.INFO, "Terminating negotiation: reservation is better.")
        #     # Typically you might do:
        #     # self.getConnection().send(NoAgreement(self.me))  # if your framework has that
        #     # then exit:
        #     return

        # 2) Check acceptance
        if self.accept_condition(self.last_received_bid):
            action = Accept(self.me, self.last_received_bid)
            self.accepted_bid = self.last_received_bid
        else:
            # 3) Propose a new bid
            bid = self.find_bid()
            action = Offer(self.me, bid)
            utility = float(self.profile.getUtility(bid))
            opp_utility = (self.opponent_model.get_predicted_utility(bid)
                           if self.opponent_model else 0.0)
            self.sent_bids.append({
                "round": self.round_number,
                "bid": str(bid),
                "utility": utility,
                "predicted_opponent_utility": opp_utility,
            })

        # Send final action
        self.send_action(action)


    def save_data(self):
        """Saves negotiation data for post-analysis."""
        data = {
            "received_bids": self.received_bids,
            "sent_bids": self.sent_bids,
            "accepted_bid": str(self.accepted_bid) if self.accepted_bid else None,
            "lambda_point": self.lambda_point,
            "reservation_value": self.reservation_value,
        }
        with open(f"{self.storage_dir}/data.json", "w") as f:
            json.dump(data, f, indent=2)


    ############################################################################
    ########################  Accept & Offer Methods  ##########################
    ############################################################################

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
        return utility >= self.get_acceptance_threshold()


    def find_bid(self) -> Bid:
        """Generates a new offer using precomputed bids"""
        if not self.bids_with_utilities:
            # Fallback if no bids were precomputed
            domain = self.profile.getDomain()
            all_bids = AllBidsList(domain)
            return all_bids.get(randint(0, all_bids.size()-1))

        # Only consider bids above reservation value
        valid_bids = [b for b in self.bids_with_utilities if b[1] >= self.reservation_value]
        if not valid_bids:
            return self.bids_with_utilities[0][0]  # Fallback to best bid if none meet reservation

        # Select from top 100 bids (or all if less than 100)
        num_top_bids = min(100, len(valid_bids))
        top_bids = valid_bids[:num_top_bids]
        
        # Get opponent utilities for scoring
        t = self.progress.get(time()*1000)
        alpha = 0.95
        eps = 0.1
        time_pressure = 1.0 - (t**(1/eps))
        
        # Score top bids
        scored_bids = []
        for bid, util in top_bids:
            opp_util = self.opponent_model.get_predicted_utility(bid) if self.opponent_model else 0.0
            score = alpha*time_pressure*util + (1 - alpha*time_pressure)*opp_util
            scored_bids.append((bid, score))
        
        # Sort by score
        scored_bids.sort(key=lambda x: x[1], reverse=True)
        
        # Epsilon-greedy: 10% chance to pick randomly from top 50
        if randint(1,100) <= 10:  # 10% chance
            top_k = min(49, len(scored_bids)-1)
            return scored_bids[randint(0, top_k)][0]
        else:
            return scored_bids[0][0]


    ############################################################################
    #######################  Acceptance Threshold (AT)  ########################
    ############################################################################

    def get_acceptance_threshold(self) -> float:
        """
        ABiNeS acceptance threshold, eq. (3) in the paper:
        For t <= lambda_point:
            threshold(t) = umax - [umax - umax*delta^(1-lambda)]*(t/lambda)^beta
        After lambda_point:
            threshold(t) = umax * delta^(1-t)
        (In a simpler environment, discount=1 if no discount factor is used)
        """
        t = self.progress.get(time()*1000)
        # If your profile has discounting:
        delta = 1
        umax = 1.0  # normalized max utility

        if t <= self.lambda_point:
            # Boulware from 0..lambda_point
            # typical formula: threshold(t) = umax - (umax - umax*delta^(1-lambda_point))*(t/lambda_point)^beta
            term = (umax - umax*(delta**(1 - self.lambda_point)))
            return umax - term * ((t/self.lambda_point)**self.beta)
        else:
            # after lambda => accept anything >= umax * delta^(1-t)
            return umax * (delta**(1 - t))


    ############################################################################
    ###########################  Termination (TC)  #############################
    ############################################################################

    def should_terminate(self) -> bool:
        """
        Paper’s Termination Condition (Algorithm 3):
         if discounted_reservation > current_acceptance_threshold => terminate
         else => do NOT terminate
         
        Interpreted as: treat the reservation value as an alternative 'offer' from
        the opponent. If that 'offer' is better than your acceptance threshold,
        the agent is better off stopping negotiation.
        """
        # 1. Compute the discounted reservation
        delta = 1
        t = self.progress.get(time()*1000)
        # The reservation_value is our "ru0", discount it
        discounted_reservation = self.reservation_value * (delta**t)

        # 2. Compare with acceptance threshold
        if discounted_reservation > self.get_acceptance_threshold():
            # "Accept the reservation" => effectively terminate with no agreement
            return True

        return False
