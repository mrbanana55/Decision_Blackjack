# Quickstart & Verification Guide: Decision Blackjack Frontend Web Application

**Feature**: `008-frontend-web-application`  
**Date**: 2026-10-13  
**Status**: Draft  

---

## Prerequisites

1. **Backend Running**:
   Ensure backend FastAPI service is running locally on port 8000:
   ```bash
   cd backend && python3 -m uvicorn app.main:app --port 8000
   ```
2. **Frontend Dependencies**:
   Ensure dependencies are installed in `frontend/`:
   ```bash
   cd frontend && npm install
   ```
3. **Launch Dev Server**:
   ```bash
   cd frontend && npm run dev
   ```
   Open `http://localhost:5173` in any modern web browser.

---

## Scenario 1: Variant Rules Form & Fast Batch Execution (Path 1)

1. Open `http://localhost:5173`.
2. Inspect the configuration form:
   - Change Soft 17 to `H17`, Decks to `6`, Rounds to `100`.
   - Ensure "Fast Batch" execution mode is selected.
   - Leave Mock Mode toggled ON (for instant execution).
3. Click **"Launch Simulation"**.
4. **Verification**:
   - The browser navigates to `/batch/:sessionId`.
   - A focused progress card displays "Simulating: Round X of 100" with an animated progress bar.
   - Upon completion, the page automatically navigates to `/complete/:sessionId` displaying the completion success dialog.

---

## Scenario 2: Real-Time Tri-Entity Visualizer (Path 2) with 2x3 Grid

1. On the configuration form (`/`), select **"Real-Time Visualizer"**.
2. Keep all three players (Jev, Laya, Basic Strategy) selected.
3. Set rounds to `10`, delay to `400 ms`, and click **"Launch Simulation"**.
4. **Verification**:
   - The browser navigates to `/simulate/:sessionId`.
   - Three columns are displayed:
     - **Column 1 (Jev)**: Top row table carpet is `rgb(213, 120, 190)`.
     - **Column 2 (Laya)**: Top row table carpet is `rgb(68, 120, 208)`.
     - **Column 3 (Basic Strategy)**: Top row table carpet is `rgb(118, 194, 154)`.
   - GSAP animations slide cards from the shoe into dealer and player positions.
   - Whenever an entity executes a **Double Down**, the dealt card is rotated **horizontally** (90 degrees).
   - Bottom row displays:
     - Top line: `Current Bet: $X` and `Action: [HIT/STAND/DOUBLE]`.
     - Basic strategy comparison badge.
     - Real-time bankroll with delta (`+$X`).
     - **Three dynamic graph bars**: (1) Optimality Rate %, (2) Win/Loss/Push %, (3) Relative Bankroll %.

---

## Scenario 3: Deselected Player Empty Table & Darkened Stats

1. On the configuration form, uncheck **Laya** (so only Jev and Basic Strategy are active).
2. Click **"Launch Simulation"** in Real-Time Visualizer mode.
3. **Verification**:
   - Column 2 (Laya) renders as an **empty table**:
     - Top row shows only the blue carpet background `rgb(68, 120, 208)` with zero card animations.
     - Bottom row stats are visually dimmed/darkened (`opacity-40 grayscale`).
   - Columns 1 (Jev) and 3 (Basic Strategy) play and animate normally.

---

## Scenario 4: Dynamic Speed Slider Pacing Scaling

1. During an active visual simulation, locate the range bar slider in the bottom control bar.
2. Drag the slider from `400 ms` to `0 ms` (Maximum Speed).
3. **Verification**:
   - Pacing instantly accelerates without page reload.
   - Card animation durations smoothly scale down to 0 ms, instantly placing cards without lagging or queueing.
4. Drag slider to `1,000 ms`.
5. **Verification**:
   - Pacing slows down, and deal animations scale up smoothly.

---

## Scenario 5: External AI Provider Fault & Recovery (RNF-02)

1. Run a simulation in Live mode (with an unconfigured or blocked Jev API key, or trigger `PAUSED_ERROR`).
2. **Verification**:
   - The visualizer pauses all tables immediately.
   - An alert dialog pops up with a simple explanation: `"Timeout error for Jev"`.
   - An actionable **"Retry Turn"** button is displayed.
   - Clicking "Retry Turn" re-invokes the turn; clicking "Abort" cleanly exits back to the configuration form.

---

## Scenario 6: Completion Page Success Dialog & Actions

1. Let any simulation reach its target rounds.
2. **Verification**:
   - The page transitions to `/complete/:sessionId`.
   - A success dialog states that the simulation completed successfully.
   - A **Tri-Player Summary Table** shows Final Bankroll, Net P/L, Win Rate %, and Basic Strategy Agreement % for each player.
   - Click **"Export Simulation Data"**: The browser downloads the simulation's JSON file (`/api/export/simulations/{id}`).
   - Click **"New Simulation"**: The browser navigates back to `/` ready for another experiment.

---

## Scenario 7: Startup Database Tools

1. On the home page (`/`), locate the global database buttons in the header:
2. Click **"Export Whole Database"**:
   - The browser downloads the complete historical JSON archive (`/api/export/database`).
3. Click **"Delete Database"**:
   - An alert dialog warns the user and requests confirmation.
   - Upon confirmation, all 15 tables are cleared via `DELETE /api/database`.
