"""Dynamic builder generating situation-specific TypeSafe System One requests for Jev."""

from app.engine.card import Card
from app.engine.rules import TableRules
from app.engine.types import Action, SurrenderRule
from app.integrations.jev.schemas import (
    ChoiceQuestion,
    HandSituationType,
    SystemOneRequest,
)
from app.simulation.types import DecisionContext

ACTION_DESCRIPTIONS: dict[Action, str] = {
    Action.HIT: "Request an additional card from the dealer",
    Action.STAND: "Conclude turn and maintain current hand total",
    Action.DOUBLE: "Double the initial wager, take exactly one card, and stand",
    Action.SPLIT: "Separate pair of cards into two independent hands with matching wager",
    Action.SURRENDER: "Forfeit half the initial wager and retire the hand",
}


class JevSchemaBuilder:
    """Builds structured TypeSafe System One requests matching dynamic game context."""

    def detect_hand_situation(self, context: DecisionContext) -> HandSituationType:
        """Categorize the active hand state into a HandSituationType."""
        if len(context.player_cards) >= 3:
            return HandSituationType.MULTI_CARD_DRAW

        if len(context.player_cards) == 2:
            if Action.SPLIT in context.legal_actions:
                return HandSituationType.INITIAL_PAIR_SPLIT
            return HandSituationType.INITIAL_STANDARD

        return HandSituationType.MULTI_CARD_DRAW

    def format_cards(self, cards: list[Card]) -> str:
        """Format a list of cards with rank value and suit names."""
        return ", ".join(f"{c.rank.value} of {c.suit.value.title()}" for c in cards)

    def format_hand_state(
        self,
        context: DecisionContext,
        rules: TableRules | None = None,
        bankroll: float | None = None,
    ) -> str:
        """Build a descriptive state string summarizing observable table context."""
        cards_str = self.format_cards(context.player_cards)
        soft_hard = "Soft" if context.is_soft else "Hard"

        pair_note = ""
        if (
            len(context.player_cards) == 2
            and context.player_cards[0].rank == context.player_cards[1].rank
        ):
            pair_note = f" (Pair of {context.player_cards[0].rank.value}s)"

        dealer_str = (
            f"{context.dealer_upcard.rank.value} of {context.dealer_upcard.suit.value.title()}"
            if context.dealer_upcard
            else "Unknown"
        )

        state_parts = [
            f"You are playing blackjack. Round {context.round_number}, Hand {context.hand_index + 1}.",
            f"Player holds [{cards_str}]{pair_note} (Total: {context.player_total}, {soft_hard}).",
            f"Dealer Upcard: {dealer_str}.",
        ]

        if bankroll is not None:
            state_parts.append(f"Bankroll: ${bankroll:,.2f}.")

        if context.true_count is not None:
            tc_sign = "+" if context.true_count >= 0 else ""
            state_parts.append(f"True Count: {tc_sign}{context.true_count:.1f}.")

        if rules is not None:
            surrender_enabled = (
                getattr(rules, "surrender_rule", SurrenderRule.NONE) != SurrenderRule.NONE
                or getattr(rules, "allow_late_surrender", False)
            )
            surrender_status = "Enabled" if surrender_enabled else "Disabled"
            state_parts.append(f"Surrender: {surrender_status}.")
            state_parts.append(f"Table Minimum Bet: ${rules.min_bet:,.2f}.")

        legal_str = ", ".join(act.name.lower() for act in context.legal_actions)
        state_parts.append(f"Legal actions: {legal_str}.")

        return " ".join(state_parts)

    def build_hand_decision_request(
        self,
        context: DecisionContext,
        rules: TableRules | None = None,
        bankroll: float | None = None,
        model: str = "jev-latest",
    ) -> SystemOneRequest:
        """Construct a SystemOneRequest for in-hand playing actions (Hit, Stand, Double, etc.)."""
        situation = self.detect_hand_situation(context)
        state_desc = self.format_hand_state(context, rules=rules, bankroll=bankroll)

        criteria: dict[str, str] = {}
        for action in context.legal_actions:
            key = action.name.lower()
            desc = ACTION_DESCRIPTIONS.get(action, f"Execute {key} action")
            criteria[key] = desc

        # Fallback safeguard: hit and stand if empty
        if not criteria:
            criteria["hit"] = ACTION_DESCRIPTIONS[Action.HIT]
            criteria["stand"] = ACTION_DESCRIPTIONS[Action.STAND]

        # Determine context-specific question instruction
        if situation == HandSituationType.INITIAL_PAIR_SPLIT:
            instruction = "Select the optimal action for the paired hand given the dealer upcard and table rules."
        elif situation == HandSituationType.INITIAL_STANDARD:
            surrender_active = (
                getattr(rules, "surrender_rule", SurrenderRule.NONE) != SurrenderRule.NONE
                or getattr(rules, "allow_late_surrender", False)
            ) if rules else False
            if surrender_active and Action.SURRENDER in context.legal_actions:
                instruction = "Select the optimal action for the player hand given the dealer upcard and table state (surrender is allowed)."
            else:
                instruction = "Select the optimal action for the player hand given the dealer upcard and table state."
        else:
            instruction = "Select the optimal action for the multi-card hand given the dealer upcard and table state."

        question = ChoiceQuestion(
            type="choice",
            instructions=instruction,
            criteria=criteria,
        )

        model_name = model if isinstance(model, str) else "jev-latest"
        return SystemOneRequest(
            state=state_desc,
            model=model_name,
            questions={"action": question},
        )

    def build_betting_request(
        self,
        bankroll: float,
        rules: TableRules,
        true_count: float = 0.0,
        cards_seen: int = 0,
        total_cards: int = 312,
        round_number: int = 1,
        model: str = "jev-latest",
    ) -> SystemOneRequest:
        """Construct a SystemOneRequest for round-opening wager sizing."""
        min_bet = rules.min_bet
        tc_sign = "+" if true_count >= 0 else ""
        state_desc = (
            f"You are playing blackjack. Round {round_number}. "
            f"Table Rules Minimum Bet: ${min_bet:,.2f}. "
            f"Current Bankroll: ${bankroll:,.2f}. "
            f"Shoe True Count: {tc_sign}{true_count:.1f}. "
            f"Cards Seen: {cards_seen}/{total_cards}."
        )

        criteria: dict[str, str] = {
            "1x": f"1 unit (${min_bet:,.2f}) - Base table minimum wager",
        }

        # Multipliers eligible based on bankroll
        if bankroll >= min_bet * 2:
            criteria["2x"] = f"2 units (${min_bet * 2:,.2f}) - Moderate count advantage wager"
        if bankroll >= min_bet * 4:
            criteria["4x"] = f"4 units (${min_bet * 4:,.2f}) - Elevated count advantage wager"
        if bankroll >= min_bet * 8:
            criteria["8x"] = f"8 units (${min_bet * 8:,.2f}) - High count maximum spread wager"

        if len(criteria) == 1:
            criteria["min"] = f"All-in remaining balance (${bankroll:,.2f})"

        question = ChoiceQuestion(
            type="choice",
            instructions="Select the opening wager level for the upcoming round given the shoe count and current bankroll.",
            criteria=criteria,
        )

        model_name = model if isinstance(model, str) else "jev-latest"
        return SystemOneRequest(
            state=state_desc,
            model=model_name,
            questions={"bet_sizing": question},
        )

    def build_insurance_request(
        self,
        context: DecisionContext,
        insurance_cost: float,
        bankroll: float | None = None,
        model: str = "jev-latest",
    ) -> SystemOneRequest:
        """Construct a SystemOneRequest for the insurance offer phase."""
        cards_str = self.format_cards(context.player_cards)
        tc_sign = "+" if context.true_count >= 0 else ""
        bankroll_str = f"Bankroll: ${bankroll:,.2f}. " if bankroll is not None else ""

        state_desc = (
            f"You are playing blackjack. Dealer exposed upcard is Ace. "
            f"Player holds [{cards_str}] (Total: {context.player_total}). "
            f"{bankroll_str}"
            f"True Count: {tc_sign}{context.true_count:.1f}. "
            f"Insurance cost: ${insurance_cost:,.2f}."
        )

        criteria = {
            "accept": f"Pay insurance wager of ${insurance_cost:,.2f} to protect against dealer natural Blackjack (pays 2:1)",
            "decline": "Decline insurance side bet and proceed to normal hand resolution",
        }

        question = ChoiceQuestion(
            type="choice",
            instructions="Decide whether to accept or decline the insurance side bet against a possible dealer Blackjack.",
            criteria=criteria,
        )

        model_name = model if isinstance(model, str) else "jev-latest"
        return SystemOneRequest(
            state=state_desc,
            model=model_name,
            questions={"insurance": question},
        )
