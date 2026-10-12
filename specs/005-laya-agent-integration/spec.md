# Feature Specification: Laya Decision Agent Integration & Container Host Bridge

**Feature Branch**: `005-laya-agent-integration`

**Created**: 2026-10-11

**Status**: Ready for Planning

**Input**: User description: "Let's make the Laya integration. Right now i have a laya server running in http://0.0.0.0:1234, you can make curl http://127.0.0.1:8000/health to check it. The idea here is that the orchestrator gives stuff like the cards, bankroll, etc. And we need to make the corresponding petitions to make laya take decisions on each game phase. Consider that right now Laya is running locally on my computer without a docker container, so you might need to do some tweaks inside the backend container in order to be able to communicate with laya. Laya expects the same json like JEV does"

## Clarifications

### Session 2026-10-11

- **Opening Bet Sizing (FR-006)**: Discrete System One Choice Query (Option B). At the start of each round, the orchestrator queries Laya via a TypeSafe System One Choice question with discrete bet options (e.g. `1x`, `2x`, `4x`, `8x` table minimum bet units, bounded by current bankroll and table maximum), formatted per [`docs/Laya_Example_Body.md`](file:///Users/andresdelgado/Documents/Coding/Decision_Blackjack/docs/Laya_Example_Body.md).
- **Insurance Phase Handling (FR-007)**: Query Laya via System One Choice (Option B). When the dealer's upcard is an Ace, the orchestrator queries Laya via a Choice question with `accept` and `decline` criteria, applying the chosen insurance action to the table.
- **Connectivity Failure Recovery (FR-008)**: Strict Pause with State Preservation (Option A / RNF-02). If the local Laya server times out, drops connection, or returns an HTTP error, all synchronized tables pause immediately, current game state and persistence telemetry are preserved, and an alert is emitted allowing the user to Retry or Abort.
- **Dynamic Endpoint Configuration (FR-002)**: Laya server endpoint is loaded dynamically from `LAYA_BASE_URL` in the `.env` file, allowing host and port reconfiguration without code changes or container image rebuilds.

---

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Real-Time Hand Action Decisions via Local Laya Model (Priority: P1)

As a simulation runner or researcher, I want the simulation orchestrator to query the locally hosted Laya model for all playing actions (Hit, Stand, Double, Split, Surrender) during each hand turn, so that Laya acts as an autonomous AI decision-maker competing under identical shoe conditions alongside other entities.

**Why this priority**: Core value of the feature. Replacing simulated mock responses with real inferences from the locally running Laya model enables empirical evaluation of local deep learning policies against game theory and cloud AI.

**Independent Test**: Can be tested independently by creating a simulation session with the Laya entity, stepping through active hands, and verifying that the action taken at each player turn matches the discrete decision, confidence rating, and metadata returned by the local Laya server.

**Acceptance Scenarios**:

1. **Given** a player hand with legal actions (e.g. Hit, Stand, Double), **When** Laya's turn arrives in the hand play phase, **Then** the orchestrator formats the observable table context (player cards, total, dealer upcard, legal actions, bankroll) into the decision request, transmits it to the local Laya endpoint (`/v1/systemone`), receives a valid action choice, and applies that action to the table hand.
2. **Given** a scenario where split or surrender is legally available (e.g., pair of 8s or 16 vs 10), **When** Laya's decision is requested, **Then** the choices provided to Laya include the legal split or surrender options, and the orchestrator executes the chosen action if selected.
3. **Given** a completed inference turn, **When** the decision is applied, **Then** inference latency, model confidence, and response metadata are attached to telemetry events and persisted to the database.

---

### User Story 2 - Host-Container Network Bridge & Health Connectivity (Priority: P1)

As an engineer or developer running the backend inside Docker while Laya runs natively on the host machine, I want the backend container to dynamically resolve Laya's location from `LAYA_BASE_URL` in the `.env` file across any configured host port, so that network isolation does not prevent communication and changing ports in `.env` works without code modifications.

**Why this priority**: P1 blocker. Without container-to-host bridge routing and flexible environment configuration, any request from the container to host-bound services fails, and hardcoded ports prevent changing ports in future setups.

**Independent Test**: Can be tested independently by changing `LAYA_BASE_URL` in `.env` (or environment), triggering a health probe from inside the backend container against the configured endpoint, and receiving a 200 OK response with model status details.

**Acceptance Scenarios**:

1. **Given** the backend container running in Docker Compose and `LAYA_BASE_URL` set in `.env` (e.g. `http://127.0.0.1:1234` or custom port), **When** the backend initiates an HTTP request, **Then** the request routes through the host bridge to the host machine's designated port without connection timeouts or connection refused errors.
2. **Given** a startup connectivity or health verification check, **When** probing the endpoint at `<LAYA_BASE_URL>/health`, **Then** the service reports readiness (`status: ok`) and active model checkpoint revisions.
3. **Given** `LAYA_BASE_URL` updated in `.env` to a different port or hostname, **When** restarting the backend, **Then** the backend immediately adopts the new URL from the environment without code alterations or hardcoded assumptions.

---

### User Story 3 - Multi-Phase Game Decisions: Discrete Bet Sizing & Insurance (Priority: P2)

As a researcher benchmarking AI risk management, I want the simulation orchestrator to consult Laya during all game phases requiring decision-making (including discrete round wagering and insurance offers), so that Laya's bankroll management and risk preferences are fully evaluated across complete rounds.

**Why this priority**: Essential for full round autonomy. A complete blackjack agent must decide how much to risk per round and whether to protect against dealer blackjacks, not just hit or stand.

**Independent Test**: Can be tested independently by running rounds where the dealer shows an Ace (insurance phase) and observing round-opening bet selections, verifying that Laya's choices follow the configured TypeSafe System One Choice contract.

**Acceptance Scenarios**:

1. **Given** the start of a new round with available bankroll and table minimum rules, **When** determining the opening wager for Laya's table, **Then** the orchestrator sends a Choice question with discrete bet multipliers (`1x`, `2x`, `4x`, `8x` units) bounded by bankroll, and wagers the amount selected by Laya.
2. **Given** the dealer's visible upcard is an Ace, **When** insurance is offered to the table, **Then** the orchestrator queries Laya with a Choice question (`accept` vs `decline`), resolving the side bet according to Laya's response.
3. **Given** an opening wager or insurance decision, **When** applied, **Then** bankroll balances and transactions are updated accurately in table state and persistence logs.

---

### User Story 4 - Fault Resilience, Session Preservation & Comparative Analysis (Priority: P2)

As a simulation controller, I want the system to handle local Laya server latency spikes, HTTP faults, or connection drops gracefully by pausing all tables and preserving collected data, so that transient host issues do not corrupt the multi-agent experiment.

**Why this priority**: Fulfills Constitution Principle II, Principle III, and RNF-02. In a synchronized 3-entity experiment, one failing agent must not crash the other tables or cause unrecorded state loss.

**Independent Test**: Can be tested independently by simulating a dropped connection or server error during an active simulation run, verifying that the session transitions to paused error state with full telemetry preserved, allowing retry or abort.

**Acceptance Scenarios**:

1. **Given** an active synchronized multi-entity simulation, **When** Laya fails to respond within the configured timeout or returns an HTTP 5xx error, **Then** the orchestrator pauses all active tables synchronously, preserves state, and emits an error notification (`SESSION_PAUSED`).
2. **Given** a paused simulation due to a temporary Laya failure, **When** the operator resolves the issue and issues a resume command, **Then** the orchestrator retries the pending decision and resumes game flow seamlessly.
3. **Given** successful Laya decisions, **When** applied to the table, **Then** the decision comparison service evaluates Laya's choice against basic strategy to record deviations and benchmark metrics.

---

### Edge Cases

- **Host Bridge Unreachable**: What happens if Docker Desktop's host resolution is disabled? The system must detect connection refusal immediately, mark Laya as unreachable with a clear diagnostic message, and offer configuration override options rather than hanging indefinitely.
- **Malformed Model Output**: What happens if Laya returns a response missing the chosen action or containing invalid JSON? The system must capture the raw payload for audit debugging, log a validation error, and raise an agent fault rather than executing an undefined action.
- **Illegal Action Returned**: What happens if Laya selects an action that is not in the legal actions list (e.g. Double on a 3-card hand)? The system must catch the illegal action, prevent invalid table state mutation, and follow the configured recovery policy (fault pause).
- **Resource Exhaustion on Host**: What happens if local GPU/MPS inference on the host causes high latency (e.g. > 5 seconds)? The request timeout must be bounded and configurable to prevent deadlocking orchestrator loops.
- **Table Reshuffle Crossing**: What happens when the shoe reshuffles between rounds? Laya's context state must reflect the fresh shoe generation and reset cards-seen/count tracking.

---

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a dedicated decision provider client (`LayaAgent`) that communicates with the local Laya server over HTTP using the standardized JSON payload schema matching TypeSafe System One per [`docs/Laya_Example_Body.md`](file:///Users/andresdelgado/Documents/Coding/Decision_Blackjack/docs/Laya_Example_Body.md).
- **FR-002**: System MUST read Laya's endpoint dynamically from `LAYA_BASE_URL` defined in `.env` (propagated to the backend container via Docker Compose with host bridge routing, e.g. mapping `127.0.0.1` / `localhost` to `host.docker.internal` inside the container), allowing the user to change the port or host in `.env` at any time without code changes.
- **FR-003**: System MUST provide a health check probe for Laya that verifies service availability (`/health`), active device mode (e.g., MPS/CPU), and loaded model checkpoints before initiating or during simulations.
- **FR-004**: System MUST employ situation-specific question schemas that dynamically generate the `state` description, instructions, and `criteria` options according to the player's exact tactical situation (e.g., initial hand with pair split opportunity, initial hand with double/surrender, multi-card post-hit draw, insurance offer, and round opening wager).
- **FR-005**: System MUST parse Laya's JSON response to extract the chosen action, confidence score, inference latency, and response metadata, mapping them to the domain `AgentDecision`.
- **FR-006**: System MUST query Laya before each round deal using a TypeSafe System One Choice question to select an initial wager amount from discrete bet options (e.g. `1x`, `2x`, `4x`, `8x` units of table minimum bet bounded by available bankroll), parsing the chosen option into a concrete currency bet.
- **FR-007**: System MUST query Laya during the insurance phase (when dealer upcard is an Ace) using a TypeSafe System One Choice question with `accept` and `decline` criteria, applying the chosen insurance decision to the table.
- **FR-008**: System MUST handle connection timeouts and unreachable server scenarios by strictly pausing all synchronized tables, preserving collected state and telemetry without data loss (RNF-02 compliance), and offering Retry and Abort control actions.
- **FR-009**: System MUST attach Laya's inference telemetry (latency, confidence, model revision, and decision metadata) to all emitted simulation events and persist them in the database (`decisions` and `model_responses` tables) and run archives.
- **FR-010**: System MUST evaluate Laya's decisions against the mathematical Basic Strategy comparator in real-time, recording optimal vs sub-optimal flags and expected-value deviations.

---

### Technical Data Contract (Situation-Specific Schemas)

Per [`docs/Laya_Example_Body.md`](file:///Users/andresdelgado/Documents/Coding/Decision_Blackjack/docs/Laya_Example_Body.md), all petitions sent to Laya follow TypeSafe System One conventions.

The system formats distinct question schemas tailored to the player's exact in-game situation:

#### Situation 1A: Initial Paired Hand (Split Eligible, Surrender Disabled)
When the player holds 2 cards of identical rank, bankroll $\ge$ bet, and surrender is disabled:
```json
{
  "state": "Hand 1: [8 of Spades, 8 of Diamonds] (Pair of 8s, Total: 16). Dealer Upcard: 7 of Hearts. Bankroll: $1,000. True Count: +0.5. Legal actions: hit, stand, split. Surrender: Disabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of 8s into two independent hands with matching wager"
      }
    }
  }
}
```

#### Situation 1B: Initial Paired Hand (Split Eligible, Surrender Enabled)
When the player holds 2 cards of identical rank, bankroll $\ge$ bet, and late surrender is enabled:
```json
{
  "state": "Hand 1: [8 of Spades, 8 of Diamonds] (Pair of 8s, Total: 16). Dealer Upcard: 10 of Clubs. Bankroll: $1,000. True Count: +0.0. Legal actions: hit, stand, split, surrender. Surrender: Enabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of 8s into two independent hands with matching wager",
        "surrender": "Forfeit half the initial wager and retire the hand"
      }
    }
  }
}
```

#### Situation 2A: Initial Standard Hand (Double Eligible, Surrender Disabled, No Split)
When the player holds 2 non-matching cards, bankroll $\ge$ bet, and surrender is disabled:
```json
{
  "state": "Hand 1: [5 of Diamonds, 6 of Clubs] (Total: 11, Hard). Dealer Upcard: 6 of Spades. Bankroll: $1,000. True Count: +2.0. Legal actions: hit, stand, double. Surrender: Disabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager, take exactly one card, and stand"
      }
    }
  }
}
```

#### Situation 2B: Initial Standard Hand (Double & Surrender Enabled, No Split)
When the player holds 2 non-matching cards (e.g. 10+6 vs 10), bankroll $\ge$ bet, and late surrender is enabled:
```json
{
  "state": "Hand 1: [10 of Spades, 6 of Hearts] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $1,000. True Count: +1.0. Legal actions: hit, stand, double, surrender. Surrender: Enabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager, take exactly one card, and stand",
        "surrender": "Forfeit half the initial wager and retire the hand"
      }
    }
  }
}
```

#### Situation 3: Multi-Card Hand (Post-Hit / 3+ Cards)

Once the player has taken one or more hits, double, split, and surrender are prohibited by game rules. Only `hit` and `stand` are presented:

```json
{
  "state": "Hand 1: [10 of Spades, 3 of Hearts, 3 of Clubs] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $950. True Count: +1.5. Legal actions: hit, stand.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the multi-card hand given the dealer upcard and table state.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total"
      }
    }
  }
}
```

#### Situation 4: Insurance Phase (Dealer Upcard is Ace)

Before hand actions are played, if the dealer exposes an Ace:

```json
{
  "state": "Dealer shows Ace. Initial hand: [King of Spades, 7 of Diamonds]. Bankroll: $1,000. True Count: +3.0. Insurance wager cost: $25.",
  "questions": {
    "insurance": {
      "type": "choice",
      "instructions": "Decide whether to take insurance against a potential dealer Blackjack.",
      "criteria": {
        "accept": "Place insurance bet equal to half the initial wager",
        "decline": "Decline insurance side bet and proceed to hand play"
      }
    }
  }
}
```

#### Situation 5: Round Betting Phase (Pre-Deal Wager Sizing)

Before cards are dealt, Laya decides the round opening bet amount:

```json
{
  "state": "Round 14. Table Minimum Bet: $50. Current Bankroll: $1,250. Shoe True Count: +2.5. Cards Seen: 142/312.",
  "questions": {
    "bet_sizing": {
      "type": "choice",
      "instructions": "Select the opening wager level for the upcoming round given the shoe count and current bankroll.",
      "criteria": {
        "1x": "1 unit ($50) - Base minimum wager",
        "2x": "2 units ($100) - Moderate advantage wager",
        "4x": "4 units ($200) - Elevated count advantage wager",
        "8x": "8 units ($400) - High count maximum spread wager"
      }
    }
  }
}
```

---

### Criteria Definitions Glossary

- `hit`: "Request an additional card from the dealer" (active while player hand is not busted or standing)
- `stand`: "Conclude turn and maintain current hand total" (active on all active hands)
- `double`: "Double the initial wager, take exactly one card, and stand" (active only on 2-card hands when bankroll $\ge$ bet)
- `split`: "Separate pair of equal cards into two independent hands" (active only on 2-card paired hands when split limit not exceeded and bankroll $\ge$ bet)
- `surrender`: "Forfeit half the initial wager and retire the hand" (active only on initial 2-card hand before any hit/split/double when late surrender permitted)
- `accept` / `decline`: Insurance decision options when dealer upcard is Ace
- `1x`, `2x`, `4x`, `8x`: Discrete opening round wager multipliers of table minimum bet

---

### Key Entities _(include if feature involves data)_

- **LayaDecisionAdapter**: Client module encapsulating HTTP communication, serialization of `DecisionContext` into TypeSafe System One JSON, response deserialization, and error translation.
- **LayaModelMetadata**: Inferred model telemetry attributes including checkpoint revision, execution device (MPS/CPU/CUDA), inference duration, and confidence distribution.
- **LayaHostConfig**: Configuration entity defining the Laya base URL sourced from `LAYA_BASE_URL` in `.env`, request timeout thresholds, retry limits, and health probe intervals.

---

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of valid playing phase turns for the Laya entity successfully obtain decisions from the local model and execute without manual intervention.
- **SC-002**: Over 95% of local inference requests complete with an end-to-end round-trip latency under 300 ms on supported local hardware.
- **SC-003**: In the event of a simulated local server disconnect or shutdown, 100% of active sessions pause cleanly within 1 second without data loss or engine state corruption.
- **SC-004**: Zero crashes or unhandled exceptions occur in the backend container when communicating with the host-bound service during a 500-round automated simulation.
- **SC-005**: 100% of Laya decisions are cross-evaluated against the basic strategy comparator with accurate deviation telemetry recorded in run persistence.

---

## Assumptions

- **Host Availability**: The host machine has sufficient CPU/GPU/MPS memory to run the Laya inference server continuously alongside Docker containers without out-of-memory crashes.
- **Schema Compatibility**: Laya uses the identical TypeSafe System One request/response protocol (state context and discrete choice question with criteria and instructions) as JEV, matching [`docs/Laya_Example_Body.md`](file:///Users/andresdelgado/Documents/Coding/Decision_Blackjack/docs/Laya_Example_Body.md).
- **Port/Host Flexibility**: The port and host URL are fully dynamic and loaded from `LAYA_BASE_URL` in `.env`, allowing users to adjust ports without altering application code.
- **Network Protocol**: Communication between backend container and host Laya server uses standard HTTP/1.1 JSON without requiring mTLS or API token authentication for local development.
- **Simultaneous Entities**: Simulations can run with Laya alone, or with Laya, Jev, and Basic Strategy competing synchronously in parallel tables.
