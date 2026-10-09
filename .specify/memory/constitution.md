<!--
Sync Impact Report:
- Version change: 0.0.0 (Template) → 1.0.0
- List of modified principles:
  - [PRINCIPLE_1_NAME] → I. Engine Independence & Determinism
  - [PRINCIPLE_2_NAME] → II. Tri-Entity Synchronization & Experiment Isolation
  - [PRINCIPLE_3_NAME] → III. Provider Abstraction & Model Decoupling
  - [PRINCIPLE_4_NAME] → IV. Seeded Reproducibility
  - [PRINCIPLE_5_NAME] → V. Telemetry, Structured Persistence & Batch Safety
- Added sections:
  - Technology Stack & Architectural Constraints
  - Development Workflow & Quality Gates
  - Governance
- Removed sections:
  - None (scaffold placeholders replaced)
- Follow-up TODOs:
  - None
-->

# Decision_Blackjack Constitution

## Core Principles

### I. Engine Independence & Determinism

The Blackjack engine MUST serve as the deterministic, UI-agnostic core of the system.
All game rules—including shoe generation, card shuffling, burn protocols, card distribution,
hand evaluation, Ace softness resolution, natural Blackjack detection, dealer standing/hitting
rules (Hard/Soft 17), split/double/surrender logic, and bankroll settlement—MUST reside
exclusively within backend core services.
The frontend client MUST NOT execute, validate, or mutate core game mechanics.
The engine MUST be capable of running fully headless simulations without an active UI or
live network sockets.
_Rationale_: Decoupling the rule engine ensures mathematical integrity, prevents state drift
between the client and server, and enables rapid automated test runs and headless benchmarking.

### II. Tri-Entity Synchronization & Experiment Isolation

The three decision entities—**Jev** (remote System One AI via API), **Laya** (local model),
and **Optimal Strategy** (mathematical baseline with Hi-Lo card counting)—MUST be evaluated in independent, isolated game tables.
All three tables MUST originate from identical initial conditions (same random seed, initial
shoe permutation, and table rules configuration).
Table progression MUST be synchronized by a central orchestrator at the turn and round level.
No table may advance to subsequent rounds until all active entities have concluded their round actions.
If a decision entity experiences latency or an operational failure, the orchestrator MUST
pause or stop all tables synchronously.
_Rationale_: Comparative benchmarking loses scientific validity if tables diverge in initial
shoe composition or run out of synchronization.

### III. Provider Abstraction & Model Decoupling

All decision entities MUST implement a unified `DecisionProvider` interface that accepts
an immutable representation of game state and returns a decision accompanied by confidence
metrics and inference metadata.
The core engine MUST NOT depend on HTTP clients, transport protocols, or remote vendor SDKs;
all external model interactions (such as the Jev API) MUST be encapsulated within dedicated
adapter modules.
API keys and secrets MUST be loaded from environment variables (`.env`) and MUST NEVER be
exposed to the frontend client or committed to version control.
Transient failures or HTTP errors from remote providers MUST trigger a graceful pause with
state preservation rather than an unhandled application crash.
_Rationale_: Isolates external network fragility, prevents credential leaks, and allows new
decision models to be plugged in without refactoring the blackjack engine.

### IV. Seeded Reproducibility

Every simulation run MUST support explicit random seed configuration (`seed`).
Pseudo-random number generators (PRNG) responsible for shoe initialization, shuffling, and
card cutting MUST be deterministically seeded.
Given an identical seed, configuration, and entity responses, the simulation run MUST produce
an identical sequence of rounds, hands, and outcomes.
_Rationale_: Reproducibility is mandatory for investigating decision discrepancies, debugging
rare rule permutations, and auditing model behavior under identical conditions.

### V. Telemetry, Structured Persistence & Batch Safety

The system MUST record every round event, card deal, player decision, confidence metric,
model latency, and bankroll transaction into a structured schema (PostgreSQL) and structured
file records (`/data/runs/[timestamp]`).
Telemetry updates dispatched to the user interface during active simulations MUST maintain
a latency under 200 ms following inference completion.
For high-volume simulations exceeding 10,000 rounds, persistence operations MUST be executed
in batches to prevent RAM saturation and buffer bloat.
Results MUST be exportable in structured tabular formats (JSON) for external statistical
evaluation.
_Rationale_: The system's primary objective is comparative analysis of AI decision models
against game theory; incomplete or corrupted persistence destroys the value of the simulation.

## Technology Stack & Architectural Constraints

- **Backend**: Python 3.12+ managed with `uv`, FastAPI for REST and WebSocket orchestration,
  implementing asynchronous task management.
- **Database**: PostgreSQL with relational schemas capturing runs, simulations, player sessions,
  shoes, rounds, hands, card events, decisions, bets, and bankroll transactions.
- **Frontend**: React with TypeScript, Vite, Tailwind CSS, shadcn/ui components, and React Hook
  Form for configuration workflows.
- **Containerization**: Docker and Docker Compose providing isolated, reproducible deployment
  accessible over `localhost`.
- **Fault Recovery**: RNF-02 compliance: Remote provider HTTP errors (4xx/5xx) or timeouts
  MUST pause the simulation, preserve collected data, notify the user, and offer Retry or Abort.

## Development Workflow & Quality Gates

- **Test-Driven Development (TDD)**: Non-negotiable for engine mechanics. All rule variations
  (Soft 17, DAS, RSA, Surrender, ENHC/Peek) MUST have comprehensive automated unit tests before
  incorporation into the orchestrator.
- **Type Safety & Contracts**: Strict TypeScript in the frontend; Pydantic v2 schemas and strict
  Python typing in the backend.
- **Code Review & Quality Gates**: PRs MUST be verified against principle compliance. Any business
  logic placed in the frontend or unseeded randomness in the engine MUST be rejected.
- **Automated Verification**: Linters (`ruff`, `eslint`, `tsc`) and test suites MUST pass
  cleanly before any merge.

## Governance

This constitution supersedes all other documentation, ad-hoc agreements, or code practices.
All pull requests, architecture documents, and implementations MUST comply with its principles.
Amendments require documentation, explicit justification, and a version increment according
to Semantic Versioning:

- **MAJOR**: Incompatible principle removals or foundational governance overhauls.
- **MINOR**: Additions of new principles, sections, or materially expanded architectural rules.
- **PATCH**: Non-semantic clarifications, wording improvements, or typographical corrections.
  Compliance reviews MUST be performed during `/speckit-specify`, `/speckit-plan`, and code reviews.

**Version**: 1.0.0 | **Ratified**: 2026-10-09 | **Last Amended**: 2026-10-09
