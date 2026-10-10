"""Pure settlement logic and payout arithmetic for concluded Blackjack rounds."""

from dataclasses import dataclass
from app.engine.hand import DealerHand, PlayerHand
from app.engine.rules import TableRules
from app.engine.types import DealerStyle, HandStatus, SettlementOutcome


@dataclass(slots=True)
class HandSettlement:
    """Financial outcome for an individual player hand."""

    hand_index: int
    outcome: SettlementOutcome
    player_total: int
    dealer_total: int
    bet: float
    payout: float  # Gross funds returned (stake + win)
    net_profit: float  # Net change for this hand (payout - bet)
    description: str


@dataclass(slots=True)
class RoundSettlement:
    """Comprehensive financial and outcome summary for a concluded round."""

    hand_outcomes: list[HandSettlement]
    insurance_bet: float
    insurance_payout: float
    total_staked: float
    gross_return: float
    net_profit: float
    final_bankroll: float


def settle_round(
    player_hands: list[PlayerHand],
    dealer_hand: DealerHand,
    insurance_bet: float,
    current_bankroll: float,
    rules: TableRules,
) -> RoundSettlement:
    """Calculate payouts, resolve insurance, and determine final bankroll."""
    hand_outcomes: list[HandSettlement] = []
    total_hand_bets = sum(h.bet for h in player_hands)
    total_staked = total_hand_bets + insurance_bet

    dealer_val = dealer_hand.evaluate()
    dealer_bj = dealer_val.is_blackjack
    dealer_busted = dealer_val.is_busted
    dealer_total = dealer_val.total

    for idx, hand in enumerate(player_hands):
        hand_val = hand.evaluate()
        player_total = hand_val.total
        bet = hand.bet

        # 1. Surrender
        if hand.is_surrendered:
            payout = round(bet * 0.5, 2)
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.SURRENDER,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=payout,
                    net_profit=round(payout - bet, 2),
                    description="Player surrendered hand (50% refund).",
                )
            )
            continue

        # 2. Player Bust
        if hand_val.is_busted:
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.LOSS,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=0.0,
                    net_profit=-bet,
                    description=f"Player busted ({player_total}).",
                )
            )
            continue

        # 3. Dealer Natural Blackjack
        if dealer_bj:
            if hand_val.is_blackjack:
                # Push on matching natural blackjacks
                hand_outcomes.append(
                    HandSettlement(
                        hand_index=idx,
                        outcome=SettlementOutcome.PUSH,
                        player_total=player_total,
                        dealer_total=dealer_total,
                        bet=bet,
                        payout=bet,
                        net_profit=0.0,
                        description="Push: Both player and dealer hold natural Blackjack.",
                    )
                )
            else:
                # Player loss to dealer Blackjack
                hand_outcomes.append(
                    HandSettlement(
                        hand_index=idx,
                        outcome=SettlementOutcome.LOSS,
                        player_total=player_total,
                        dealer_total=dealer_total,
                        bet=bet,
                        payout=0.0,
                        net_profit=-bet,
                        description="Dealer has natural Blackjack.",
                    )
                )
            continue

        # 4. Player Natural Blackjack (dealer does NOT have Blackjack)
        if hand_val.is_blackjack:
            profit = round(bet * rules.blackjack_payout_ratio, 2)
            payout = round(bet + profit, 2)
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.NATURAL_BLACKJACK,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=payout,
                    net_profit=profit,
                    description=f"Natural Blackjack win ({rules.blackjack_payout_ratio} payout).",
                )
            )
            continue

        # 5. Dealer Busted (and player did not bust)
        if dealer_busted:
            payout = round(bet * 2.0, 2)
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.WIN,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=payout,
                    net_profit=bet,
                    description=f"Dealer busted ({dealer_total}). Player wins 1:1.",
                )
            )
            continue

        # 6. Normal Total Comparisons
        if player_total > dealer_total:
            payout = round(bet * 2.0, 2)
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.WIN,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=payout,
                    net_profit=bet,
                    description=f"Player wins ({player_total} vs {dealer_total}).",
                )
            )
        elif player_total < dealer_total:
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.LOSS,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=0.0,
                    net_profit=-bet,
                    description=f"Dealer wins ({dealer_total} vs {player_total}).",
                )
            )
        else:
            # Push
            hand_outcomes.append(
                HandSettlement(
                    hand_index=idx,
                    outcome=SettlementOutcome.PUSH,
                    player_total=player_total,
                    dealer_total=dealer_total,
                    bet=bet,
                    payout=bet,
                    net_profit=0.0,
                    description=f"Push: Equal score ({player_total}). Stake returned.",
                )
            )

    # Resolve Insurance
    insurance_payout = 0.0
    if insurance_bet > 0.0:
        if dealer_bj:
            # Pays 2:1 plus returned insurance bet
            insurance_payout = round(insurance_bet + (insurance_bet * rules.insurance_payout_ratio), 2)
        else:
            insurance_payout = 0.0

    gross_return = round(sum(h.payout for h in hand_outcomes) + insurance_payout, 2)
    net_profit = round(gross_return - total_staked, 2)
    final_bankroll = round(current_bankroll + gross_return, 2)

    return RoundSettlement(
        hand_outcomes=hand_outcomes,
        insurance_bet=insurance_bet,
        insurance_payout=insurance_payout,
        total_staked=total_staked,
        gross_return=gross_return,
        net_profit=net_profit,
        final_bankroll=final_bankroll,
    )
