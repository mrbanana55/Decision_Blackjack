# Phase 0 Research: Laya Decision Agent Integration

**Feature**: `005-laya-agent-integration`
**Status**: Completed

## 1. Directory Organization & Provider Modularity

### Decision
Place all Laya-specific integration components under a dedicated subpackage:
`backend/app/integrations/laya/`
with public exports surfaced via `backend/app/integrations/laya/__init__.py`.

```text
backend/app/integrations/
├── __init__.py
└── laya/
    ├── __init__.py           # Public exports (LayaAgent, LayaClient, LayaSchemaBuilder, etc.)
    ├── agent.py              # LayaAgent implementing DecisionProvider protocol
    ├── builder.py            # LayaSchemaBuilder generating situation-specific TypeSafe schemas
    ├── client.py             # Async HTTP client (httpx) with health check & retry/timeout logic
    ├── config.py             # LayaConfig loading LAYA_BASE_URL from .env with container bridge routing
    └── schemas.py            # Pydantic v2 models for TypeSafe System One requests and responses
```

### Rationale
- Complies directly with user instruction: *"All the requests stuff should be on the `backend/app/integrations` directory... Use a directory for Laya and inside it add anything related to the integration with laya."*
- Follows Constitution Principle III (Provider Abstraction & Model Decoupling): keeps HTTP transports, JSON serialization, and vendor-specific endpoints strictly isolated from core Blackjack engine and simulation orchestrator.
- Establishes a repeatable blueprint for future providers (e.g. `backend/app/integrations/jev/`).

### Alternatives Considered
- *Inlining inside `backend/app/simulation/agents/laya.py`*: Rejected because it mixes network transport and serialization with simulation lifecycle logic and clutters the simulation agent package.
- *Single flat `integrations.py` file*: Rejected because multi-phase schema modeling, client error recovery, and agent adaptation require modular separation as more providers are integrated.

---

## 2. Dynamic Rule-Adaptive Situational Schemas

### Decision
`LayaSchemaBuilder` dynamically generates the petition `state` description, question `instructions`, and `criteria` mapping by evaluating:
1. `context.legal_actions` (which already encapsulates table rules: `allow_late_surrender`, `double_after_split`, `max_split_hands`, card count, and bankroll affordability).
2. Dynamic table rules configuration (never hardcoding minimum bet, split limits, or dealer hit/stand rules; retrieving `min_bet` from `TableRules`).
3. Hand soft/hard total and card composition.

### Situational Categories Identified:
1. **Initial Paired Hand (Split Eligible)**: Hand has 2 equal rank cards, split limit not reached, bankroll $\ge$ bet. Schema includes `split` criteria alongside `hit`, `stand`, and conditionally `double` or `surrender`.
2. **Initial Standard Hand (Double/Surrender Eligible)**: Hand has 2 cards, non-pair. Includes `hit`, `stand`, and conditionally `double` and/or `surrender` based on `legal_actions`. Omit `split`.
3. **Multi-Card Draw Hand (Post-Hit / 3+ Cards)**: Player has drawn cards. Prohibits double, split, and surrender. Criteria contains strictly `hit` and `stand`.
4. **Insurance Offer Phase (Dealer Ace Revealed)**: Pre-play phase. Criteria contains strictly `accept` vs `decline`, detailing the exact insurance wager cost ($0.5 \times \text{initial\_bet}$) and player bankroll.
5. **Round Betting Phase (Pre-Deal Wager Sizing)**: Evaluates dynamic table minimum bet ($M = \text{rules.min\_bet}$), current bankroll, and running/true count. Presents discrete choices:
   - `1x`: 1 unit ($M) - Base minimum wager
   - `2x`: 2 units ($2M) - Moderate count wager
   - `4x`: 4 units ($4M) - Elevated advantage wager
   - `8x`: 8 units ($8M) - High count maximum spread wager
   (Options requiring bankroll > available balance are automatically pruned or capped).

### Rationale
- Completely eliminates illegal action exceptions from the model by never offering invalid moves as selectable criteria.
- Adheres to the user's explicit directive: *"rules may change, so depending on the rules configuration the player might be able to surrender or not... The minimum bet can change depending on the user's configuration, so dont make it hard written."*

### Alternatives Considered
- *Static 5-action criteria on every turn with penalty logic*: Rejected because it wastes LLM attention on illegal actions, corrupts probability distributions, and leads to unnecessary model error handling loops.
- *Free-form text generation*: Rejected because TypeSafe System One specializes in typed discrete Choice decisions.

---

## 3. Host-to-Container Bridge & Environment Configuration

### Decision
1. In `backend/app/integrations/laya/config.py`:
   - Load `LAYA_BASE_URL` from `.env` using Pydantic Settings / `os.getenv`, defaulting to `http://127.0.0.1:1234` when running natively.
   - Intelligent Container Host Normalization: When running inside Docker (detectable via `/.dockerenv` or `ENVIRONMENT != 'local'`) and `LAYA_BASE_URL` contains `127.0.0.1` or `localhost`, automatically rewrite the hostname to `host.docker.internal` (e.g. `http://host.docker.internal:1234`).
2. In `docker-compose.yml`:
   - Add `extra_hosts: ["host.docker.internal:host-gateway"]` to the `backend` service to ensure cross-platform compatibility across Linux and macOS Docker daemons.
   - Pass `LAYA_BASE_URL: ${LAYA_BASE_URL:-http://host.docker.internal:1234}` in the `environment` block.

### Rationale
- Zero-friction developer experience: The user can keep `LAYA_BASE_URL=http://127.0.0.1:1234` in their root `.env` file, and both native tests (`pytest` on Mac) and container tests (`docker compose exec backend uv run pytest`) seamlessly connect to the host Laya process without manual URL switching.
- Allows immediate reconfiguration if Laya is moved to a different port (e.g. `http://127.0.0.1:5000`) simply by changing `.env`.

### Alternatives Considered
- *Requiring host IP addresses (e.g. 192.168.x.x)*: Rejected because local DHCP changes break the configuration.
- *Hardcoding `host.docker.internal` in code*: Rejected because native non-container executions (such as local IDE debuggers) cannot resolve `host.docker.internal`.

---

## 4. HTTP Client & Transport Architecture

### Decision
Use `httpx.AsyncClient` with connection pooling, keep-alive, configurable timeouts (default 3.0 seconds, connect timeout 1.5 seconds), and clean resource lifecycle management.

- `check_health() -> LayaHealthStatus`: Probes `GET /health`, parses device (`mps`/`cpu`/`cuda`), loaded models, and revision hashes.
- `send_systemone(request: SystemOneRequest) -> SystemOneResponse`: Posts JSON payload to `POST /v1/systemone`, captures high-precision wall-clock latency with `time.perf_counter()`, and unpacks answers.

### Rationale
- `httpx` is standard in modern async Python/FastAPI codebases, supporting native JSON serialization, structured HTTP error hierarchies, and async connection management.
- Bounded timeouts prevent high local inference load from hanging orchestrator event loops.

### Alternatives Considered
- *`aiohttp`*: Rejected because `httpx` is already part of the project backend dependencies and aligns with FastAPI conventions.
- *Synchronous `requests` in a threadpool*: Rejected because native asyncio HTTP clients avoid thread pool contention and overhead during fast-paced simulation turns.

---

## 5. Fault Recovery, State Preservation & RNF-02 Compliance

### Decision
When `LayaClient` encounters connection errors (`httpx.ConnectError`), timeouts (`httpx.TimeoutException`), or HTTP 5xx responses:
1. It raises domain-specific `AgentFaultError` with clear diagnostics (endpoint attempted, status code, cause).
2. The `SimulationOrchestrator` catches `AgentFaultError`, transitions `session.status` to `PAUSED_ERROR`, persists current table and round state without truncation, and emits `SESSION_PAUSED` telemetry.
3. The orchestrator exposes `resume_session()`, allowing the operator to start/restart Laya and retry the exact turn without losing table synchronization or seed reproducibility.

### Rationale
- Directly implements Constitution Principle III and RNF-02: *"Transient failures or HTTP errors from remote providers MUST trigger a graceful pause with state preservation rather than an unhandled application crash."*
- Ensures multi-agent benchmarks do not produce skewed or corrupted metrics due to transient host process restarts.
