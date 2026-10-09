"""Blackjack rules engine package.

Strictly deterministic and decoupled from UI, network protocols, or persistence.
Responsible for:
- Shoe creation, shuffling, cutting, and burning
- Dealing and hand evaluations
- Ace softness resolution (Hard vs Soft totals)
- Natural Blackjack detection
- Dealer rules (Stand on 17 / Hit Soft 17)
- Payout settlements and bankroll calculations
"""
