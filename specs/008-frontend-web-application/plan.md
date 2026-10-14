# Implementation Plan: Decision Blackjack Frontend Web Application

**Branch**: `008-frontend-web-application` | **Date**: 2026-10-13 | **Spec**: [`specs/008-frontend-web-application/spec.md`](./spec.md)

**Input**: Feature specification from `/specs/008-frontend-web-application/spec.md` and user requirements.

---

## Summary

Build the complete, production-ready **Frontend Web Application** for the Decision Blackjack benchmarking suite located in `frontend/`. Implemented as an interactive Single-Page Application (SPA) using **React 19**, **TypeScript**, **Tailwind CSS**, **shadcn/ui** (`@base-ui/react`), **React Router 8** (`react-router` v8.4.0), and **GSAP** (`@gsap/react`), the frontend connects to the backend over REST and native WebSockets.

Key capabilities delivered:
1. **Interactive Variant Rules Configuration (`/`)**: Complete form mapping all rules from `docs/Reglas de BlackJack.md`, player selection toggles (Jev, Laya, Basic Strategy), Mock Mode toggle, and startup database tools (Export Whole Database & Delete Database).
2. **Dual-Path Execution**:
   - **Path 1 (Fast Batch `/batch/:sessionId`)**: Progress card displaying round progress, progress bar, and Cancel button.
   - **Path 2 (Real-Time Visualizer `/simulate/:sessionId`)**: 2x3 Grid with distinct table carpet colors:
     - Jev: `rgb(213, 120, 190)`
     - Laya: `rgb(68, 120, 208)`
     - Basic Strategy: `rgb(118, 194, 154)`
3. **GSAP Card Animations & Doubling**: Real-time card dealing from shoe, split cards, surrender, and **horizontal orientation (90-degree rotation)** for double down cards, with dynamic duration scaling down to instant placement at 0 ms delay.
4. **Live Stats & 3 Dynamic Graph Bars**: Header showing `Current Bet` and `Action: [HIT/STAND]`, basic strategy comparison badge, bankroll state (`+$50`), and 3 dynamic graph bars (Optimality Rate %, Win/Loss/Push %, Relative Bankroll %).
5. **Deselected Player Handling**: Deselected players display an empty table with carpet color (no card animations) and darkened/disabled stats.
6. **Bottom Controls**: Pause/Resume, dynamic speed slider (0 to 2000 ms), Cancel/Stop, and Export Database.
7. **Error Recovery (RNF-02)**: Alert dialog with simple explanation and "Retry Turn" button on recoverable faults.
8. **Completion Success Page (`/complete/:sessionId`)**: Success dialog with Tri-Player summary table, "Export Simulation Data", and "New Simulation" buttons.

---

## Technical Context

**Language/Version**: TypeScript 5.5+, React 19  
**Primary Dependencies**: Tailwind CSS 3.4, shadcn/ui (`@base-ui/react`), GSAP 3.15 + `@gsap/react`, React Router 8 (`react-router` v8.4.0), React Hook Form 7.53, Lucide React  
**Storage**: N/A on client; browser standard download for `.json` exports; PostgreSQL 16 on backend  
**Testing**: TypeScript type-checking (`tsc --noEmit`), Vite build validation, and quickstart scenario tests  
**Target Platform**: Modern Desktop Browsers (Chromium, Firefox, Safari)  
**Project Type**: Single-Page Web Application (SPA)  
**Performance Goals**: < 200 ms perceived visual latency post-inference (RNF-01), 60 FPS GSAP card animations, 0 ms unthrottled batch pacing  
**Constraints**: Zero core game logic in client (Constitution Principle I), tri-entity synchronization (Constitution Principle II), API keys never exposed to client (Constitution Principle III)  
**Scale/Scope**: 1 to 100,000 rounds, 3 simultaneous players, 4 responsive routes  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Engine Independence & Determinism**  
  *Status*: PASS. The frontend client does NOT calculate hand totals, detect busts, or validate game rules. It is a pure presentation layer driven by server state snapshots and WebSocket event frames.
- **Principle II: Tri-Entity Synchronization & Experiment Isolation**  
  *Status*: PASS. Visualizer coordinates the 3 isolated tables (Jev, Laya, Basic Strategy) in a synchronized 2x3 grid.
- **Principle III: Provider Abstraction & Model Decoupling**  
  *Status*: PASS. No remote AI provider SDKs, HTTP client tokens, or API keys are placed in frontend code.
- **Principle IV: Seeded Reproducibility**  
  *Status*: PASS. Form exposes explicit optional integer `seed` input forwarded to `POST /api/simulations`.
- **Principle V: Telemetry, Structured Persistence & Batch Safety**  
  *Status*: PASS. Event frames stream over native WebSockets; visual latency remains under 50 ms (< 200 ms target); export and purge tools hook into backend streaming APIs.

---

## Project Structure

### Documentation (this feature)

```text
specs/008-frontend-web-application/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── ui-components.md
│   └── websocket-events.md
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (`frontend/`)

```text
frontend/
├── Assets/
│   └── cards/                     # Authentic playing card SVGs
│       ├── 10_of_spades.svg
│       ├── ace_of_hearts.svg
│       ├── card_back.svg
│       └── ... (52 cards + backs)
├── src/
│   ├── types/
│   │   ├── simulation.ts          # Variant rules, game state, telemetry frames
│   │   └── api.ts                 # REST and WebSocket request/response schemas
│   ├── lib/
│   │   ├── utils.ts               # cn() classname merger (clsx + tailwind-merge)
│   │   └── cardAssets.ts          # Nominal string to SVG asset mapper
│   ├── services/
│   │   ├── apiClient.ts           # REST API fetch client
│   │   └── websocketService.ts    # Native WebSocket client manager
│   ├── context/
│   │   └── SimulationContext.tsx  # React Context for session & live telemetry
│   ├── components/
│   │   ├── ui/                    # shadcn UI components (Button, Card, Input, etc.)
│   │   ├── Navbar.tsx             # Brand header with database export/purge
│   │   ├── ControlBar.tsx         # Pause/Resume, speed slider, Stop, Export DB
│   │   ├── FaultAlertModal.tsx    # RNF-02 Error Dialog with Retry/Abort
│   │   └── CardView.tsx           # Single playing card with GSAP animation ref
│   ├── forms/
│   │   └── SimulationConfigForm.tsx # RHF variant rules form + player selection
│   ├── visualization/
│   │   ├── VisualizerGrid2x3.tsx  # 2x3 Grid organizing the 3 player columns
│   │   ├── TableCarpetRow.tsx     # Top row: table carpet with exact RGB colors & GSAP
│   │   ├── LiveStatsRow.tsx       # Bottom row: bet, action badge, 3 graph bars
│   │   └── FastBatchProgressCard.tsx # Path 1 round progress card with Cancel
│   ├── pages/
│   │   ├── ConfigurationPage.tsx  # Home route ('/') with config form & DB tools
│   │   ├── VisualizerPage.tsx     # Path 2 route ('/simulate/:sessionId')
│   │   ├── FastBatchPage.tsx      # Path 1 route ('/batch/:sessionId')
│   │   └── CompletionPage.tsx     # Completion route ('/complete/:sessionId')
│   ├── App.tsx                    # React Router configuration
│   ├── main.tsx                   # React root entry point
│   └── index.css                  # Tailwind directives & CSS variables
├── components.json
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

**Structure Decision**: Clean modular SPA architecture separating UI primitives, forms, visualization rows, telemetry context, and routed pages.

---

## Complexity Tracking

*No constitutional violations; no complexity exceptions needed.*
