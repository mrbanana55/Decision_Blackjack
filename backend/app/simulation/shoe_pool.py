"""Generational shoe repository managing multi-table shoe lifecycles."""

import copy
from app.engine.shoe import Shoe


class ShoePool:
    """Session-level repository maintaining deterministic shoe generations across tables.
    
    When a table reaches the cut-card threshold and finishes its round, it checks the pool
    for the next shoe generation. If another table already generated and saved it, the table
    adopts a clone of that generation. If not, the pool deterministically generates, saves,
    and returns it.
    """

    def __init__(
        self,
        base_seed: int,
        num_decks: int = 6,
        penetration: float = 0.75,
    ) -> None:
        self.base_seed: int = base_seed
        self.num_decks: int = num_decks
        self.penetration: float = penetration
        self.generation_cache: dict[int, Shoe] = {}

    def derive_seed(self, generation: int) -> int:
        """Derive deterministic seed for a shoe generation."""
        return self.base_seed + (generation * 1000)

    def has_generation(self, generation: int) -> bool:
        """Check if a shoe generation has already been generated and saved."""
        return generation in self.generation_cache

    def get_shoe_for_generation(self, generation: int) -> Shoe:
        """Retrieve a pristine shoe for the specified generation, creating it if not cached.
        
        Returns a fresh clone of the generation shoe to ensure independent card dealing
        without cross-table contamination while maintaining identical initial card order.
        """
        if generation not in self.generation_cache:
            seed = self.derive_seed(generation)
            shoe = Shoe(
                num_decks=self.num_decks,
                seed=seed,
                penetration=self.penetration,
            )
            self.generation_cache[generation] = shoe

        # Return a pristine deepcopy for the requesting table
        return copy.deepcopy(self.generation_cache[generation])

    def clear(self) -> None:
        """Clear cached shoe generations."""
        self.generation_cache.clear()
