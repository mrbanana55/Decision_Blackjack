"""Lookup matrices and resolution engine strictly adhering to docs/Estrategia Optima.md."""

from typing import Any
from app.engine.card import Card, Rank
from app.engine.rules import TableRules
from app.engine.types import Action


# 1. Hard Totals Matrix (Totals 8 through 17+ vs Dealer Upcards 2 through 11/Ace)
# Table in docs:
# 17+: All S
# 16-13: S vs 2-6, H vs 7-A
# 12: H vs 2-3, S vs 4-6, H vs 7-A
# 11: D vs 2-A
# 10: D vs 2-9, H vs 10, A
# 9: H vs 2, D vs 3-6, H vs 7-A
# 8: All H
HARD_TOTALS_MATRIX: dict[int, dict[int, Action]] = {
    17: {u: Action.STAND for u in range(2, 12)},
    16: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND, 6: Action.STAND, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    15: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND, 6: Action.STAND, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    14: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND, 6: Action.STAND, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    13: {2: Action.STAND, 3: Action.STAND, 4: Action.STAND, 5: Action.STAND, 6: Action.STAND, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    12: {2: Action.HIT, 3: Action.HIT, 4: Action.STAND, 5: Action.STAND, 6: Action.STAND, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    11: {u: Action.DOUBLE for u in range(2, 12)},
    10: {2: Action.DOUBLE, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.DOUBLE, 8: Action.DOUBLE, 9: Action.DOUBLE, 10: Action.HIT, 11: Action.HIT},
    9:  {2: Action.HIT, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    8:  {u: Action.HIT for u in range(2, 12)},
}

# 2. Soft Totals Matrix (A,2 through A,9 vs Dealer Upcards 2 through 11/Ace)
# Hand represented by non-Ace value (e.g., 9 for A,9 [soft 20], 8 for A,8 [soft 19], etc.)
# A,9: All S
# A,8: All S
# A,7: Ds vs 2-6, S vs 7-8, H vs 9-A
# A,6: H vs 2, D vs 3-6, H vs 7-A
# A,5: H vs 2-3, D vs 4-6, H vs 7-A
# A,4: H vs 2-3, D vs 4-6, H vs 7-A
# A,3: H vs 2-4, D vs 5-6, H vs 7-A
# A,2: H vs 2-4, D vs 5-6, H vs 7-A
SOFT_TOTALS_MATRIX: dict[int, dict[int, Any]] = {
    9: {u: Action.STAND for u in range(2, 12)},
    8: {u: Action.STAND for u in range(2, 12)},
    7: {2: "Ds", 3: "Ds", 4: "Ds", 5: "Ds", 6: "Ds", 7: Action.STAND, 8: Action.STAND, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    6: {2: Action.HIT, 3: Action.DOUBLE, 4: Action.DOUBLE, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    5: {2: Action.HIT, 3: Action.HIT, 4: Action.DOUBLE, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    4: {2: Action.HIT, 3: Action.HIT, 4: Action.DOUBLE, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    3: {2: Action.HIT, 3: Action.HIT, 4: Action.HIT, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
    2: {2: Action.HIT, 3: Action.HIT, 4: Action.HIT, 5: Action.DOUBLE, 6: Action.DOUBLE, 7: Action.HIT, 8: Action.HIT, 9: Action.HIT, 10: Action.HIT, 11: Action.HIT},
}

# 3. Pair Splitting Matrix (Pairs 2,2 to A,A vs Dealer Upcards 2 through 11/Ace)
# Table in docs:
# A,A: All Y
# T,T: All N
# 9,9: Y vs 2-6, N vs 7, Y vs 8-9, N vs 10, A
# 8,8: Y vs 2-9, N vs 10, A
# 7,7: Y vs 2-7, N vs 8-A
# 6,6: Y/N vs 2, Y vs 3-6, N vs 7-A
# 5,5: All N
# 4,4: N vs 2-4, Y/N vs 5-6, N vs 7-A
# 3,3: Y/N vs 2-3, Y vs 4-7, N vs 8-A
# 2,2: Y/N vs 2-3, Y vs 4-7, N vs 8-A
PAIR_SPLITTING_MATRIX: dict[Rank, dict[int, str]] = {
    Rank.ACE:   {u: "Y" for u in range(2, 12)},
    Rank.KING:  {u: "N" for u in range(2, 12)},
    Rank.QUEEN: {u: "N" for u in range(2, 12)},
    Rank.JACK:  {u: "N" for u in range(2, 12)},
    Rank.TEN:   {u: "N" for u in range(2, 12)},
    Rank.NINE:  {2: "Y", 3: "Y", 4: "Y", 5: "Y", 6: "Y", 7: "N", 8: "Y", 9: "Y", 10: "N", 11: "N"},
    Rank.EIGHT: {2: "Y", 3: "Y", 4: "Y", 5: "Y", 6: "Y", 7: "Y", 8: "Y", 9: "Y", 10: "N", 11: "N"},
    Rank.SEVEN: {2: "Y", 3: "Y", 4: "Y", 5: "Y", 6: "Y", 7: "Y", 8: "N", 9: "N", 10: "N", 11: "N"},
    Rank.SIX:   {2: "Y/N", 3: "Y", 4: "Y", 5: "Y", 6: "Y", 7: "N", 8: "N", 9: "N", 10: "N", 11: "N"},
    Rank.FIVE:  {u: "N" for u in range(2, 12)},
    Rank.FOUR:  {2: "N", 3: "N", 4: "N", 5: "Y/N", 6: "Y/N", 7: "N", 8: "N", 9: "N", 10: "N", 11: "N"},
    Rank.THREE: {2: "Y/N", 3: "Y/N", 4: "Y", 5: "Y", 6: "Y", 7: "Y", 8: "N", 9: "N", 10: "N", 11: "N"},
    Rank.TWO:   {2: "Y/N", 3: "Y/N", 4: "Y", 5: "Y", 6: "Y", 7: "Y", 8: "N", 9: "N", 10: "N", 11: "N"},
}

# 4. Surrender Matrix (16 vs 9,10,A; 15 vs 10)
SURRENDER_MATRIX: dict[int, dict[int, Action | None]] = {
    16: {u: (Action.SURRENDER if u in (9, 10, 11) else None) for u in range(2, 12)},
    15: {u: (Action.SURRENDER if u == 10 else None) for u in range(2, 12)},
}


def get_dealer_upcard_value(dealer_upcard: Card | None) -> int:
    """Return dealer nominal upcard value (2-10, Ace is 11)."""
    if dealer_upcard is None:
        return 10
    if dealer_upcard.is_ace:
        return 11
    return dealer_upcard.nominal_value


def get_optimal_action(
    player_cards: list[Card],
    player_total: int,
    is_soft: bool,
    dealer_upcard: Card | None,
    legal_actions: list[Action],
    rules: TableRules | None = None,
) -> tuple[Action, str]:
    """Resolve the game-theoretically optimal action strictly adhering to docs/Estrategia Optima.md."""
    dealer_val = get_dealer_upcard_value(dealer_upcard)
    legal = set(legal_actions)
    active_rules = rules if rules is not None else TableRules()

    # Step 1: Surrender Check (2-card hand only, when surrender is legal)
    if len(player_cards) == 2 and not is_soft and Action.SURRENDER in legal:
        if player_total in SURRENDER_MATRIX:
            surr_action = SURRENDER_MATRIX[player_total].get(dealer_val)
            if surr_action == Action.SURRENDER:
                return Action.SURRENDER, f"Surrender {player_total} vs dealer {dealer_val}"

    # Step 2: Pair Splitting Check (2 cards of same rank or 10-value)
    if len(player_cards) == 2 and Action.SPLIT in legal:
        card1, card2 = player_cards[0], player_cards[1]
        is_pair = (card1.rank == card2.rank) or (card1.nominal_value == card2.nominal_value == 10)
        if is_pair:
            pair_rank = card1.rank
            # Normalize 10-value cards (10, J, Q, K) to TEN for lookup
            if pair_rank in (Rank.JACK, Rank.QUEEN, Rank.KING):
                pair_rank = Rank.TEN

            split_code = PAIR_SPLITTING_MATRIX.get(pair_rank, {}).get(dealer_val, "N")
            if split_code == "Y":
                return Action.SPLIT, f"Split pair of {pair_rank.name}s vs dealer {dealer_val}"
            elif split_code == "Y/N":
                # Split only if Double After Split (DAS) is allowed
                if active_rules.double_after_split:
                    return Action.SPLIT, f"Split pair of {pair_rank.name}s with DAS vs dealer {dealer_val}"
                # If DAS is false, do not split -> proceed to soft/hard total evaluation below

    # Step 3: Soft Totals Check
    if is_soft and player_total <= 21:
        # Determine soft non-ace value: (player_total - 11)
        non_ace_val = player_total - 11
        if non_ace_val in SOFT_TOTALS_MATRIX:
            soft_entry = SOFT_TOTALS_MATRIX[non_ace_val].get(dealer_val, Action.STAND)
            if soft_entry == "Ds":
                if Action.DOUBLE in legal:
                    return Action.DOUBLE, f"Double soft {player_total} vs dealer {dealer_val} (Ds)"
                return Action.STAND, f"Stand on soft {player_total} vs dealer {dealer_val} (Ds fallback)"
            elif soft_entry == Action.DOUBLE:
                if Action.DOUBLE in legal:
                    return Action.DOUBLE, f"Double soft {player_total} vs dealer {dealer_val}"
                return Action.HIT, f"Hit soft {player_total} vs dealer {dealer_val} (D fallback)"
            elif soft_entry == Action.STAND:
                return Action.STAND, f"Stand on soft {player_total}"
            elif soft_entry == Action.HIT:
                return Action.HIT, f"Hit soft {player_total}"

        if player_total >= 19:
            return Action.STAND, f"Stand on soft {player_total}"

    # Step 4: Hard Totals Check
    if player_total >= 17:
        return Action.STAND, f"Stand on hard {player_total}"
    elif player_total in HARD_TOTALS_MATRIX:
        hard_entry = HARD_TOTALS_MATRIX[player_total].get(dealer_val, Action.HIT)
        if hard_entry == Action.DOUBLE:
            if Action.DOUBLE in legal:
                return Action.DOUBLE, f"Double hard {player_total} vs dealer {dealer_val}"
            return Action.HIT, f"Hit hard {player_total} vs dealer {dealer_val} (D fallback)"
        elif hard_entry == Action.STAND:
            return Action.STAND, f"Stand on hard {player_total} vs dealer {dealer_val}"
        elif hard_entry == Action.HIT:
            return Action.HIT, f"Hit hard {player_total} vs dealer {dealer_val}"

    # 8 or below -> Hit
    return Action.HIT, f"Hit hard {player_total}"
