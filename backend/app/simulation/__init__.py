"""Multi-table simulation orchestration package.

Coordinates turn-by-turn and round-by-round execution across:
1. Jev table (Remote System One AI)
2. Laya table (Local model)
3. Optimal Strategy table (Mathematical baseline)

Enforces experiment synchronization, identical starting shoe seeds, and synchronized pauses.
"""
