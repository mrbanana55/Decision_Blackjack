"""Finite state machine orchestrator for a single Blackjack round."""

from dataclasses import dataclass
from typing import Any
from app.engine.card import Card
from app.engine.hand import DealerHand, PlayerHand
from app.engine.interfaces import (
    IllegalActionError,
    InsufficientFundsError,
    InvalidBetError,
    InvalidStateError,
    RoundController,
)
from app.engine.rules import TableRules
from app.engine.settlement import RoundSettlement, settle_round
from app.engine.shoe import Shoe
from app.engine.types import (
    Action,
    DealerStyle,
    HandStatus,
    RoundPhase,
    Soft17Rule,
    SurrenderRule,
)


@dataclass
class RoundState:
    """Snapshot container representing the full table state."""

    phase: RoundPhase
    active_hand_index: int
    player_hands: list[PlayerHand]
    dealer_hand: DealerHand
    insurance_bet: float
    legal_actions: list[Action]
    shoe_cards_remaining: int
    reshuffle_needed: bool
    player_bankroll: float

    def to_dict(self) -> dict[str, Any]:
        """Convert state snapshot to dictionary representation."""
        return {
            "phase": self.phase.value,
            "active_hand_index": self.active_hand_index,
            "player_hands": [
                {
                    "hand_index": h.hand_index,
                    "cards": [{"suit": c.suit.value, "rank": c.rank.value, "value": c.nominal_value} for c in h.cards],
                    "bet": h.bet,
                    "status": h.status.value,
                    "total": h.total,
                    "is_soft": h.is_soft,
                    "is_blackjack": h.is_blackjack,
                    "is_busted": h.is_busted,
                    "is_split": h.is_split,
                    "is_doubled": h.is_doubled,
                }
                for h in self.player_hands
            ],
            "dealer_hand": {
                "cards": [
                    {"suit": c.suit.value, "rank": c.rank.value, "value": c.nominal_value}
                    for c in (self.dealer_hand.cards if self.dealer_hand.is_revealed else self.dealer_hand.cards[:1])
                ],
                "upcard": (
                    {"suit": self.dealer_hand.upcard.suit.value, "rank": self.dealer_hand.upcard.rank.value, "value": self.dealer_hand.upcard.nominal_value}
                    if self.dealer_hand.upcard
                    else None
                ),
                "is_revealed": self.dealer_hand.is_revealed,
                "visible_total": self.dealer_hand.visible_total,
            },
            "insurance_bet": self.insurance_bet,
            "legal_actions": [a.value for a in self.legal_actions],
            "shoe_cards_remaining": self.shoe_cards_remaining,
            "reshuffle_needed": self.reshuffle_needed,
            "player_bankroll": self.player_bankroll,
        }


class BlackjackRound(RoundController):
    """Finite state machine orchestrating a complete Blackjack round."""

    def __init__(
        self,
        rules: TableRules | None = None,
        shoe: Shoe | None = None,
        player_bankroll: float = 1000.0,
    ) -> None:
        self.rules: TableRules = rules if rules is not None else TableRules()
        self.shoe: Shoe = shoe if shoe is not None else Shoe(num_decks=self.rules.num_decks)
        self.current_bankroll: float = float(player_bankroll)

        self._phase: RoundPhase = RoundPhase.AWAITING_BET
        self.player_hands: list[PlayerHand] = []
        self.dealer_hand: DealerHand = DealerHand()
        self.active_hand_index: int = 0
        self.insurance_bet: float = 0.0
        self.settlement: RoundSettlement | None = None

        self._state: RoundState = RoundState(
            phase=self._phase,
            active_hand_index=0,
            player_hands=[],
            dealer_hand=self.dealer_hand,
            insurance_bet=0.0,
            legal_actions=[],
            shoe_cards_remaining=self.shoe.cards_remaining,
            reshuffle_needed=self.shoe.reshuffle_needed,
            player_bankroll=self.current_bankroll,
        )

    @property
    def phase(self) -> RoundPhase:
        """Current lifecycle phase of the round."""
        return self._phase

    @property
    def state(self) -> RoundState:
        """Current snapshot of the table state."""
        return self._update_state()

    def _update_state(self) -> RoundState:
        """Update and synchronize internal state snapshot."""
        self._state.phase = self._phase
        self._state.active_hand_index = self.active_hand_index
        self._state.player_hands = self.player_hands
        self._state.dealer_hand = self.dealer_hand
        self._state.insurance_bet = self.insurance_bet
        self._state.legal_actions = self.get_legal_actions()
        self._state.shoe_cards_remaining = self.shoe.cards_remaining
        self._state.reshuffle_needed = self.shoe.reshuffle_needed
        self._state.player_bankroll = self.current_bankroll
        return self._state

    def start_round(self, bet: float) -> RoundState:
        """Place initial bet, deal cards, and initiate round lifecycle."""
        if self._phase not in (RoundPhase.AWAITING_BET, RoundPhase.ROUND_COMPLETE):
            raise InvalidStateError(f"Cannot start round in phase {self._phase.value}.")

        # Reshuffle between rounds if cut-card penetration was reached (Clarification Q5)
        if self.shoe.reshuffle_needed:
            self.shoe.reset()

        if not self.rules.validate_bet(bet):
            raise InvalidBetError(
                f"Bet {bet} is outside table boundaries [{self.rules.min_bet}, {self.rules.max_bet}]."
            )

        if bet > self.current_bankroll:
            raise InsufficientFundsError(
                f"Bet {bet} exceeds available bankroll {self.current_bankroll}."
            )

        # Immediate deduction (Clarification Q3)
        self.current_bankroll = round(self.current_bankroll - bet, 2)

        # Initialize hands
        self.player_hands = [PlayerHand(bet=bet, hand_index=0)]
        self.dealer_hand = DealerHand()
        self.active_hand_index = 0
        self.insurance_bet = 0.0
        self.settlement = None
        self._phase = RoundPhase.DEALING

        # Deal initial cards
        self.player_hands[0].add_card(self.shoe.deal())
        self.dealer_hand.add_card(self.shoe.deal())  # Dealer upcard
        self.player_hands[0].add_card(self.shoe.deal())

        if self.rules.hole_card_rule == DealerStyle.AMERICAN_PEEK:
            # Dealer hole card dealt face-down
            self.dealer_hand.add_card(self.shoe.deal())

        # Check Insurance & Peek conditions
        upcard = self.dealer_hand.upcard
        dealer_upcard_is_ace = upcard is not None and upcard.is_ace
        dealer_upcard_is_ten = upcard is not None and upcard.nominal_value == 10

        player_bj = self.player_hands[0].is_blackjack

        if dealer_upcard_is_ace and self.rules.insurance_enabled:
            self._phase = RoundPhase.INSURANCE_OFFERED
            return self._update_state()

        if self.rules.hole_card_rule == DealerStyle.AMERICAN_PEEK and (dealer_upcard_is_ace or dealer_upcard_is_ten):
            self._phase = RoundPhase.DEALER_PEEK
            if self.dealer_hand.is_blackjack:
                self.dealer_hand.reveal()
                self._phase = RoundPhase.SETTLEMENT
                return self._update_state()
            # Dealer does not have BJ
            if player_bj:
                self._phase = RoundPhase.SETTLEMENT
                return self._update_state()
            self._phase = RoundPhase.PLAYER_TURNS
            return self._update_state()

        # Non-peek or dealer upcard < 10
        if player_bj:
            if self.rules.hole_card_rule == DealerStyle.EUROPEAN_NO_HOLE_CARD and (dealer_upcard_is_ace or dealer_upcard_is_ten):
                # Dealer draws 2nd card in DEALER_TURN
                self._phase = RoundPhase.DEALER_TURN
            else:
                self._phase = RoundPhase.SETTLEMENT
            return self._update_state()

        self._phase = RoundPhase.PLAYER_TURNS
        return self._update_state()

    def submit_insurance(self, accept: bool) -> RoundState:
        """Accept or decline the insurance side bet offer."""
        if self._phase != RoundPhase.INSURANCE_OFFERED:
            raise InvalidStateError(f"Cannot submit insurance in phase {self._phase.value}.")

        initial_bet = self.player_hands[0].bet
        insurance_amount = round(initial_bet * 0.5, 2)

        if accept:
            if insurance_amount > self.current_bankroll:
                raise InsufficientFundsError(
                    f"Insurance bet {insurance_amount} exceeds available bankroll {self.current_bankroll}."
                )
            self.current_bankroll = round(self.current_bankroll - insurance_amount, 2)
            self.insurance_bet = insurance_amount

        player_bj = self.player_hands[0].is_blackjack

        # In American Peek, dealer peeks after insurance resolution
        if self.rules.hole_card_rule == DealerStyle.AMERICAN_PEEK:
            self._phase = RoundPhase.DEALER_PEEK
            if self.dealer_hand.is_blackjack:
                self.dealer_hand.reveal()
                self._phase = RoundPhase.SETTLEMENT
                return self._update_state()
            if player_bj:
                self._phase = RoundPhase.SETTLEMENT
                return self._update_state()
            self._phase = RoundPhase.PLAYER_TURNS
            return self._update_state()

        # In ENHC
        if player_bj:
            self._phase = RoundPhase.DEALER_TURN
            return self._update_state()

        self._phase = RoundPhase.PLAYER_TURNS
        return self._update_state()

    def get_legal_actions(self) -> list[Action]:
        """Return list of valid actions for the currently active player hand."""
        if self._phase != RoundPhase.PLAYER_TURNS:
            return []

        if self.active_hand_index >= len(self.player_hands):
            return []

        active_hand = self.player_hands[self.active_hand_index]
        if active_hand.status != HandStatus.ACTIVE:
            return []

        actions: list[Action] = [Action.STAND]

        # Hit: total < 21, not doubled, not surrendered
        if active_hand.total < 21 and not active_hand.is_doubled and not active_hand.is_surrendered:
            actions.append(Action.HIT)

        # Double: 2 cards, bankroll covers bet, (not split OR DAS enabled)
        if (
            len(active_hand.cards) == 2
            and not active_hand.is_doubled
            and (not active_hand.is_split or self.rules.double_after_split)
            and self.current_bankroll >= active_hand.bet
        ):
            actions.append(Action.DOUBLE)

        # Split: matching rank/10-value, bankroll covers bet, not exceeding max split hands
        if (
            active_hand.can_split
            and len(self.player_hands) < self.rules.max_split_hands
            and self.current_bankroll >= active_hand.bet
        ):
            # Check resplit aces rule
            is_ace_split = active_hand.cards[0].is_ace
            if not (is_ace_split and active_hand.is_split and not self.rules.resplit_aces):
                actions.append(Action.SPLIT)

        # Surrender: 2 cards, not split, surrendered permitted
        if (
            len(active_hand.cards) == 2
            and not active_hand.is_split
            and self.rules.surrender_rule in (SurrenderRule.LATE, SurrenderRule.EARLY)
        ):
            actions.append(Action.SURRENDER)

        return actions

    def submit_action(self, action: Action) -> RoundState:
        """Apply player action to the currently active hand."""
        if self._phase != RoundPhase.PLAYER_TURNS:
            raise InvalidStateError(f"Cannot submit action in phase {self._phase.value}.")

        legal = self.get_legal_actions()
        if action not in legal:
            raise IllegalActionError(f"Action '{action.value}' is illegal for the active hand.")

        active_hand = self.player_hands[self.active_hand_index]

        if action == Action.HIT:
            active_hand.add_card(self.shoe.deal())
            if active_hand.is_busted:
                active_hand.status = HandStatus.BUSTED
                self._advance_hand()
            elif active_hand.total == 21:
                active_hand.status = HandStatus.STOOD
                self._advance_hand()

        elif action == Action.STAND:
            active_hand.status = HandStatus.STOOD
            self._advance_hand()

        elif action == Action.DOUBLE:
            if self.current_bankroll < active_hand.bet:
                raise InsufficientFundsError("Insufficient bankroll to double down.")
            self.current_bankroll = round(self.current_bankroll - active_hand.bet, 2)
            active_hand.bet = round(active_hand.bet * 2.0, 2)
            active_hand.is_doubled = True
            active_hand.add_card(self.shoe.deal())
            if active_hand.is_busted:
                active_hand.status = HandStatus.BUSTED
            else:
                active_hand.status = HandStatus.DOUBLED
            self._advance_hand()

        elif action == Action.SPLIT:
            if self.current_bankroll < active_hand.bet:
                raise InsufficientFundsError("Insufficient bankroll to split hand.")
            self.current_bankroll = round(self.current_bankroll - active_hand.bet, 2)

            # Separate matching card
            split_card = active_hand.cards.pop()
            new_hand = PlayerHand(
                bet=active_hand.bet,
                cards=[split_card],
                hand_index=len(self.player_hands),
                is_split=True,
            )
            active_hand.is_split = True
            self.player_hands.append(new_hand)

            # Deal second card to Hand 1 immediately (Sequential dealing - Clarification Q2)
            active_hand.add_card(self.shoe.deal())

            # Check split Aces restriction
            is_ace_split = active_hand.cards[0].is_ace
            if is_ace_split and not self.rules.hit_split_aces:
                active_hand.status = HandStatus.STOOD
                self._advance_hand()

        elif action == Action.SURRENDER:
            active_hand.is_surrendered = True
            active_hand.status = HandStatus.SURRENDERED
            self._advance_hand()

        return self._update_state()

    def _advance_hand(self) -> None:
        """Advance turn focus to next active split hand, or proceed to dealer/settlement."""
        self.active_hand_index += 1

        if self.active_hand_index < len(self.player_hands):
            next_hand = self.player_hands[self.active_hand_index]
            # Hand 2 receives its card sequentially when it becomes active
            if len(next_hand.cards) == 1:
                next_hand.add_card(self.shoe.deal())
                if next_hand.cards[0].is_ace and not self.rules.hit_split_aces:
                    next_hand.status = HandStatus.STOOD
                    self._advance_hand()
                    return
                if next_hand.total == 21:
                    next_hand.status = HandStatus.STOOD
                    self._advance_hand()
                    return
            elif next_hand.status != HandStatus.ACTIVE:
                self._advance_hand()
                return
        else:
            # All player hands have completed turns
            surviving = any(
                not h.is_busted and not h.is_surrendered
                for h in self.player_hands
            )
            if not surviving:
                # All hands busted or surrendered; dealer does not need to draw
                if self.rules.hole_card_rule == DealerStyle.AMERICAN_PEEK:
                    self.dealer_hand.reveal()
                self._phase = RoundPhase.SETTLEMENT
            else:
                self._phase = RoundPhase.DEALER_TURN

    def play_dealer_to_end(self) -> RoundState:
        """Execute deterministic dealer drawing until reaching terminal state."""
        if self._phase == RoundPhase.SETTLEMENT:
            return self._update_state()

        if self._phase != RoundPhase.DEALER_TURN:
            raise InvalidStateError(f"Cannot play dealer in phase {self._phase.value}.")

        # In American Peek, reveal hole card
        if self.rules.hole_card_rule == DealerStyle.AMERICAN_PEEK:
            self.dealer_hand.reveal()
        else:
            # In ENHC, deal second card to dealer and reveal
            if len(self.dealer_hand.cards) == 1:
                self.dealer_hand.add_card(self.shoe.deal())
            self.dealer_hand.reveal()

        # Dealer drawing loop
        while True:
            val = self.dealer_hand.evaluate()
            if val.is_busted:
                break
            if val.total < 17:
                self.dealer_hand.add_card(self.shoe.deal())
            elif val.total == 17:
                if val.is_soft and self.rules.soft_17_rule == Soft17Rule.HIT_SOFT_17:
                    # H17: Dealer hits on Soft 17
                    self.dealer_hand.add_card(self.shoe.deal())
                else:
                    # S17: Dealer stands on Soft 17
                    break
            else:
                # Hard 17-21
                break

        self._phase = RoundPhase.SETTLEMENT
        return self._update_state()

    def settle(self) -> RoundSettlement:
        """Compare all active hands against dealer, calculate payouts, and finalize bankroll."""
        if self._phase != RoundPhase.SETTLEMENT:
            raise InvalidStateError(f"Cannot settle round in phase {self._phase.value}.")

        self.settlement = settle_round(
            player_hands=self.player_hands,
            dealer_hand=self.dealer_hand,
            insurance_bet=self.insurance_bet,
            current_bankroll=self.current_bankroll,
            rules=self.rules,
        )

        self.current_bankroll = self.settlement.final_bankroll
        self._phase = RoundPhase.ROUND_COMPLETE

        # Collect dealt cards into shoe discard tray for potential recovery
        for h in self.player_hands:
            self.shoe.discard_many(h.cards)
        self.shoe.discard_many(self.dealer_hand.cards)

        self._update_state()
        return self.settlement
