"""Tests for 100% matrix adherence to docs/Estrategia Optima.md."""

from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.strategy_matrices import (
    HARD_TOTALS_MATRIX,
    PAIR_SPLITTING_MATRIX,
    SOFT_TOTALS_MATRIX,
    SURRENDER_MATRIX,
    get_optimal_action,
)


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.SPADES, rank=rank)


def test_hard_totals_matrix_cell_completeness():
    """Verify all 100 cells of Hard Totals (totals 8 through 17 vs dealer upcards 2 through 11)."""
    assert len(HARD_TOTALS_MATRIX) == 10
    dealer_upcards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    for total in range(8, 18):
        assert total in HARD_TOTALS_MATRIX
        row = HARD_TOTALS_MATRIX[total]
        for upcard in dealer_upcards:
            assert upcard in row, f"Missing cell for total {total} vs dealer {upcard}"

    # Specific sample cell verification from docs/Estrategia Optima.md
    assert HARD_TOTALS_MATRIX[17][2] == Action.STAND
    assert HARD_TOTALS_MATRIX[16][6] == Action.STAND
    assert HARD_TOTALS_MATRIX[16][7] == Action.HIT
    assert HARD_TOTALS_MATRIX[12][2] == Action.HIT
    assert HARD_TOTALS_MATRIX[12][4] == Action.STAND
    assert HARD_TOTALS_MATRIX[11][2] == Action.DOUBLE
    assert HARD_TOTALS_MATRIX[11][11] == Action.DOUBLE
    assert HARD_TOTALS_MATRIX[10][9] == Action.DOUBLE
    assert HARD_TOTALS_MATRIX[10][10] == Action.HIT
    assert HARD_TOTALS_MATRIX[9][2] == Action.HIT
    assert HARD_TOTALS_MATRIX[9][3] == Action.DOUBLE
    assert HARD_TOTALS_MATRIX[8][5] == Action.HIT


def test_soft_totals_matrix_cell_completeness():
    """Verify all 80 cells of Soft Totals (A,2 through A,9 vs dealer upcards 2 through 11)."""
    assert len(SOFT_TOTALS_MATRIX) == 8
    dealer_upcards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    for other_card in range(2, 10):
        assert other_card in SOFT_TOTALS_MATRIX
        row = SOFT_TOTALS_MATRIX[other_card]
        for upcard in dealer_upcards:
            assert upcard in row, f"Missing soft total A,{other_card} vs dealer {upcard}"

    # Specific sample cell verification from docs/Estrategia Optima.md
    assert SOFT_TOTALS_MATRIX[9][2] == Action.STAND
    assert SOFT_TOTALS_MATRIX[8][11] == Action.STAND
    # A,7: Ds vs 2-6, S vs 7-8, H vs 9-A
    assert SOFT_TOTALS_MATRIX[7][2] == "Ds"
    assert SOFT_TOTALS_MATRIX[7][6] == "Ds"
    assert SOFT_TOTALS_MATRIX[7][7] == Action.STAND
    assert SOFT_TOTALS_MATRIX[7][9] == Action.HIT
    # A,6: H vs 2, D vs 3-6, H vs 7-A
    assert SOFT_TOTALS_MATRIX[6][2] == Action.HIT
    assert SOFT_TOTALS_MATRIX[6][3] == Action.DOUBLE
    assert SOFT_TOTALS_MATRIX[6][6] == Action.DOUBLE
    assert SOFT_TOTALS_MATRIX[6][7] == Action.HIT
    # A,2 and A,3: H vs 2-4, D vs 5-6, H vs 7-A
    assert SOFT_TOTALS_MATRIX[2][4] == Action.HIT
    assert SOFT_TOTALS_MATRIX[2][5] == Action.DOUBLE
    assert SOFT_TOTALS_MATRIX[3][6] == Action.DOUBLE
    assert SOFT_TOTALS_MATRIX[3][7] == Action.HIT


def test_pair_splitting_matrix_cell_completeness():
    """Verify all cells of Pair Splitting (pairs 2,2 to A,A vs dealer upcards 2 through 11)."""
    assert len(PAIR_SPLITTING_MATRIX) == 13
    dealer_upcards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    ranks = [
        Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
        Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE
    ]

    for rank in ranks:
        assert rank in PAIR_SPLITTING_MATRIX
        row = PAIR_SPLITTING_MATRIX[rank]
        for upcard in dealer_upcards:
            assert upcard in row, f"Missing pair cell for {rank} vs dealer {upcard}"

    # Specific sample cell verification
    # A,A & 8,8: Always Y
    assert all(PAIR_SPLITTING_MATRIX[Rank.ACE][u] == "Y" for u in dealer_upcards)
    assert all(PAIR_SPLITTING_MATRIX[Rank.EIGHT][u] == "Y" for u in [2, 3, 4, 5, 6, 7, 8, 9])
    assert PAIR_SPLITTING_MATRIX[Rank.EIGHT][10] == "N"  # In docs: 8,8 vs 10, A is N
    assert PAIR_SPLITTING_MATRIX[Rank.EIGHT][11] == "N"
    # T,T & 5,5: Always N
    assert all(PAIR_SPLITTING_MATRIX[Rank.TEN][u] == "N" for u in dealer_upcards)
    assert all(PAIR_SPLITTING_MATRIX[Rank.FIVE][u] == "N" for u in dealer_upcards)
    # 9,9: Y vs 2-6, 8-9; N vs 7, 10, A
    assert PAIR_SPLITTING_MATRIX[Rank.NINE][2] == "Y"
    assert PAIR_SPLITTING_MATRIX[Rank.NINE][7] == "N"
    assert PAIR_SPLITTING_MATRIX[Rank.NINE][8] == "Y"
    assert PAIR_SPLITTING_MATRIX[Rank.NINE][10] == "N"
    # 6,6: Y/N vs 2; Y vs 3-6; N vs 7-A
    assert PAIR_SPLITTING_MATRIX[Rank.SIX][2] == "Y/N"
    assert PAIR_SPLITTING_MATRIX[Rank.SIX][3] == "Y"
    assert PAIR_SPLITTING_MATRIX[Rank.SIX][7] == "N"
    # 4,4: Y/N vs 5-6; N otherwise
    assert PAIR_SPLITTING_MATRIX[Rank.FOUR][4] == "N"
    assert PAIR_SPLITTING_MATRIX[Rank.FOUR][5] == "Y/N"
    # 2,2 and 3,3: Y/N vs 2-3; Y vs 4-7; N vs 8-A
    assert PAIR_SPLITTING_MATRIX[Rank.TWO][2] == "Y/N"
    assert PAIR_SPLITTING_MATRIX[Rank.TWO][4] == "Y"
    assert PAIR_SPLITTING_MATRIX[Rank.TWO][8] == "N"


def test_surrender_matrix_and_application():
    """Verify Surrender cells and fallback."""
    # 16 vs 9, 10, A
    assert SURRENDER_MATRIX[16][9] == Action.SURRENDER
    assert SURRENDER_MATRIX[16][10] == Action.SURRENDER
    assert SURRENDER_MATRIX[16][11] == Action.SURRENDER
    # 15 vs 10
    assert SURRENDER_MATRIX[15][10] == Action.SURRENDER
    assert SURRENDER_MATRIX[15][9] is None

    rules = TableRules(surrender_rule="late")
    # When surrender is legal
    act, reason = get_optimal_action(
        player_cards=[_card(Rank.TEN), _card(Rank.SIX)],
        player_total=16,
        is_soft=False,
        dealer_upcard=_card(Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SURRENDER],
        rules=rules,
    )
    assert act == Action.SURRENDER

    # When surrender is NOT legal, fallback to Hit
    act_no_surr, _ = get_optimal_action(
        player_cards=[_card(Rank.TEN), _card(Rank.SIX)],
        player_total=16,
        is_soft=False,
        dealer_upcard=_card(Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND],
        rules=rules,
    )
    assert act_no_surr == Action.HIT


def test_das_pair_splitting_resolution():
    """Verify conditional Y/N pair splitting respecting TableRules.double_after_split."""
    # 6,6 vs dealer 2 is Y/N
    cards = [_card(Rank.SIX), _card(Rank.SIX)]
    upcard = _card(Rank.TWO)

    # With DAS=True -> Split
    act_das, _ = get_optimal_action(
        player_cards=cards,
        player_total=12,
        is_soft=False,
        dealer_upcard=upcard,
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
        rules=TableRules(double_after_split=True),
    )
    assert act_das == Action.SPLIT

    # With DAS=False -> Do not split; evaluate as hard 12 vs 2 -> Hit
    act_no_das, _ = get_optimal_action(
        player_cards=cards,
        player_total=12,
        is_soft=False,
        dealer_upcard=upcard,
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
        rules=TableRules(double_after_split=False),
    )
    assert act_no_das == Action.HIT


def test_soft_totals_ds_fallback():
    """Verify A,7 (soft 18) vs dealer 3: Ds -> Double if legal, else Stand."""
    cards = [_card(Rank.ACE), _card(Rank.SEVEN)]
    upcard = _card(Rank.THREE)

    # When Double is legal -> Double
    act_dbl, _ = get_optimal_action(
        player_cards=cards,
        player_total=18,
        is_soft=True,
        dealer_upcard=upcard,
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
        rules=TableRules(),
    )
    assert act_dbl == Action.DOUBLE

    # When Double is not legal (e.g. 3-card hand) -> Stand
    act_stand, _ = get_optimal_action(
        player_cards=[_card(Rank.ACE), _card(Rank.FIVE), _card(Rank.TWO)],
        player_total=18,
        is_soft=True,
        dealer_upcard=upcard,
        legal_actions=[Action.HIT, Action.STAND],
        rules=TableRules(),
    )
    assert act_stand == Action.STAND


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All strategy matrix tests passed!")
