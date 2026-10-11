"""Mathematical Blackjack Basic Strategy decision provider.

Re-exports BasicStrategyPlayer from app.models for backward compatibility.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.basic_strategy_player import BasicStrategyPlayer

def __getattr__(name: str):
    if name in ("BasicStrategyAgent", "BasicStrategyPlayer"):
        from app.models.basic_strategy_player import BasicStrategyPlayer
        return BasicStrategyPlayer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["BasicStrategyAgent", "BasicStrategyPlayer"]
