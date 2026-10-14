# UI Component Contracts & Specifications

**Feature**: `008-frontend-web-application`  
**Date**: 2026-10-13  
**Status**: Draft  

---

## 1. Component Hierarchy & Layout

```text
App (React Router)
├── Routes
│   ├── Route path="/" element={<ConfigurationPage />}
│   │   ├── Navbar (Brand & Global Actions)
│   │   │   ├── ExportWholeDatabaseButton -> GET /api/export/database
│   │   │   └── DeleteDatabaseButton -> DELETE /api/database (with AlertDialog)
│   │   └── SimulationConfigForm (React Hook Form + shadcn)
│   │       ├── HouseRulesSection (S17, Payout, Peek, Surrender, Splits, Decks)
│   │       ├── BettingLimitsSection (Bankroll, Min Bet, Max Bet)
│   │       ├── SimulationScopeSection (Rounds, Mode, Seed, Delay, Mock Mode)
│   │       └── PlayerSelectionSection (Jev, Laya, Basic Strategy checkboxes)
│   │
│   ├── Route path="/batch/:sessionId" element={<FastBatchPage />}
│   │   └── FastBatchProgressCard
│   │       ├── RoundProgressIndicator ("Round 450 of 1,000")
│   │       ├── ProgressBar (shadcn Progress)
│   │       └── CancelButton -> POST /api/simulations/{id}/control { command: "stop" }
│   │
│   ├── Route path="/simulate/:sessionId" element={<VisualizerPage />}
│   │   ├── TopStatusBar (Round Counter, Shoe Generation, Session Status)
│   │   ├── VisualizerGrid2x3 (3-column layout)
│   │   │   ├── PlayerColumn (Jev)
│   │   │   │   ├── TableCarpetRow (bg: rgb(213, 120, 190), GSAP Cards, Horizontal Double)
│   │   │   │   └── LiveStatsRow (Bet, Action Badge, Comparison, 3 Graph Bars)
│   │   │   ├── PlayerColumn (Laya)
│   │   │   │   ├── TableCarpetRow (bg: rgb(68, 120, 208), GSAP Cards, Horizontal Double)
│   │   │   │   └── LiveStatsRow (Bet, Action Badge, Comparison, 3 Graph Bars)
│   │   │   └── PlayerColumn (Basic Strategy)
│   │   │       ├── TableCarpetRow (bg: rgb(118, 194, 154), GSAP Cards, Horizontal Double)
│   │   │       └── LiveStatsRow (Bet, Action Badge, Comparison, 3 Graph Bars)
│   │   ├── ControlBar (Bottom fixed/sticky bar)
│   │   │   ├── PauseResumeButton
│   │   │   ├── SpeedRangeSlider (0 to 2000 ms)
│   │   │   ├── CancelButton
│   │   │   └── ExportDatabaseButton
│   │   └── FaultAlertModal (RNF-02 Error Dialog with Retry)
│   │
│   └── Route path="/complete/:sessionId" element={<CompletionPage />}
│       └── CompletionSuccessDialog
│           ├── SuccessMessageTitle & Subtitle
│           ├── TriPlayerSummaryTable (Final Bankroll, Net P/L, Win Rate %, Agreement %)
│           ├── ActionButton1: "Export Simulation Data" -> GET /api/export/simulations/{id}
│           └── ActionButton2: "New Simulation" -> Navigate("/")
```

---

## 2. Component Interface Contracts

### 2.1 `TableCarpetRow` (Top Row of 2x3 Grid)
- **Props**:
  ```typescript
  interface TableCarpetRowProps {
    entityId: 'jev' | 'laya' | 'optimal';
    carpetColor: string; // "rgb(213, 120, 190)", "rgb(68, 120, 208)", "rgb(118, 194, 154)"
    isSelected: boolean;
    dealerCards: CardVisualState[];
    dealerTotal: number;
    playerHands: PlayerHandVisual[];
    activeHandIndex: number;
    delayMs: number;
  }
  ```
- **Rules**:
  - If `isSelected === false`: Render only the container with background `carpetColor`, displaying a subtle centered "Table Inactive / Deselected" watermark. Do not render cards or run animations.
  - Cards dealt on a **Double Down** action MUST render with CSS `transform: rotate(90deg)` (horizontal orientation) and appropriate margin adjustments so cards do not collide.
  - GSAP animations must use `useGSAP` with scope bound to the carpet container ref.

### 2.2 `LiveStatsRow` (Bottom Row of 2x3 Grid)
- **Props**:
  ```typescript
  interface LiveStatsRowProps {
    entityId: 'jev' | 'laya' | 'optimal';
    isSelected: boolean;
    currentBet: number;
    lastAction: string | null; // e.g., "HIT", "STAND"
    comparison: DecisionComparison | null;
    currentBankroll: number;
    netProfitDelta: number;
    optimalityRate: number; // 0.0 to 1.0
    winLossPush: { wins: number; losses: number; pushes: number; total: number };
    relativeBankrollPct: number;
  }
  ```
- **Rules**:
  - If `isSelected === false`: Render container with `opacity-40 grayscale pointer-events-none` (darkened/disabled state).
  - Header: Left: `Current Bet: $X`. Right: `Action: [BADGE]` (e.g. `Action: HIT`).
  - Middle: Comparison line: `✓ Matches Optimal (Hard 16 vs 10)` or `✗ Deviates: Recommended Stand`.
  - Financials: `Bankroll: $1,050 (+50.00)` in green or red.
  - **3 Graph Bars**:
    1. Optimality Rate: Horizontal progress bar labeled `Basic Strategy Agreement: XX%`.
    2. Outcome Breakdown: Tri-color segmented bar (Green: Wins, Red: Losses, Gray: Pushes).
    3. Relative Bankroll: Progress bar centered at 100%, showing relative wealth.

### 2.3 `ControlBar`
- **Props**:
  ```typescript
  interface ControlBarProps {
    status: SimulationLifecycle;
    delayMs: number;
    onTogglePause: () => void;
    onSpeedChange: (newDelayMs: number) => void;
    onCancel: () => void;
    onExportDatabase: () => void;
  }
  ```
- **Rules**:
  - `PauseResumeButton`: Displays Pause icon when `RUNNING`, Play icon when `PAUSED`.
  - `SpeedRangeSlider`: Slider from 0 to 2000 ms. Displays real-time value: `0 ms (Max)` to `2000 ms (Slow)`.
  - `CancelButton`: Prompts confirmation before calling stop.
  - `ExportDatabaseButton`: Triggers direct download of `/api/export/database`.

### 2.4 `FaultAlertModal` (RNF-02 Compliance)
- **Props**:
  ```typescript
  interface FaultAlertModalProps {
    isOpen: boolean;
    entityId: string;
    errorMessage: string;
    isRecoverable: boolean;
    onRetry: () => void;
    onAbort: () => void;
  }
  ```
- **Rules**:
  - Displays a clean error alert: e.g. "Timeout error for Jev".
  - If `isRecoverable === true`: Displays **"Retry Turn"** button alongside "Abort".
  - If `isRecoverable === false`: Displays only "Abort Simulation" button.
