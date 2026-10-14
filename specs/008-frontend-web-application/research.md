# Technical Research: Decision Blackjack Frontend Web Application

**Feature**: `008-frontend-web-application`  
**Date**: 2026-10-13  
**Status**: Completed  

---

## 1. Single Page Application Architecture & Routing

### Decision: React 19 + React Router 8 (`react-router` v8.4.0) SPA
- **Choice**: Multi-route Single-Page Application using `react-router` (`BrowserRouter`, `Routes`, `Route`, `useNavigate`, `useParams`). All components and routing hooks are imported directly from `'react-router'`.
- **Rationale**:
  - Clean separation of the user journey:
    - `/`: Initial Variant Rules Configuration Form, Player Selection, and Global Database Controls.
    - `/simulate/:sessionId`: Real-Time Tri-Entity Table Visualizer (2x3 Grid, GSAP animations, 3 dynamic graph bars, control bar, error modal).
    - `/batch/:sessionId`: Fast Batch execution progress card with round indicator and Cancel button.
    - `/complete/:sessionId`: Completion Page with Success Dialog, Tri-Player Summary Table, and Action Buttons (Export Simulation Data & New Simulation).
  - Enables bookmarking or inspecting simulation sessions by `session_id`.
- **Alternatives Considered**:
  - *Single monolithic page with state conditional rendering*: Harder to manage route transitions, back-button history, and cleanup on navigation.

---

## 2. Animation Strategy: GSAP & `@gsap/react`

### Decision: GSAP Core + `useGSAP` Hook with Dynamic Duration Scaling
- **Choice**: GreenSock Animation Platform (`gsap` 3.15+) combined with `@gsap/react` (`useGSAP`).
- **Rationale**:
  - GSAP is the industry standard for high-performance DOM/SVG animations and runs smoothly at 60+ FPS.
  - `@gsap/react` provides automatic lifecycle cleanup (`ctx.revert()`), prevents memory leaks across React re-renders, and offers `contextSafe` for callback handling.
  - **Horizontal Double Down Rotation**: Cards dealt on a double down action are animated with `transform: rotate(90deg)` (horizontal orientation), fulfilling `SC-003`.
  - **Dynamic Pacing Scaling (`SC-005`)**: When the user adjusts the speed range slider, animation duration scales proportionally:
    $$\text{duration} = \max\left(0, \min\left(0.4, \frac{\text{delay\_ms}}{1000} \times 0.4\right)\right)$$
    At `delay_ms = 0`, duration is 0 s, rendering cards instantly to prevent animation backlogs.
- **Alternatives Considered**:
  - *CSS Transitions / Keyframes*: Difficult to dynamically scale duration per event, coordinate multi-card dealing sequences, and interrupt cleanly on simulation pause.
  - *Framer Motion*: Larger bundle size and less precise fine-grained timeline control compared to GSAP.

---

## 3. UI Component Library: Tailwind CSS & shadcn/ui

### Decision: Tailwind CSS v3 + shadcn/ui Base Nova Theme (`@base-ui/react`)
- **Choice**: shadcn/ui primitives configured in `components.json` with semantic Tailwind utility classes and Lucide icons.
- **Components Implemented / Used**:
  - `Button`: Primary, outline, secondary, and destructive variants with Lucide icons (`Play`, `Pause`, `RotateCcw`, `Download`, `Trash2`, `Settings`).
  - `Card`, `CardHeader`, `CardTitle`, `CardContent`: Form groups, player columns, and summary containers.
  - `Input`, `Label`: Numerical rule bounds (bankroll, bet limits, decks, rounds, seed).
  - `Select`: Dropdowns for house rule variants (Soft 17, BJ payout, surrender, peek rule).
  - `Switch` / `Checkbox`: Toggles for DAS, RSA, Insurance, Mock Mode, and individual Player Selection.
  - `Slider`: Speed range bar (0 ms to 2,000 ms).
  - `Progress`: Fast Batch progress bar and real-time graph bars in player stats.
  - `Dialog` / `AlertDialog`: Error notifications (RNF-02), confirmation for database purge, and completion success dialog.
  - `Badge`: Decision badges (`Action: HIT`, `Action: STAND`), comparison tags, and bankroll delta badges (`+$50`, `-$20`).
- **Rationale**:
  - Full accessibility compliance (ARIA labels, keyboard focus management).
  - Semantic dark mode styling matching casino felt aesthetics.
- **Alternatives Considered**:
  - *Custom hand-written CSS*: Prone to styling bugs and accessibility oversights.

---

## 4. Playing Card Assets & Mapping

### Decision: Local SVG Deck from `frontend/Assets/cards/`
- **Choice**: Map backend string representations (e.g., `10♠`, `A♥`, `K♦`, `7♣`) directly to the pre-existing SVG deck in `frontend/Assets/cards/` (`10_of_spades.svg`, `ace_of_hearts.svg`, etc.).
- **Dealer Hole Card**: In American Peek mode before dealer play, the second dealer card renders using `card_back.svg` and flips face-up upon dealer reveal.
- **Fallback**: Clean stylized HTML card with unicode suit symbol if an asset is missing.
- **Rationale**:
  - Vector SVGs render crisply at any scale without pixelation.
  - Pre-installed in `frontend/Assets/cards/` with 0 external network requests.

---

## 5. WebSockets & Real-Time Telemetry State Management

### Decision: Native WebSocket Client with React Context (`SimulationContext`)
- **Choice**: Native browser `WebSocket` connecting to `ws://localhost:8000/ws/simulations/{session_id}`.
- **Event Dispatching**:
  - `SESSION_SNAPSHOT`: Initializes active players, table metrics, and rule config.
  - `ROUND_STARTED`: Increments round counter and shoe generation.
  - `BET_PLACED`: Updates current bet and bankroll deductions.
  - `CARD_DEALT`: Dispatches card to table slot, triggering GSAP deal animation (or horizontal orientation if double down).
  - `DECISION_MADE`: Updates `Action: [DECISION]`, confidence score, and basic strategy comparison.
  - `ROUND_SETTLED`: Updates bankroll deltas, running deviations, and the 3 dynamic graph bars.
  - `SESSION_PAUSED` / `SESSION_RESUMED`: Synchronizes control bar state.
  - `SESSION_ERROR`: Displays error notification with "Retry" button (if recoverable).
  - `SESSION_COMPLETED`: Navigates to `/complete/:sessionId`.
- **Latency Requirement (RNF-01)**: React batch updates ensure visual latency remains strictly under 50 ms upon event receipt (well below the 200 ms threshold).

---

## 6. Real-Time Graph Bars Formulation

### Decision: Three Synchronized Progress Bars per Player Column
- **Bar 1: Basic Strategy Optimality Rate (%)**:
  $$\text{Optimality Rate} = \frac{\text{optimal\_decisions}}{\text{total\_decisions}} \times 100\%$$
- **Bar 2: Win / Loss / Push Distribution (%)**:
  - Triple-segmented bar: Green (Wins), Red (Losses), Gray (Pushes).
- **Bar 3: Current Bankroll Relative to Starting Bankroll**:
  $$\text{Relative Bankroll \%} = \min\left(200\%, \max\left(0\%, \frac{\text{Current Bankroll}}{\text{Starting Bankroll}} \times 100\%\right)\right)$$
  - Displays baseline at 100%, green when $> 100\%$, red when $< 100\%$.
