# Feature Specification: Decision Blackjack Frontend Web Application

**Feature Branch**: `008-frontend-web-application`  
**Created**: 2026-10-13  
**Status**: Draft  
**Input**: User description: "Let's make the frontend. when I start the apps frontend I want to see a form to set and modify the variant rules of blackjack (they're in @docs/Reglas de BlackJack.md) and once the form is correctly filled i want to send the rules with the API we made previously. After submitting the form there will be 2 paths: the first path is the one where I can simply submit the form and get the data without any special animation or live show, I just want the games to be played and to get the data ASAP. The other option is to see the real time games of each player. In this second path I want to simultaneusly see each player game, showing animations when cards are dealt, split, surrender or double (double needs a card to be horizontal instead of vertical). Apart from seing the card animations according to each players actions I wanna see real time stats, showing useful info like comparissons between AI players and what the basic strategy would do in the same position, the bankroll state (example: +$50), etc. This stats should also be displayed using real time graph bars. The screen structure for this second path consist of a 2 by 3 grid, one column for each player (Jev, Laya, Basic Strategy). The top row of each column should have the game card animations, each of this player row's should have a different background color (JEV: (213, 120, 190), Laya: (68, 120, 208), Basic Strategy: (118, 194, 154)) simulating the tables carpet. The bottom row of each column should have the corresponding player's live stats. At the top of the live stats I want to see the current bet and next to it i want to see the decision the AI made (Example: Action: HIT). At the bottom of all I need a section for user control, I need buttons to pause the simulation, a range bar to change the game's speed, cancel button, export database, etc. The hability to export the export the whole database and delete database should also be available at the start of the app. If an error happens then the user should see an alert notification with a simply explanation of the error (example: Timeout error for jev). When an error happens then the simulation's visualization should pause and the error notification should have a button to quickly solve the problem if possible (like retry). If the problem can't be solved quickly then no button should be shown in the notification. After a simulation is completed in any of the 2 paths mentioned before, the page should go to another page showing a dialog that tells the user the simulation(s) was/were successful. After the messsage, two action buttons should be shown. The first action button should let the user export the simulation's data, the second button should redirect to the initial form for another simulation."

---

## Clarifications

### Session 2026-10-13
- Q: Which specific comparative metrics should be displayed using the real-time graph bars in the bottom row of each player column? → A: Three dynamic bars showing (1) Basic Strategy Optimality Rate (% agreement), (2) Win / Loss / Push distribution percentage, and (3) Current bankroll relative to starting bankroll.
- Q: What visual feedback and controls should be displayed to the user while Path 1 (Fast Batch) is executing before redirecting to the completion dialog? → A: Progress card with Cancel: shows current round count (e.g., "Round 450/1,000"), percentage progress bar, and a Cancel button.
- Q: Should the initial configuration form include an optional "Mock Mode" toggle to allow running simulations with simulated agent responses when external Jev API keys or local Laya endpoints are unavailable? → A: Option A (Optional Mock Mode toggle defaulting to Live models, allowing users to switch to mock agents when desired).
- Q: How should card animation durations behave when the user sets the simulation speed slider to high or unthrottled speeds (low millisecond delay)? → A: Option A (Dynamic Animation Scaling: animation durations scale down proportionally with the speed slider, smoothly transitioning to instant card placement at 0 ms delay).
- Q: What summary metrics should be displayed inside the completion dialog alongside the success message before the action buttons? → A: Option A (Tri-Player Summary Table: shows Final Bankroll, Net P/L ($), Win Rate %, and Basic Strategy Agreement % for Jev, Laya, and Basic Strategy).
- Q: How should player selection work on the configuration form and in the visualizer when a player is deselected? → A: The form provides toggles to enable/disable each player (Jev, Laya, Basic Strategy). If selected, the player is instantiated and runs normally. If deselected, the visualizer shows that player's column as an empty table with its carpet background color (no card animations) and its live stats are darkened/dimmed as disabled.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interactive Rule Configuration & Dual-Path Simulation Launch (Priority: P1)

As a researcher or blackjack analyst, I want to configure the game variant rules and choose between a fast-batch execution or an interactive real-time visualizer so that I can either collect simulation data immediately or observe decision-making dynamics in detail.

**Why this priority**: Without the ability to define table parameters and start a simulation through both operational paths, no other visualization or data collection workflows can occur.

**Independent Test**: The user fills in the variant rules form on the startup screen, selects "Fast Batch" or "Real-Time Visualizer", submits the form, and the system verifies all input constraints and initiates the simulation via the backend API.

**Acceptance Scenarios**:
1. **Given** the user opens the frontend application, **When** the startup screen loads, **Then** an interactive configuration form presents all variant rules from `Reglas de BlackJack.md` (Soft 17, Natural BJ payout, Peek/ENHC, Insurance, Surrender, DAS, Splits/RSA, Shoe/Decks, Penetration, Burn cards, Bankroll, Bet limits, Round count, Seed) along with global buttons to export the full database or delete/clear all database records.
2. **Given** a correctly filled configuration form, **When** the user submits selecting Path 1 ("Fast Batch / Immediate Data"), **Then** the application displays a focused progress card showing the current round count (e.g., "Round 450/1,000"), an animated percentage progress bar, and a "Cancel" button to abort if needed, running as fast as possible without card animations until completion.
3. **Given** a correctly filled configuration form, **When** the user submits selecting Path 2 ("Real-Time Visualizer"), **Then** the application navigates immediately to the live 2x3 grid arena and begins streaming round events.
4. **Given** invalid rule values (such as minimum bet greater than maximum bet or negative bankroll), **When** the user attempts to submit, **Then** inline validation errors prevent submission and highlight the invalid fields.
5. **Given** the configuration form, **When** the user toggles "Mock Mode", **Then** the simulation executes using deterministic mock agent responses without requiring external Jev API keys or an active local Laya inference service.
6. **Given** the configuration form, **When** configuring players, **Then** individual toggle options allow enabling or disabling each player (Jev, Laya, Basic Strategy), requiring at least one player to remain active.

---

### User Story 2 - Real-Time Tri-Entity Table Visualizer (2x3 Grid with Carpet Colors & Card Animations) (Priority: P1)

As an observer analyzing AI decision quality, I want to watch all three players (Jev, Laya, and Basic Strategy) play simultaneously across a synchronized 2 by 3 grid with distinct carpet colors and distinct card animations so that I can see every card deal, split, surrender, and double down in real time.

**Why this priority**: The core comparative visual purpose of the application is observing how Jev and Laya behave compared to mathematical Basic Strategy on identical initial shoes.

**Independent Test**: Running a visual simulation displays 3 player columns with the top row showing card animations over custom carpet colors, specifically rotating doubled cards horizontally (90 degrees).

**Acceptance Scenarios**:
1. **Given** an active visual simulation, **When** viewing the 2x3 grid, **Then** three columns are displayed for **Jev** (Column 1), **Laya** (Column 2), and **Basic Strategy** (Column 3).
2. **Given** the top row of each column, **When** rendered on screen, **Then** each player's table area displays its specific carpet background color:
   - Jev: `rgb(213, 120, 190)`
   - Laya: `rgb(68, 120, 208)`
   - Basic Strategy: `rgb(118, 194, 154)`
3. **Given** a player receives cards during deal or hit, **When** the card event arrives, **Then** a deal animation places the card face-up on the table (with the dealer hole card kept face-down until revealed if American Peek applies).
4. **Given** a player executes a **Double Down** action, **When** the double down card is dealt, **Then** that third card is animated and oriented **horizontally** (rotated 90 degrees) instead of vertically.
5. **Given** a player executes a **Split** action, **When** the split event arrives, **Then** the initial pair splits into two distinct hand slots with subsequent cards dealt sequentially.
6. **Given** a player executes a **Surrender** action, **When** the surrender event arrives, **Then** a surrender indicator/animation marks the hand as forfeited with half the stake returned.
7. **Given** the user adjusts the speed slider, **When** game pacing is accelerated, **Then** card deal and action animation durations dynamically scale down proportionally, rendering cards instantly without delay when the slider is set to 0 ms.
8. **Given** a player is deselected in the configuration form, **When** the 2x3 grid visualizer renders, **Then** that player's column displays an empty table showing only its carpet background color without any card animations, and its bottom stats area is rendered in a darkened/dimmed disabled state.

---

### User Story 3 - Live Player Stats, AI vs Basic Strategy Comparisons, & Real-Time Graph Bars (Priority: P2)

As an evaluator, I want the bottom row of each player column to display real-time tactical statistics, current bet amount, the AI's chosen action, bankroll delta, optimal strategy agreement comparisons, and dynamic graph bars so that I can evaluate decision accuracy at a glance.

**Why this priority**: Real-time analytical stats allow users to understand *why* players are winning or losing and immediately detect deviations from basic strategy without waiting for final reports.

**Independent Test**: During round execution, inspect the bottom row of each column and verify the current bet, action badge, bankroll state (`+$50`), and animated graph bars update dynamically with each turn and settlement.

**Acceptance Scenarios**:
1. **Given** an active round, **When** viewing the bottom row of each column, **Then** the top of the stats section displays the **current bet** (e.g., `$20`) and directly next to it the **chosen decision** (e.g., `Action: HIT`).
2. **Given** an AI player makes an action decision, **When** the comparison against basic strategy is received, **Then** the stats section displays whether the decision matches optimal play along with the recommended action and strategy category (Hard Total, Soft Total, Pair Split, Surrender).
3. **Given** round settlements occur, **When** bankroll changes, **Then** the current bankroll and net delta (e.g., `+$50` or `-$20`) update with real-time colored feedback.
4. **Given** ongoing gameplay, **When** tracking player metrics, **Then** three dynamic real-time graph bars represent (1) Basic Strategy Optimality Rate (% agreement), (2) Win / Loss / Push distribution percentage, and (3) Current bankroll relative to starting bankroll.

---

### User Story 4 - Live Interactive Flow Controls & Speed Adjustment (Priority: P2)

As a researcher, I want a control bar at the bottom of the visualizer to pause, resume, change playback speed with a slider range bar, cancel/stop the run, or export the database so that I have full interactive control over the simulation pace.

**Why this priority**: Users must be able to slow down to inspect critical decisions or speed up through repetitive hands, as well as halt simulations when desired.

**Independent Test**: Moving the speed range bar dynamically updates the delay between rounds, clicking Pause suspends play across all tables, and clicking Resume or Stop transitions state accordingly.

**Acceptance Scenarios**:
1. **Given** a running simulation, **When** the user clicks the "Pause" button, **Then** the simulation suspends execution synchronously at the current action boundary and the button toggles to "Resume".
2. **Given** a paused simulation, **When** the user clicks "Resume", **Then** the simulation continues execution seamlessly.
3. **Given** an active simulation, **When** the user adjusts the speed range bar (slider), **Then** the pacing delay updates dynamically (from 0 ms to 2,000 ms) without requiring a restart.
4. **Given** an active simulation, **When** the user clicks "Cancel / Stop", **Then** the simulation halts and finalizes metrics.
5. **Given** the control bar, **When** the user clicks "Export Database", **Then** a download of the full database archive is initiated.

---

### User Story 5 - Fault Notification & Quick-Action Recovery (RNF-02 Compliance) (Priority: P2)

As a user running AI simulations, I want clear alert notifications with simple explanations when an external model experiences an error (e.g., network timeout), with a quick "Retry" button when recoverable, so that network hiccups do not corrupt the simulation state.

**Why this priority**: External AI APIs (such as TypeSafe Jev) or local endpoints (Laya) may encounter rate limits or timeouts. The simulation must not crash or lose in-flight data.

**Independent Test**: Triggering an AI timeout halts all tables in `PAUSED_ERROR`, displays a clear alert notification with the error explanation and a "Retry" button, and clicking "Retry" resumes play cleanly.

**Acceptance Scenarios**:
1. **Given** an external AI failure or timeout (e.g., Jev times out), **When** the backend signals `PAUSED_ERROR`, **Then** the visualizer immediately pauses all tables and displays an alert notification containing a simple explanation (e.g., "Timeout error for Jev").
2. **Given** a recoverable error (such as a transient timeout or rate limit), **When** the alert notification appears, **Then** a "Retry" button is displayed to quickly retry the failed action.
3. **Given** an unrecoverable error (e.g., missing API key or fatal configuration), **When** the alert notification appears, **Then** no quick retry button is shown, displaying only an option to abort or view error details.
4. **Given** the user clicks "Retry" on a recoverable fault, **When** the backend re-executes the turn successfully, **Then** the alert notification dismisses and normal gameplay resumes.

---

### User Story 6 - Simulation Completion Dialog & Data Export (Priority: P3)

As a user completing a simulation (in either Fast Batch or Visualizer path), I want to be redirected to a completion page with a clear success dialog offering two primary action buttons: export the simulation data and return to the form for another run.

**Why this priority**: Provides a clean end-to-end journey closure, ensuring researchers immediately obtain exported artifacts and can configure another experiment.

**Independent Test**: Letting a simulation reach its target rounds opens the completion page dialog, allowing one-click JSON data export and a clean return to the configuration form.

**Acceptance Scenarios**:
1. **Given** a simulation finishes all configured rounds (in either Path 1 Fast Batch or Path 2 Real-Time Visualizer), **When** the final round settles, **Then** the application navigates to a completion page displaying a success dialog with a Tri-Player summary table (Final Bankroll, Net P/L, Win Rate %, and Basic Strategy Agreement % for Jev, Laya, and Basic Strategy) alongside the success message.
2. **Given** the completion dialog, **When** the user clicks the first action button ("Export Simulation Data"), **Then** the complete hierarchical JSON dataset for that simulation run is downloaded to the user's browser.
3. **Given** the completion dialog, **When** the user clicks the second action button ("New Simulation"), **Then** the user is redirected back to the initial configuration form with default or preserved settings to start a new experiment.

---

### User Story 7 - Database Maintenance & Archival at Startup (Priority: P3)

As an administrator or researcher starting the application, I want global controls on the startup screen to export the entire database archive or delete all records so that I can keep local storage organized and archive past research batches.

**Why this priority**: Necessary for storage hygiene and offline data warehousing across multiple multi-round experimental sessions.

**Independent Test**: Clicking "Export Whole Database" downloads the full database archive, and clicking "Delete Database" prompts for confirmation before purging all records.

**Acceptance Scenarios**:
1. **Given** the startup screen, **When** the user clicks "Export Whole Database", **Then** the browser downloads the complete historical JSON archive (`/api/export/database`).
2. **Given** the startup screen, **When** the user clicks "Delete Database", **Then** a confirmation dialog warns the user and requires explicit confirmation.
3. **Given** confirmed deletion, **When** the backend truncates all 15 relational tables, **Then** a success confirmation notifies the user that the database has been cleared.

---

### Edge Cases

- **Double Down on Split Hand**: If rules allow Double After Split (DAS), the card dealt for the double must orient horizontally on that specific split hand without affecting the other split hand.
- **Player Bankruptcy Before Max Rounds**: If one player goes bankrupt (bankroll below table minimum), that player's table displays a "Bankrupt" indicator while peer tables continue playing until all are bankrupt or max rounds are reached.
- **Immediate Fast Batch Error**: If an error occurs during Path 1 (Fast Batch), an error alert notification displays the error message with appropriate retry or abort options instead of silently hanging.
- **Window Resize & Responsive Display**: On narrower desktop screens, the 2x3 grid maintains column alignment for each player, scaling cards and stats proportionally without breaking horizontal double card layouts.
- **Mid-Round Pause & Resume**: Pausing while cards are dealing allows the current dealing animation to finish smoothly before freezing the game state at the turn boundary.
- **Attempting Database Delete during Active Run**: If a user attempts to purge the database while a simulation is actively running, the operation is blocked with a user-friendly conflict warning.
- **All Players Deselected**: Form validation prevents submission if zero players are selected, displaying an error requiring at least one active player.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display an initial configuration form presenting all blackjack variant rules specified in `docs/Reglas de BlackJack.md`:
  - Dealer Soft 17 rule (`S17` vs `H17`)
  - Natural Blackjack payout ratio (`3:2`, `6:5`, `1:1`)
  - Hole Card / Peek rule (`American Peek` vs `European No Hole Card`)
  - Insurance rule (Allowed / Prohibited)
  - Surrender rule (`Late Surrender`, `Early Surrender`, `No Surrender`)
  - Double After Split (`DAS` Allowed / Prohibited)
  - Resplit maximum hands limit (1 to 4)
  - Resplit Aces (`RSA` Allowed / Prohibited)
  - Hit Split Aces (Allowed / Prohibited)
  - Number of decks in shoe (1, 2, 4, 6, 8)
  - Shoe cut-card penetration (50% to 85%)
  - Burn cards count (0 to 5)
  - Initial bankroll per player (minimum $10)
  - Table minimum and maximum bet limits
  - Total rounds count (1 to 100,000)
  - Optional deterministic random seed
  - Optional Mock Mode toggle (defaulting to Live models) for offline testing without external AI dependencies
  - Individual player selection toggles for Jev, Laya, and Basic Strategy (requiring at least one active player; defaults to all three selected)
- **FR-002**: System MUST validate all form fields prior to submission, displaying immediate inline validation messages for out-of-bound inputs.
- **FR-003**: System MUST provide two distinct execution paths upon form submission:
  - **Path 1 (Fast Batch)**: Submits configuration and runs simulation without animations or live rendering, displaying a focused progress card with real-time round progress (e.g., "Round 450/1,000"), an animated percentage progress bar, and a "Cancel" button, retrieving final data as quickly as possible.
  - **Path 2 (Real-Time Visualizer)**: Submits configuration and immediately opens the live synchronized 2x3 grid arena.
- **FR-004**: System MUST render Path 2 using a **2 by 3 grid layout**, with one column dedicated to each player:
  - Column 1: **Jev**
  - Column 2: **Laya**
  - Column 3: **Basic Strategy**
  - If any player is deselected in configuration, that player's column MUST render as an empty table: the top row displays only the player's carpet background color without any card animations, and the bottom row renders the stats in a darkened, disabled visual state.
- **FR-005**: System MUST render the **top row** of each column with distinct carpet background colors simulating casino tables:
  - Jev: `rgb(213, 120, 190)`
  - Laya: `rgb(68, 120, 208)`
  - Basic Strategy: `rgb(118, 194, 154)`
- **FR-006**: System MUST animate game cards in the top row for each player action:
  - Initial deal animation for player and dealer cards
  - Hit card deal animation
  - **Double Down animation orienting the dealt card horizontally (90-degree rotation)**
  - Split animation dividing the pair into two distinct playable hand slots
  - Surrender visual indicator marking the hand as forfeited
  - Card animation durations MUST scale dynamically with the speed slider, transitioning smoothly to instant card placement at 0 ms delay to prevent visual lag or frame queuing.
- **FR-007**: System MUST render the **bottom row** of each column displaying the player's live statistics:
  - Top header of stats displaying **Current Bet** and directly adjacent **Decision Made** (e.g., `Action: HIT`)
  - Bankroll state with real-time net profit/loss indicator (e.g., `+$50`)
  - AI decision comparison indicating agreement or deviation against Basic Strategy
  - Three dynamic real-time graph bars visualizing:
    1. Basic Strategy Optimality Rate (% agreement)
    2. Win / Loss / Push distribution percentage
    3. Current bankroll relative to starting bankroll
- **FR-008**: System MUST provide a bottom user control section in Path 2 featuring:
  - Pause / Resume toggle button
  - Range bar (slider) to dynamically change game speed / delay
  - Cancel / Stop button
  - Export Database button
- **FR-009**: System MUST provide global database management actions on the initial screen:
  - "Export Whole Database" button to download the entire historical archive
  - "Delete Database" button with confirmation modal to purge all database records
- **FR-010**: System MUST handle operational errors by pausing visualization and displaying an alert notification with a simple explanation of the failure (e.g., "Timeout error for Jev").
- **FR-011**: If an error is recoverable (e.g., network timeout or rate limit), the alert notification MUST display a "Retry" button to resume the simulation; if unrecoverable, no retry button shall be displayed.
- **FR-012**: Upon simulation completion (in either Path 1 or Path 2), the system MUST navigate to a completion page displaying a success dialog with a Tri-Player summary table (Final Bankroll, Net P/L, Win Rate %, and Basic Strategy Agreement % for Jev, Laya, and Basic Strategy).
- **FR-013**: The completion dialog MUST display exactly two primary action buttons:
  - Button 1: "Export Simulation Data" (downloads the run's JSON data)
  - Button 2: "New Simulation" (redirects back to the initial configuration form)

---

### Key Entities

- **VariantRules**: The complete set of user-configurable blackjack table rules and boundaries (S17/H17, BJ payout, peek rule, surrender, DAS, splits, decks, penetration, burn cards, bankroll, bets).
- **SimulationSetup**: The operational parameters for a run (round count, execution mode [Fast Batch vs Real-Time Visualizer], random seed, speed delay).
- **PlayerColumnState**: The visual and statistical state of a player table at round $N$:
  - `is_selected`: Boolean indicating whether the player was chosen for this run; when false, renders an empty table with carpet color and darkened/disabled stats
  - Carpet color (`rgb(213, 120, 190)` for Jev, `rgb(68, 120, 208)` for Laya, `rgb(118, 194, 154)` for Basic Strategy)
  - Active cards and hand orientation (horizontal on double down)
  - Current bet and current action decision
  - Bankroll and net profit delta
  - Optimal strategy agreement comparison
  - Real-time graph bars data: Basic Strategy Optimality Rate %, Win/Loss/Push %, and Bankroll relative to starting bankroll
- **SimulationRunResult**: The final dataset produced upon completion, containing total rounds, win/loss tallies, net profit/loss, strategy agreement percentages, and individual round timelines.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure and launch a complete blackjack simulation across all variant rules in under 60 seconds from app startup.
- **SC-002**: In Path 2 (Real-Time Visualizer), visual card dealing, doubling, and stat updates render with a perceived UI latency under 200 ms from event receipt.
- **SC-003**: Doubled cards are unambiguously rendered horizontally (rotated 90 degrees) in 100% of double down occurrences across all active tables.
- **SC-004**: Each table carpet displays its exact required color value: Jev `rgb(213, 120, 190)`, Laya `rgb(68, 120, 208)`, Basic Strategy `rgb(118, 194, 154)`.
- **SC-005**: Adjusting the speed range bar alters game pacing smoothly between 0 ms and 2,000 ms, scaling animation durations proportionally down to instant placement at 0 ms without dropping game frames or triggering desynchronization.
- **SC-006**: When an external AI error occurs, 100% of cases pause the visualizer, preserve collected state, and present an actionable alert with a retry button when recoverable.
- **SC-007**: Upon simulation completion in both Fast Batch and Visualizer paths, users are transitioned to the completion dialog with functional "Export Simulation Data" and "New Simulation" buttons.

---

## Assumptions

- The backend FastAPI application is running locally or via Docker Compose and exposes standard REST and WebSocket endpoints on port 8000.
- Browser environment is a modern Chromium, WebKit, or Gecko desktop browser with JavaScript enabled and standard WebSocket support.
- Screen resolution is optimized for standard desktop displays (1280x800 and above) to accommodate the 2 by 3 grid layout with 3 simultaneous player columns.
- Card assets can be rendered cleanly using styled HTML/CSS elements with suit symbols (`♠`, `♥`, `♦`, `♣`) and rotation transforms.
- Exported files are provided as `.json` attachments directly downloadable via browser standard download mechanics.
