# WebSocket Protocol & Telemetry Contract

**Feature**: `008-frontend-web-application`  
**Endpoint**: `ws://localhost:8000/ws/simulations/{session_id}`  

---

## 1. Client Frame Listener Mapping

| Inbound Event | Trigger Condition | Frontend UI Reaction |
|:---|:---|:---|
| `SESSION_SNAPSHOT` | Handshake connection established | Hydrates simulation config, active players, initial table bankrolls. Starts round loop. |
| `ROUND_STARTED` | New round initiated | Increments round counter; clears dealer/player hands; resets action badges. |
| `BET_PLACED` | Entity places opening bet | Updates `current_bet` in player stats; deducts bet from local bankroll counter. |
| `CARD_DEALT` | Initial deal or hit action | Triggers GSAP card deal animation into player or dealer hand. Rotates card 90° if action was Double Down. |
| `DECISION_MADE` | In-hand player action applied | Updates `Action: [ACTION]` badge, confidence metric, and basic strategy comparison. |
| `ROUND_SETTLED` | Dealer finishes and hands settle | Updates bankroll delta (`+$X` / `-$X`), increments win/loss/push counts, and recalculates the 3 dynamic graph bars. |
| `SESSION_PAUSED` | User or system pauses simulation | Sets UI status to `PAUSED`; updates button icon to Play. |
| `SESSION_RESUMED` | Simulation resumes execution | Sets UI status to `RUNNING`; updates button icon to Pause. |
| `SESSION_ERROR` | External AI fault / timeout (RNF-02) | Pauses visualizer; opens `FaultAlertModal` with simple error message and Retry button if recoverable. |
| `SESSION_COMPLETED` | Max rounds or all bankrupt reached | Navigates to `/complete/:sessionId` displaying completion dialog with Tri-Player summary table. |
| `SPEED_UPDATED` | Playback speed updated | Updates slider thumb position and animation pacing duration. |

---

## 2. Client Outbound Commands

```typescript
export type OutboundCommand =
  | { command: 'pause' }
  | { command: 'resume' }
  | { command: 'step'; level?: 'round' | 'turn' }
  | { command: 'retry'; entity_id?: string }
  | { command: 'stop' }
  | { command: 'set_speed'; delay_ms: number };
```
