# Feature Specification: Jev Decision Agent Integration & Remote System One Provider

**Feature Branch**: `006-jev-agent-integration`

**Created**: 2026-10-12

**Status**: Ready for Planning

**Input**: User description: "Let's make the Jev integration. We need to do something similar to what we did previously with Laya. We will be doing very similar things to what we did with Laya, so you can check how that was made. You can also use a type-safe skill to enhance the development. In general, we will be making the same blackjack questions we did to Laya and we will store the data in the same way."

## Clarifications & Design Alignment

### Context & Consistency with Prior Integrations

Following the successful architecture established in `specs/005-laya-agent-integration/`, this feature integrates **Jev**, TypeSafe's flagship System One model, as a first-class autonomous decision provider in the simulation orchestrator.

Key design alignments established from project patterns and TypeSafe API specifications:

- **Opening Bet Sizing (FR-006)**: Discrete System One Choice Query. At the start of each round, the orchestrator queries Jev via a TypeSafe System One Choice question with discrete bet options (`1x`, `2x`, `4x`, `8x` table minimum bet units, bounded by current bankroll and table limits).
- **Insurance Phase Handling (FR-007)**: Discrete System One Choice Query. When the dealer's visible card is an Ace, the orchestrator queries Jev via a Choice question with `accept` and `decline` criteria, applying the chosen insurance action to the table.
- **In-Hand Tactical Decisions (FR-001, FR-004)**: Dynamic Situational Schemas. The agent categorizes hands into situational states (paired split, standard 2-card with/without double/surrender, multi-card draw) and restricts choices strictly to legal actions.
- **Remote Provider Authentication & Endpoint (FR-002)**: Jev interacts with the TypeSafe System One API (`POST https://api.typesafe.ai/v1/systemone`) using Bearer token authentication via `TYPESAFE_API_KEY` and configurable endpoint `TYPESAFE_API_URL` loaded dynamically from `.env`.
- **Fault Resilience & Rate Limiting (FR-008)**: Strict Pause with State Preservation (RNF-02 & Constitution Principles II, III). If the remote Jev API times out, returns HTTP errors (401, 422), or exhausts retries on rate limits (429, 529), all synchronized tables pause synchronously (`PAUSED_ERROR`), preserving all in-flight state and telemetry without data loss, allowing the user to Retry or Abort.
- **Telemetry & Unified Persistence (FR-009, FR-010)**: All decisions, model latency, confidence scores, probability distributions, token usage, and comparisons against Basic Strategy are persisted identically into the PostgreSQL database (`decisions` and `model_responses` with provider `SYSTEM_ONE`) and JSON run archives.

---

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Real-Time Hand Action Decisions via Remote Jev Model (Priority: P1)

As a researcher benchmarking AI models against game theory, I want the simulation orchestrator to query the remote Jev System One model for all in-hand tactical decisions (Hit, Stand, Double, Split, Surrender) during each round, so that Jev competes autonomously under identical shoe conditions alongside Laya and Optimal Basic Strategy.

**Why this priority**: Core purpose of the feature. Replacing the temporary mock agent (`FakeJevAgent`) with real live inferences from TypeSafe's Jev model completes the tri-entity benchmarking capability required by the project constitution.

**Independent Test**: Can be tested independently by running a simulation session with the Jev entity, stepping through active hands, and verifying that actions taken at player turns correspond to the parsed choices, confidence scores, and probability distributions returned by the live TypeSafe System One API.

**Acceptance Scenarios**:

1. **Given** an active player hand with legal actions (e.g., Hit, Stand, Double), **When** Jev's turn arrives in the playing phase, **Then** the orchestrator formats the observable table context (player cards, total, softness, dealer upcard, legal actions, bankroll) into a TypeSafe System One Choice request, transmits it to the API with authentication, receives the decision, and applies the selected action to the hand.
2. **Given** a scenario where split or surrender is legally available (e.g., pair of 8s or 16 vs 10), **When** Jev's decision is requested, **Then** the choices presented to Jev include only legal actions according to table rules, and the chosen action executes cleanly.
3. **Given** a completed inference turn, **When** the decision is applied, **Then** inference latency, model confidence, probability distribution, and token usage are attached to telemetry events and persisted to the database.

---

### User Story 2 - Remote Provider Authentication, Configuration & Health Probes (Priority: P1)

As a developer or system operator running simulations, I want the backend service to configure Jev through `.env` variables (`TYPESAFE_API_KEY`, `TYPESAFE_API_URL`, `TYPESAFE_MODEL`) and provide a diagnostic health probe endpoint, so that I can verify credential validity and connectivity before launching long-running simulations.

**Why this priority**: P1 operational blocker. Simulations cannot execute without secure, environment-driven credentials and verifiable API connectivity. Exposing health diagnostics ensures operators do not launch broken simulations.

**Independent Test**: Can be tested independently by configuring API credentials in `.env`, triggering the health check endpoint `/health`, and verifying that the system reports connectivity status and model readiness.

**Acceptance Scenarios**:

1. **Given** valid credentials configured in `.env`, **When** the backend initiates a request to the Jev provider, **Then** requests include the proper `Authorization: Bearer <API_KEY>` header and target the configured URL.
2. **Given** the `/health/` diagnostic endpoint probed, **When** the API key is present and remote service is reachable, **Then** the endpoint returns operational readiness (`status: ok`) with configured model information.
3. **Given** missing or invalid API keys, **When** `/health` is probed or an inference is attempted, **Then** the system detects the authentication issue, reports a clear diagnostic error, and prevents unhandled application crashes.

---

### User Story 3 - Multi-Phase Game Decisions: Discrete Bet Sizing & Insurance (Priority: P2)

As a researcher evaluating AI risk management, I want the simulation orchestrator to consult Jev during all game phases requiring decision-making (including round opening bet sizing and insurance offers against dealer Aces), so that Jev's bankroll management and risk preferences are fully evaluated across complete rounds.

**Why this priority**: Essential for full round autonomy. A complete blackjack agent must decide how much to risk per round and whether to protect against dealer blackjacks, matching the exact capabilities implemented for Laya and Basic Strategy.

**Independent Test**: Can be tested independently by running rounds where the dealer shows an Ace (insurance phase) and observing round-opening bet selections, verifying that Jev's choices follow the configured TypeSafe System One Choice contract.

**Acceptance Scenarios**:

1. **Given** the start of a new round with available bankroll and table minimum bet rules, **When** determining the opening wager for Jev's table, **Then** the orchestrator sends a Choice question with discrete bet multipliers (`1x`, `2x`, `4x`, `8x` units of table minimum bet bounded by bankroll), and wagers the exact amount selected by Jev.
2. **Given** the dealer's visible upcard is an Ace, **When** insurance is offered to the table, **Then** the orchestrator queries Jev with a Choice question (`accept` vs `decline`), resolving the side bet according to Jev's response.
3. **Given** an opening wager or insurance decision, **When** applied, **Then** bankroll balances and financial transactions are updated accurately in table state and persistence logs.

---

### User Story 4 - Fault Resilience, Rate Limiting & Comparative Telemetry (Priority: P2)

As a simulation controller, I want the system to handle remote API rate limits (HTTP 429), server overloads (HTTP 529), network timeouts, and unexpected provider errors gracefully by retrying with backoff or pausing all synchronized tables without data loss, so that transient remote network issues do not corrupt the multi-agent experiment.

**Why this priority**: Fulfills Constitution Principles II, III, and RNF-02. In a synchronized 3-entity experiment, one failing or rate-limited agent must not crash the other tables, corrupt bankrolls, or lose telemetry.

**Independent Test**: Can be tested independently by simulating network timeouts, rate limit responses (HTTP 429), or authentication failures during an active simulation run, verifying that the session transitions to paused error state with full telemetry preserved, allowing retry or abort.

**Acceptance Scenarios**:

1. **Given** an active synchronized multi-entity simulation, **When** Jev encounters a transient rate limit (HTTP 429) or temporary server overload (HTTP 529), **Then** the client performs bounded exponential backoff retries.
2. **Given** persistent API failures, timeouts, or unhandled HTTP errors, **When** retries are exhausted, **Then** the orchestrator pauses all active tables synchronously (`PAUSED_ERROR`), preserves current state and bankrolls, and emits an error notification allowing Retry or Abort.
3. **Given** successful Jev decisions, **When** applied to the table, **Then** the decision comparator evaluates Jev's choice against the mathematical Basic Strategy baseline in real time, recording agreement and deviations in telemetry and database records.

---

### Edge Cases

- **Rate Limit Exhaustion (HTTP 429 / 529)**: What happens when the TypeSafe API rate limits the key during high-concurrency simulation rounds? The client applies exponential backoff up to a bounded maximum retry count; if still failing, it raises an agent fault that triggers a synchronized simulation pause without dropping pending table actions.
- **Invalid or Expired API Key (HTTP 401)**: What happens if the API key is rejected? The client detects the authentication failure immediately, aborts retries to avoid unnecessary traffic, pauses the simulation, and alerts the user to verify `.env`.
- **Malformed Model Output**: What happens if the API response omits the chosen answer or returns an invalid JSON structure? The system captures the raw response payload for debugging, logs a validation error, and triggers an agent fault rather than executing an undefined action.
- **Illegal Action Returned**: What happens if Jev selects an action not present in the legal actions list (e.g. Double on a 3-card hand)? The system traps the illegal action, logs a warning, and safely falls back to a valid legal action (e.g. Stand if legal, or Hit) or triggers a fault pause according to configuration.
- **Extreme Latency Spikes**: What happens if cloud inference takes longer than expected (> 10s)? A configurable request timeout prevents deadlocking orchestrator loops, transitioning to pause state if exceeded.
- **Bankroll Depletion Below Table Minimum**: What happens if Jev's bankroll falls below the table minimum bet? The agent is marked bankrupt for subsequent rounds, while peer tables continue according to orchestrator rules.

---

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST provide a dedicated decision provider client (`JevAgent`) that communicates with the remote TypeSafe System One API over HTTP using the standardized JSON payload schema matching TypeSafe System One specifications.
- **FR-002**: System MUST load Jev configuration dynamically from `.env` environment variables, including `TYPESAFE_API_URL` (defaulting to `https://api.typesafe.ai/v1/systemone`), `TYPESAFE_API_KEY`, and `TYPESAFE_MODEL` (defaulting to `jev-latest`), with request timeout and retry options.
- **FR-003**: System MUST provide a diagnostic health check endpoint (`/health/jev`) verifying API key presence, network reachability, and model responsiveness before initiating or during simulations.
- **FR-004**: System MUST employ situation-specific question schemas that dynamically generate the `state` description, instructions, and `criteria` options according to the player's exact tactical situation (initial hand with pair split, initial hand with double/surrender, multi-card post-hit draw, insurance offer, and round opening wager).
- **FR-005**: System MUST parse the TypeSafe System One JSON response to extract the chosen action (`choice`), confidence score (`confidence`), probability distribution (`probabilities`), token usage (`usage`), and latency, mapping them to the domain `AgentDecision`.
- **FR-006**: System MUST query Jev before each round deal using a TypeSafe System One Choice question to select an initial wager amount from discrete bet options (`1x`, `2x`, `4x`, `8x` units of table minimum bet bounded by available bankroll), parsing the chosen option into a concrete currency bet.
- **FR-007**: System MUST query Jev during the insurance phase (when dealer upcard is an Ace) using a TypeSafe System One Choice question with `accept` and `decline` criteria, applying the chosen insurance decision to the table.
- **FR-008**: System MUST handle network timeouts, HTTP errors, and rate limits (429/529) with bounded backoff retries, transitioning all synchronized tables to paused error state (`PAUSED_ERROR`) upon exhaustion without data loss or state corruption (RNF-02 compliance).
- **FR-009**: System MUST attach Jev's inference telemetry (latency, confidence, probabilities, token usage, model revision, and decision metadata) to all emitted simulation events and persist them in the database (`decisions` and `model_responses` tables with provider `SYSTEM_ONE`) and run JSON archives.
- **FR-010**: System MUST evaluate Jev's decisions against the mathematical Basic Strategy comparator in real-time, recording optimal vs sub-optimal agreement and expected-value deviations.

---

### Technical Data Contract (Situation-Specific Schemas)

Per TypeSafe System One API specifications and consistency with `docs/Laya_Example_Body.md`, all petitions sent to Jev follow TypeSafe System One request/response format with the mandatory `"model"` field and Bearer authentication header.

#### Situation 1A: Initial Paired Hand (Split Eligible, Surrender Disabled)

When the player holds 2 cards of identical rank, bankroll $\ge$ bet, and surrender is disabled:

```json
{
  "state": "Hand 1: [8 of Spades, 8 of Diamonds] (Pair of 8s, Total: 16). Dealer Upcard: 7 of Hearts. Bankroll: $1,000. True Count: +0.5. Legal actions: hit, stand, split. Surrender: Disabled.",
  "model": "jev-latest",
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
  "model": "jev-latest",
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
  "model": "jev-latest",
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

When the player holds 2 non-matching cards, bankroll $\ge$ bet, and late surrender is enabled:

```json
{
  "state": "Hand 1: [10 of Spades, 6 of Hearts] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $1,000. True Count: +1.0. Legal actions: hit, stand, double, surrender. Surrender: Enabled.",
  "model": "jev-latest",
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
  "model": "jev-latest",
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
  "model": "jev-latest",
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

Before cards are dealt, Jev decides the round opening bet amount:

```json
{
  "state": "Round 14. Table Minimum Bet: $50. Current Bankroll: $1,250. Shoe True Count: +2.5. Cards Seen: 142/312.",
  "model": "jev-latest",
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

- **JevDecisionAdapter**: Client module encapsulating HTTP communication with TypeSafe System One, serialization of `DecisionContext` into TypeSafe request payloads, Bearer authentication, retry backoff logic, response parsing, and error translation.
- **JevModelMetadata**: Telemetry attributes captured per inference, including model revision, input/output token usage, latency duration, confidence score, and option probability distributions.
- **JevConfig**: Configuration entity defining the TypeSafe API URL, API key, model name, timeout thresholds, and retry parameters sourced dynamically from `.env`.

---

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 100% of valid playing turns for the Jev entity successfully obtain decisions from the TypeSafe System One API and execute without manual intervention.
- **SC-002**: In the event of a simulated API outage, network timeout, or exhausted rate limit, 100% of active sessions pause cleanly within 1 second without data loss or engine state corruption.
- **SC-003**: Zero crashes or unhandled exceptions occur in the backend service during automated 500-round multi-agent simulations involving Jev.
- **SC-004**: 100% of Jev decisions are cross-evaluated against the mathematical Basic Strategy comparator with accurate agreement and deviation telemetry persisted.
- **SC-005**: All captured inference telemetry (model name, latency, token usage, confidence, probabilities) is persisted completely in database records and exportable run archives.

---

## Assumptions

- **TypeSafe Cloud Availability**: The external TypeSafe System One service is accessible over outbound HTTPS from the host/container network environment.
- **API Key Provisioning**: A valid TypeSafe API key is supplied via `TYPESAFE_API_KEY` in `.env` for production or live testing, with unit/mock test suites utilizing mock transports that require no live network access.
- **Schema Parity**: Jev uses the identical TypeSafe System One choice question protocol (state, questions with instructions and criteria) as specified in TypeSafe official documentation and consistent with Laya.
- **Concurrent Simulation**: Simulations can run with Jev alone, or with Jev, Laya, and Optimal Basic Strategy competing simultaneously in parallel synchronized tables.
