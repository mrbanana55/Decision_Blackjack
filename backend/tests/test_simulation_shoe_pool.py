"""Unit tests for ShoePool generational shoe repository."""

from app.simulation.shoe_pool import ShoePool


def test_seed_derivation():
    pool = ShoePool(base_seed=42, num_decks=6, penetration=0.75)
    assert pool.derive_seed(0) == 42
    assert pool.derive_seed(1) == 1042
    assert pool.derive_seed(2) == 2042
    assert pool.derive_seed(5) == 5042


def test_generation_caching_and_reuse():
    pool = ShoePool(base_seed=123, num_decks=6, penetration=0.75)

    assert not pool.has_generation(0)
    assert not pool.has_generation(1)

    # First table requests generation 0
    shoe_a0 = pool.get_shoe_for_generation(0)
    assert pool.has_generation(0)
    assert len(pool.generation_cache) == 1

    # Second table requests generation 0 (should use cached generation)
    shoe_b0 = pool.get_shoe_for_generation(0)
    assert pool.has_generation(0)
    assert len(pool.generation_cache) == 1

    # Both tables must have identical card sequences
    cards_a = [c for c in shoe_a0.cards]
    cards_b = [c for c in shoe_b0.cards]
    assert cards_a == cards_b


def test_isolation_between_tables():
    pool = ShoePool(base_seed=999, num_decks=6, penetration=0.75)

    shoe_a = pool.get_shoe_for_generation(0)
    shoe_b = pool.get_shoe_for_generation(0)

    # Deal 20 cards from Table A
    dealt_from_a = [shoe_a.deal() for _ in range(20)]
    assert shoe_a.cards_remaining == shoe_b.cards_remaining - 20

    # Table B's shoe remains pristine and unaffected
    dealt_from_b = [shoe_b.deal() for _ in range(20)]
    assert dealt_from_a == dealt_from_b

    # Cached template remains pristine
    cached_shoe = pool.generation_cache[0]
    assert len(cached_shoe.cards) == 6 * 52


def test_different_generations_have_different_cards():
    pool = ShoePool(base_seed=777, num_decks=6, penetration=0.75)

    shoe_gen0 = pool.get_shoe_for_generation(0)
    shoe_gen1 = pool.get_shoe_for_generation(1)

    assert pool.has_generation(0)
    assert pool.has_generation(1)
    assert len(pool.generation_cache) == 2

    cards_0 = [c for c in shoe_gen0.cards]
    cards_1 = [c for c in shoe_gen1.cards]
    assert cards_0 != cards_1


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All shoe pool tests passed!")
