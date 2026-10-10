"""Configurable table rules and casino constraint parameters."""

from dataclasses import dataclass
from app.engine.types import DealerStyle, Soft17Rule, SurrenderRule


@dataclass(slots=True)
class TableRules:
    """Configurable table rules conforming to casino standards."""

    soft_17_rule: Soft17Rule = Soft17Rule.STAND_ON_SOFT_17
    blackjack_payout_ratio: float = 1.5  # 3:2 payout = 1.5x
    hole_card_rule: DealerStyle = DealerStyle.AMERICAN_PEEK
    insurance_enabled: bool = True
    insurance_payout_ratio: float = 2.0  # 2:1 payout = 2.0x
    surrender_rule: SurrenderRule = SurrenderRule.LATE
    double_after_split: bool = True  # DAS
    max_split_hands: int = 4
    resplit_aces: bool = False  # RSA
    hit_split_aces: bool = False
    min_bet: float = 10.0
    max_bet: float = 500.0
    num_decks: int = 6
    penetration: float = 0.75
    burn_cards_count: int = 0

    def validate_bet(self, amount: float) -> bool:
        """Verify that an initial bet falls within configured boundaries."""
        return self.min_bet <= amount <= self.max_bet
