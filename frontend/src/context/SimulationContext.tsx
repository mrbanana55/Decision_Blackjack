import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import {
  EntityId,
  PlayerTableState,
  SimulationSessionState,
  VariantRulesFormValues,
  DEFAULT_VARIANT_RULES,
  CardVisualState,
} from '../types/simulation';
import {
  CreateSimulationPayload,
  InboundTelemetryEvent,
  SimulationResponse,
} from '../types/api';
import { apiClient } from '../services/apiClient';
import { websocketService } from '../services/websocketService';
import { resolveCardAsset, calculateCardsTotal } from '../lib/cardAssets';

interface SimulationContextValue {
  session: SimulationSessionState;
  createAndLaunchSimulation: (
    formValues: VariantRulesFormValues
  ) => Promise<SimulationResponse>;
  connectSession: (sessionId: string, initialRules?: VariantRulesFormValues) => void;
  disconnectSession: () => void;
  pause: () => void;
  resume: () => void;
  step: (level?: 'round' | 'turn') => void;
  retry: (entityId?: string) => void;
  stop: () => void;
  setSpeed: (delayMs: number) => void;
  exportSimulation: () => Promise<void>;
  clearFault: () => void;
}

const initialTable = (
  entity_id: EntityId,
  name: string,
  carpet_color: string,
  initialBankroll: number = 1000.0,
  isSelected: boolean = true,
  minBet: number = 10.0
): PlayerTableState => ({
  entity_id,
  name,
  carpet_color,
  is_selected: isSelected,
  is_bankrupt: false,
  shoe_generation: 1,
  is_shuffling: false,
  cards_remaining: 312,
  running_count: 0,
  true_count: 0.0,
  dealer_cards: [],
  dealer_total: 0,
  dealer_is_busted: false,
  player_hands: [
    {
      hand_id: `${entity_id}-hand-0`,
      cards: [],
      total: 0,
      is_soft: false,
      is_busted: false,
      is_blackjack: false,
      is_doubled: false,
      is_surrendered: false,
    },
  ],
  active_hand_index: 0,
  current_bet: minBet,
  last_action: null,
  last_comparison: null,
  current_bankroll: initialBankroll,
  starting_bankroll: initialBankroll,
  net_profit_delta: 0,
  optimality_rate: 1.0,
  win_loss_push: {
    wins: 0,
    losses: 0,
    pushes: 0,
    total: 0,
  },
  relative_bankroll_pct: 100,
});

const initialSessionState: SimulationSessionState = {
  session_id: null,
  run_id: null,
  status: 'INITIALIZING',
  execution_mode: 'visualized',
  current_round: 0,
  max_rounds: 100,
  shoe_generation: 1,
  delay_ms: 300,
  rules: null,
  tables: {
    jev: initialTable('jev', 'Jev (System One)', 'rgb(213, 120, 190)', 1000, true, 10),
    laya: initialTable('laya', 'Laya (Local)', 'rgb(68, 120, 208)', 1000, true, 10),
    optimal: initialTable('optimal', 'Basic Strategy', 'rgb(118, 194, 154)', 1000, true, 10),
  },
  active_fault: null,
  completion_summary: null,
};

const SimulationContext = createContext<SimulationContextValue | null>(null);

export const SimulationProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [session, setSession] = useState<SimulationSessionState>(initialSessionState);
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const handleInboundEvent = useCallback((event: InboundTelemetryEvent) => {
    const type = event.event_type;
    const payload: any = event.payload || {};

    setSession((prev) => {
      switch (type) {
        case 'SESSION_SNAPSHOT': {
          const rawTables = payload.tables || {};
          const entities: string[] = payload.entities || ['jev', 'laya', 'optimal'];
          const deviations = payload.deviations || {};
          const defaultMinBet = prev.rules?.min_bet || 10;

          const updatedTables = { ...prev.tables };
          (['jev', 'laya', 'optimal'] as EntityId[]).forEach((ent) => {
            const tableData = rawTables[ent];
            const isEntityActive = entities.includes(ent);
            const dev = deviations[ent];

            const current = updatedTables[ent];
            const starting = current.starting_bankroll || tableData?.bankroll || 1000;
            const currentBk = tableData?.bankroll ?? current.current_bankroll;

            const devOpt =
              dev?.optimality_rate ??
              dev?.agreement_rate ??
              current.optimality_rate ??
              1.0;
            const safeOpt = Number.isFinite(devOpt) ? devOpt : 1.0;
            const shoeGen = Number(
              tableData?.shoe_generation ?? current.shoe_generation ?? 1
            );

            updatedTables[ent] = {
              ...current,
              is_selected: isEntityActive,
              current_bankroll: currentBk,
              starting_bankroll: starting,
              current_bet: defaultMinBet,
              shoe_generation: shoeGen,
              is_shuffling: false,
              cards_remaining: tableData?.cards_remaining ?? current.cards_remaining ?? 312,
              running_count: tableData?.running_count ?? current.running_count ?? 0,
              true_count: tableData?.true_count ?? current.true_count ?? 0.0,
              optimality_rate: safeOpt,
              relative_bankroll_pct: starting > 0 ? (currentBk / starting) * 100 : 100,
            };
          });

          const maxShoeGen = Math.max(
            prev.shoe_generation || 1,
            ...Object.values(updatedTables).map((t) => t.shoe_generation || 1)
          );

          return {
            ...prev,
            shoe_generation: maxShoeGen,
            status:
              payload.status === 'RUNNING'
                ? 'RUNNING'
                : payload.status === 'PAUSED'
                ? 'PAUSED'
                : prev.status,
            current_round: payload.current_round ?? prev.current_round,
            max_rounds: payload.max_rounds ?? prev.max_rounds,
            delay_ms: payload.delay_ms ?? prev.delay_ms,
            tables: updatedTables,
          };
        }

        case 'ROUND_STARTED': {
          const roundNum = event.round_number || (payload.round_number ?? prev.current_round + 1);
          const defaultMinBet = prev.rules?.min_bet || 10;
          const updatedTables = { ...prev.tables };

          (['jev', 'laya', 'optimal'] as EntityId[]).forEach((ent) => {
            const tbl = updatedTables[ent];
            updatedTables[ent] = {
              ...tbl,
              current_bet: defaultMinBet,
              dealer_cards: [],
              dealer_total: 0,
              dealer_is_busted: false,
              player_hands: [
                {
                  hand_id: `${ent}-hand-0`,
                  cards: [],
                  total: 0,
                  is_soft: false,
                  is_busted: false,
                  is_blackjack: false,
                  is_doubled: false,
                  is_surrendered: false,
                },
              ],
              active_hand_index: 0,
              last_action: null,
            };
          });

          return {
            ...prev,
            current_round: roundNum,
            status: prev.status === 'INITIALIZING' ? 'RUNNING' : prev.status,
            tables: updatedTables,
          };
        }

        case 'CARD_DEALT': {
          const updatedTables = { ...prev.tables };

          // Format A: Orchestrator table deal event
          if (payload.entity_id) {
            const ent = payload.entity_id as EntityId;
            if (['jev', 'laya', 'optimal'].includes(ent) && updatedTables[ent]) {
              const tbl = updatedTables[ent];

              // Update bet
              const bet = payload.current_bet ?? prev.rules?.min_bet ?? tbl.current_bet ?? 10;

              // Player cards
              let playerHands = tbl.player_hands;
              if (payload.player_cards && Array.isArray(payload.player_cards)) {
                const cardItems: CardVisualState[] = payload.player_cards.map(
                  (cs: string, idx: number) => {
                    const parsed = resolveCardAsset(cs);
                    return {
                      id: `card-${ent}-0-${idx}-${cs}`,
                      card_str: cs,
                      rank: parsed.rank,
                      suit: parsed.suit,
                      svg_path: parsed.svgUrl,
                      is_hidden: false,
                      is_horizontal: false,
                      is_split: false,
                    };
                  }
                );
                const totals = calculateCardsTotal(payload.player_cards);
                playerHands = [
                  {
                    hand_id: `${ent}-hand-0`,
                    cards: cardItems,
                    total: totals.total,
                    is_soft: totals.is_soft,
                    is_busted: totals.is_busted,
                    is_blackjack: totals.total === 21 && cardItems.length === 2,
                    is_doubled: false,
                    is_surrendered: false,
                  },
                ];
              }

              // Dealer cards
              let dealerCards = tbl.dealer_cards;
              let dealerTotal = tbl.dealer_total;
              const upcardStr = payload.dealer_upcard as string;

              if (
                payload.dealer_cards &&
                Array.isArray(payload.dealer_cards) &&
                payload.dealer_cards.length > 0
              ) {
                dealerCards = payload.dealer_cards.map((cs: string, idx: number) => {
                  const parsed = resolveCardAsset(cs);
                  const isHole = idx > 0;
                  return {
                    id: `card-dealer-${ent}-${idx}-${cs}`,
                    card_str: cs,
                    rank: parsed.rank,
                    suit: parsed.suit,
                    svg_path: parsed.svgUrl,
                    is_hidden: isHole,
                    is_horizontal: false,
                    is_split: false,
                  };
                });
                dealerTotal = calculateCardsTotal([payload.dealer_cards[0]]).total;
              } else if (upcardStr) {
                const parsedUp = resolveCardAsset(upcardStr);
                const parsedHole = resolveCardAsset('?');
                dealerCards = [
                  {
                    id: `card-dealer-${ent}-0-${upcardStr}`,
                    card_str: upcardStr,
                    rank: parsedUp.rank,
                    suit: parsedUp.suit,
                    svg_path: parsedUp.svgUrl,
                    is_hidden: false,
                    is_horizontal: false,
                    is_split: false,
                  },
                  {
                    id: `card-dealer-${ent}-1-hole`,
                    card_str: '?',
                    rank: '?',
                    suit: 'spades',
                    svg_path: parsedHole.svgUrl,
                    is_hidden: true,
                    is_horizontal: false,
                    is_split: false,
                  },
                ];
                dealerTotal = calculateCardsTotal([upcardStr]).total;
              }

              const shoeGen = Number(
                payload.shoe_generation ?? tbl.shoe_generation ?? 1
              );

              updatedTables[ent] = {
                ...tbl,
                current_bet: bet,
                player_hands: playerHands,
                dealer_cards: dealerCards,
                dealer_total: dealerTotal,
                shoe_generation: shoeGen,
                is_shuffling: false,
                cards_remaining: Number(payload.cards_remaining ?? tbl.cards_remaining ?? 312),
                running_count: Number(payload.running_count ?? tbl.running_count ?? 0),
                true_count: Number(payload.true_count ?? tbl.true_count ?? 0.0),
              };
            }
          }
          // Format B: Individual card deal event
          else if (payload.recipient) {
            const recipient = payload.recipient;
            const cardStr = payload.card || '';
            const parsed = resolveCardAsset(cardStr);
            const isHole = Boolean(payload.is_hole_card);
            const isDouble = Boolean(payload.is_double_down);
            const handIndex = payload.hand_index ?? 0;

            if (recipient === 'dealer') {
              (['jev', 'laya', 'optimal'] as EntityId[]).forEach((ent) => {
                const tbl = updatedTables[ent];
                const cardItem: CardVisualState = {
                  id: `card-dealer-${ent}-${tbl.dealer_cards.length}-${cardStr}`,
                  card_str: cardStr,
                  rank: parsed.rank,
                  suit: parsed.suit,
                  svg_path: parsed.svgUrl,
                  is_hidden: isHole,
                  is_horizontal: false,
                  is_split: false,
                };
                updatedTables[ent] = {
                  ...tbl,
                  dealer_cards: [...tbl.dealer_cards, cardItem],
                  dealer_total: payload.total ?? tbl.dealer_total,
                  dealer_is_busted: Boolean(payload.is_busted),
                };
              });
            } else if (['jev', 'laya', 'optimal'].includes(recipient)) {
              const ent = recipient as EntityId;
              const tbl = updatedTables[ent];
              const hands = [...tbl.player_hands];
              while (hands.length <= handIndex) {
                hands.push({
                  hand_id: `${ent}-hand-${hands.length}`,
                  cards: [],
                  total: 0,
                  is_soft: false,
                  is_busted: false,
                  is_blackjack: false,
                  is_doubled: false,
                  is_surrendered: false,
                });
              }
              const currentHand = hands[handIndex];
              const cardItem: CardVisualState = {
                id: `card-${ent}-${handIndex}-${currentHand.cards.length}-${cardStr}`,
                card_str: cardStr,
                rank: parsed.rank,
                suit: parsed.suit,
                svg_path: parsed.svgUrl,
                is_hidden: false,
                is_horizontal: isDouble,
                is_split: hands.length > 1,
              };
              hands[handIndex] = {
                ...currentHand,
                cards: [...currentHand.cards, cardItem],
                total: payload.total ?? currentHand.total,
                is_soft: Boolean(payload.is_soft),
                is_busted: Boolean(payload.is_busted),
                is_doubled: isDouble || currentHand.is_doubled,
              };
              updatedTables[ent] = {
                ...tbl,
                player_hands: hands,
                active_hand_index: handIndex,
              };
            }
          }

          const maxShoeGen = Math.max(
            prev.shoe_generation || 1,
            ...Object.values(updatedTables).map((t) => t.shoe_generation || 1)
          );

          return {
            ...prev,
            shoe_generation: maxShoeGen,
            tables: updatedTables,
          };
        }

        case 'DECISION_MADE': {
          const ent = payload.entity_id as EntityId;
          if (!ent || !prev.tables[ent]) return prev;

          const tbl = prev.tables[ent];
          const action = payload.action;
          const comparison = payload.comparison ?? {
            is_optimal: payload.is_optimal ?? true,
            optimal_action: payload.optimal_action ?? action,
            category: 'general',
            reasoning: '',
          };

          let newBet = tbl.current_bet;
          if (payload.current_bet) {
            newBet = payload.current_bet;
          } else if (action && action.toUpperCase() === 'DOUBLE') {
            newBet = tbl.current_bet * 2;
          }

          let updatedHands = tbl.player_hands;
          if (payload.player_hands && Array.isArray(payload.player_hands)) {
            updatedHands = payload.player_hands.map((h: any, hIdx: number) => {
              const cardList = (h.cards || []).map((cs: string, cIdx: number) => {
                const parsed = resolveCardAsset(cs);
                const isLast = cIdx === h.cards.length - 1;
                const isDoubled =
                  (Boolean(h.is_doubled) || action?.toUpperCase() === 'DOUBLE') &&
                  isLast &&
                  h.cards.length > 2;
                return {
                  id: `card-${ent}-${hIdx}-${cIdx}-${cs}`,
                  card_str: cs,
                  rank: parsed.rank,
                  suit: parsed.suit,
                  svg_path: parsed.svgUrl,
                  is_hidden: false,
                  is_horizontal: isDoubled,
                  is_split: payload.player_hands.length > 1,
                };
              });
              const totals = calculateCardsTotal(h.cards || []);
              return {
                hand_id: `${ent}-hand-${hIdx}`,
                cards: cardList,
                total: h.total ?? totals.total,
                is_soft: totals.is_soft,
                is_busted: Boolean(h.is_busted ?? totals.is_busted),
                is_blackjack: Boolean(h.is_blackjack),
                is_doubled: Boolean(h.is_doubled || action?.toUpperCase() === 'DOUBLE'),
                is_surrendered: Boolean(action?.toUpperCase() === 'SURRENDER'),
              };
            });
          }

          return {
            ...prev,
            tables: {
              ...prev.tables,
              [ent]: {
                ...tbl,
                last_action: action,
                last_comparison: comparison,
                current_bet: newBet,
                player_hands: updatedHands,
                cards_remaining: Number(payload.cards_remaining ?? tbl.cards_remaining ?? 312),
                running_count: Number(payload.running_count ?? tbl.running_count ?? 0),
                true_count: Number(payload.true_count ?? tbl.true_count ?? 0.0),
              },
            },
          };
        }

        case 'ROUND_SETTLED': {
          const updatedTables = { ...prev.tables };
          const deviations = payload.running_deviations || {};

          // Single entity settlement (emitted by orchestrator per table)
          if (payload.entity_id) {
            const ent = payload.entity_id as EntityId;
            if (['jev', 'laya', 'optimal'].includes(ent) && updatedTables[ent]) {
              const tbl = updatedTables[ent];
              const netDelta = Number(payload.net_profit ?? 0);
              const newBankroll = Number(
                payload.final_bankroll ?? tbl.current_bankroll + netDelta
              );

              const outcomes = payload.outcomes || [];
              const isWin =
                netDelta > 0 ||
                outcomes.some(
                  (o: any) => o.outcome === 'win' || o.outcome === 'blackjack'
                );
              const isLoss =
                netDelta < 0 ||
                outcomes.some(
                  (o: any) => o.outcome === 'loss' || o.outcome === 'surrender'
                );
              const isPush = !isWin && !isLoss;

              const newWins = tbl.win_loss_push.wins + (isWin ? 1 : 0);
              const newLosses = tbl.win_loss_push.losses + (isLoss ? 1 : 0);
              const newPushes = tbl.win_loss_push.pushes + (isPush ? 1 : 0);
              const totalRounds = newWins + newLosses + newPushes;

              const relBankroll =
                tbl.starting_bankroll > 0
                  ? (newBankroll / tbl.starting_bankroll) * 100
                  : 0;

              // Reveal all dealer cards
              let revealedDealerCards = tbl.dealer_cards;
              let dealerTotal = tbl.dealer_total;
              let dealerBusted = tbl.dealer_is_busted;

              if (
                payload.dealer_cards &&
                Array.isArray(payload.dealer_cards) &&
                payload.dealer_cards.length > 0
              ) {
                revealedDealerCards = payload.dealer_cards.map(
                  (cs: string, idx: number) => {
                    const parsed = resolveCardAsset(cs);
                    return {
                      id: `card-dealer-${ent}-${idx}-${cs}`,
                      card_str: cs,
                      rank: parsed.rank,
                      suit: parsed.suit,
                      svg_path: parsed.svgUrl,
                      is_hidden: false,
                      is_horizontal: false,
                      is_split: false,
                    };
                  }
                );
                const dTotals = calculateCardsTotal(payload.dealer_cards);
                dealerTotal = payload.dealer_total ?? dTotals.total;
                dealerBusted = Boolean(payload.dealer_is_busted ?? dTotals.is_busted);
              } else {
                revealedDealerCards = tbl.dealer_cards.map((c) => ({
                  ...c,
                  is_hidden: false,
                }));
              }

              // Update player hands if in settlement payload
              let updatedHands = tbl.player_hands;
              if (payload.player_hands && Array.isArray(payload.player_hands)) {
                updatedHands = payload.player_hands.map((h: any, hIdx: number) => {
                  const cardList = (h.cards || []).map((cs: string, cIdx: number) => {
                    const parsed = resolveCardAsset(cs);
                    const isLast = cIdx === h.cards.length - 1;
                    const isDoubled =
                      Boolean(h.is_doubled) && isLast && h.cards.length > 2;
                    return {
                      id: `card-${ent}-${hIdx}-${cIdx}-${cs}`,
                      card_str: cs,
                      rank: parsed.rank,
                      suit: parsed.suit,
                      svg_path: parsed.svgUrl,
                      is_hidden: false,
                      is_horizontal: isDoubled,
                      is_split: payload.player_hands.length > 1,
                    };
                  });
                  const totals = calculateCardsTotal(h.cards || []);
                  return {
                    hand_id: `${ent}-hand-${hIdx}`,
                    cards: cardList,
                    total: h.total ?? totals.total,
                    is_soft: totals.is_soft,
                    is_busted: Boolean(h.is_busted ?? totals.is_busted),
                    is_blackjack: Boolean(h.is_blackjack),
                    is_doubled: Boolean(h.is_doubled),
                    is_surrendered: false,
                  };
                });
              }

              const dev = deviations[ent];
              const devOpt =
                dev?.optimality_rate ??
                dev?.agreement_rate ??
                tbl.optimality_rate ??
                1.0;
              const safeOpt = Number.isFinite(devOpt) ? devOpt : 1.0;
              const isReshuffling = Boolean(payload.reshuffle_needed);
              const shoeGen = Number(
                payload.shoe_generation ?? tbl.shoe_generation ?? 1
              );

              updatedTables[ent] = {
                ...tbl,
                dealer_cards: revealedDealerCards,
                dealer_total: dealerTotal,
                dealer_is_busted: dealerBusted,
                player_hands: updatedHands,
                current_bankroll: newBankroll,
                net_profit_delta: netDelta,
                is_bankrupt: newBankroll <= 0,
                shoe_generation: shoeGen,
                is_shuffling: isReshuffling || tbl.is_shuffling,
                cards_remaining: Number(payload.cards_remaining ?? tbl.cards_remaining ?? 312),
                running_count: Number(payload.running_count ?? tbl.running_count ?? 0),
                true_count: Number(payload.true_count ?? tbl.true_count ?? 0.0),
                optimality_rate: safeOpt,
                win_loss_push: {
                  wins: newWins,
                  losses: newLosses,
                  pushes: newPushes,
                  total: totalRounds,
                },
                relative_bankroll_pct: relBankroll,
              };
            }
          }
          // Aggregate settlements dictionary format
          else if (payload.settlements) {
            const settlements = payload.settlements || {};
            const dealerCards = payload.dealer_cards || [];

            (['jev', 'laya', 'optimal'] as EntityId[]).forEach((ent) => {
              const tbl = updatedTables[ent];
              const settlement = settlements[ent];
              const dev = deviations[ent];

              const revealedDealerCards = tbl.dealer_cards.map((c, idx) => {
                if (c.is_hidden && dealerCards[idx]) {
                  const parsed = resolveCardAsset(dealerCards[idx]);
                  return {
                    ...c,
                    card_str: dealerCards[idx],
                    rank: parsed.rank,
                    suit: parsed.suit,
                    svg_path: parsed.svgUrl,
                    is_hidden: false,
                  };
                }
                return { ...c, is_hidden: false };
              });

              if (settlement) {
                const newBankroll = Number(settlement.final_bankroll);
                const netDelta = Number(settlement.net_payout);
                const res = settlement.result;

                const newWins =
                  tbl.win_loss_push.wins +
                  (res === 'win' || res === 'blackjack' ? 1 : 0);
                const newLosses =
                  tbl.win_loss_push.losses +
                  (res === 'loss' || res === 'surrender' ? 1 : 0);
                const newPushes =
                  tbl.win_loss_push.pushes + (res === 'push' ? 1 : 0);
                const totalRounds = newWins + newLosses + newPushes;

                const relBankroll =
                  tbl.starting_bankroll > 0
                    ? (newBankroll / tbl.starting_bankroll) * 100
                    : 0;

                const devOpt =
                  dev?.optimality_rate ??
                  dev?.agreement_rate ??
                  tbl.optimality_rate ??
                  1.0;
                const safeOpt = Number.isFinite(devOpt) ? devOpt : 1.0;

                updatedTables[ent] = {
                  ...tbl,
                  dealer_cards: revealedDealerCards,
                  dealer_total: payload.dealer_total ?? tbl.dealer_total,
                  dealer_is_busted: Boolean(payload.dealer_is_busted),
                  current_bankroll: newBankroll,
                  net_profit_delta: netDelta,
                  is_bankrupt: newBankroll <= 0,
                  cards_remaining: Number(payload.cards_remaining ?? tbl.cards_remaining ?? 312),
                  running_count: Number(payload.running_count ?? tbl.running_count ?? 0),
                  true_count: Number(payload.true_count ?? tbl.true_count ?? 0.0),
                  optimality_rate: safeOpt,
                  win_loss_push: {
                    wins: newWins,
                    losses: newLosses,
                    pushes: newPushes,
                    total: totalRounds,
                  },
                  relative_bankroll_pct: relBankroll,
                };
              } else {
                updatedTables[ent] = {
                  ...tbl,
                  dealer_cards: revealedDealerCards,
                  dealer_total: payload.dealer_total ?? tbl.dealer_total,
                  dealer_is_busted: Boolean(payload.dealer_is_busted),
                };
              }
            });
          }

          const maxShoeGen = Math.max(
            prev.shoe_generation || 1,
            ...Object.values(updatedTables).map((t) => t.shoe_generation || 1)
          );

          return {
            ...prev,
            shoe_generation: maxShoeGen,
            tables: updatedTables,
          };
        }

        case 'SHOE_RESHUFFLED': {
          const updatedTables = { ...prev.tables };
          const ent = (payload.entity_id || payload.table_id) as EntityId;
          const shoeGen = Number(payload.shoe_number ?? ((payload.generation ?? 0) + 1));

          if (['jev', 'laya', 'optimal'].includes(ent) && updatedTables[ent]) {
            updatedTables[ent] = {
              ...updatedTables[ent],
              shoe_generation: shoeGen,
              is_shuffling: true,
              cards_remaining: Number(payload.cards_remaining ?? (prev.rules?.num_decks ?? 6) * 52),
              running_count: Number(payload.running_count ?? 0),
              true_count: Number(payload.true_count ?? 0.0),
            };
          } else {
            // Apply to all active tables if not entity-specific
            (['jev', 'laya', 'optimal'] as EntityId[]).forEach((e) => {
              if (updatedTables[e]) {
                updatedTables[e] = {
                  ...updatedTables[e],
                  shoe_generation: shoeGen,
                  is_shuffling: true,
                  cards_remaining: Number(payload.cards_remaining ?? (prev.rules?.num_decks ?? 6) * 52),
                  running_count: Number(payload.running_count ?? 0),
                  true_count: Number(payload.true_count ?? 0.0),
                };
              }
            });
          }

          const maxShoeGen = Math.max(
            prev.shoe_generation || 1,
            ...Object.values(updatedTables).map((t) => t.shoe_generation || 1)
          );

          return {
            ...prev,
            shoe_generation: maxShoeGen,
            tables: updatedTables,
          };
        }

        case 'SESSION_PAUSED':
          return { ...prev, status: 'PAUSED' };

        case 'SESSION_RESUMED':
          return { ...prev, status: 'RUNNING' };

        case 'SPEED_UPDATED':
          return { ...prev, delay_ms: payload.delay_ms ?? prev.delay_ms };

        case 'SESSION_ERROR': {
          return {
            ...prev,
            status: 'PAUSED_ERROR',
            active_fault: {
              entity_id: payload.entity_id || 'unknown',
              error_message: payload.error || payload.error_message || 'Unexpected simulation error',
              is_recoverable: payload.is_recoverable ?? true,
            },
          };
        }

        case 'SESSION_COMPLETED': {
          const finalDevs = payload.final_deviations || {};
          const playersSummary = (['jev', 'laya', 'optimal'] as EntityId[]).reduce(
            (acc, ent) => {
              const tbl = prev.tables[ent];
              const dev = finalDevs[ent];
              const netProfit = tbl.current_bankroll - tbl.starting_bankroll;
              const winRate =
                tbl.win_loss_push.total > 0
                  ? (tbl.win_loss_push.wins / tbl.win_loss_push.total) * 100
                  : 0;

              const rawOpt =
                dev?.optimality_rate ??
                dev?.agreement_rate ??
                tbl.optimality_rate ??
                1.0;
              const safeOpt = Number.isFinite(rawOpt)
                ? rawOpt <= 1.0
                  ? rawOpt * 100
                  : rawOpt
                : 100.0;

              acc[ent] = {
                final_bankroll: tbl.current_bankroll,
                net_profit: netProfit,
                win_rate: winRate,
                optimality_rate: safeOpt,
              };
              return acc;
            },
            {} as any
          );

          return {
            ...prev,
            status: 'COMPLETED',
            completion_summary: {
              total_rounds: payload.total_rounds || prev.current_round,
              players: playersSummary,
            },
          };
        }

        default:
          return prev;
      }
    });
  }, []);

  useEffect(() => {
    const unsubscribe = websocketService.subscribe(handleInboundEvent);
    return () => {
      unsubscribe();
    };
  }, [handleInboundEvent]);

  const connectSession = useCallback(
    (sessionId: string, initialRules?: VariantRulesFormValues) => {
      websocketService.connect(sessionId);
      setSession((prev) => {
        const rules = initialRules || prev.rules || DEFAULT_VARIANT_RULES;
        const initialBankroll = rules.initial_bankroll;
        const minBet = rules.min_bet || 10.0;

        return {
          ...prev,
          session_id: sessionId,
          status: 'INITIALIZING',
          rules,
          max_rounds: rules.max_rounds,
          delay_ms: rules.delay_ms,
          execution_mode: rules.execution_mode,
          tables: {
            jev: initialTable(
              'jev',
              'Jev (System One)',
              'rgb(213, 120, 190)',
              initialBankroll,
              rules.selected_players.jev,
              minBet
            ),
            laya: initialTable(
              'laya',
              'Laya (Local)',
              'rgb(68, 120, 208)',
              initialBankroll,
              rules.selected_players.laya,
              minBet
            ),
            optimal: initialTable(
              'optimal',
              'Basic Strategy',
              'rgb(118, 194, 154)',
              initialBankroll,
              rules.selected_players.optimal,
              minBet
            ),
          },
        };
      });
    },
    []
  );

  const disconnectSession = useCallback(() => {
    websocketService.disconnect();
  }, []);

  const createAndLaunchSimulation = useCallback(
    async (formValues: VariantRulesFormValues): Promise<SimulationResponse> => {
      const entities: EntityId[] = [];
      if (formValues.selected_players.optimal) entities.push('optimal');
      if (formValues.selected_players.jev) entities.push('jev');
      if (formValues.selected_players.laya) entities.push('laya');

      if (entities.length === 0) {
        throw new Error('At least one player must be selected.');
      }

      const payload: CreateSimulationPayload = {
        max_rounds: Number(formValues.max_rounds),
        num_simulations: Number(formValues.num_simulations || 1),
        execution_mode: formValues.execution_mode,
        delay_ms: Number(formValues.delay_ms),
        seed:
          formValues.seed !== null &&
          formValues.seed !== undefined &&
          String(formValues.seed).trim() !== ''
            ? Number(formValues.seed)
            : null,
        entities,
        mock_mode: Boolean(formValues.mock_mode),
        table_rules: {
          soft_17_rule: formValues.soft_17_rule,
          blackjack_payout: Number(formValues.blackjack_payout),
          hole_card_rule: formValues.hole_card_rule,
          insurance_allowed: Boolean(formValues.insurance_allowed),
          surrender_rule: formValues.surrender_rule,
          double_after_split: Boolean(formValues.double_after_split),
          max_split_hands: Number(formValues.max_split_hands),
          resplit_aces: Boolean(formValues.resplit_aces),
          hit_split_aces: Boolean(formValues.hit_split_aces),
          num_decks: Number(formValues.num_decks),
          penetration: Number(formValues.penetration),
          burn_cards_count: Number(formValues.burn_cards_count),
          initial_bankroll: Number(formValues.initial_bankroll),
          min_bet: Number(formValues.min_bet),
          max_bet: Number(formValues.max_bet),
          stop_on_all_bankrupt: Boolean(formValues.stop_on_all_bankrupt),
        },
      };

      const res = await apiClient.createSimulation(payload);
      connectSession(res.session_id, formValues);
      setSession((prev) => ({
        ...prev,
        session_id: res.session_id,
        run_id: res.run_id,
      }));

      return res;
    },
    [connectSession]
  );

  const pause = useCallback(() => {
    websocketService.sendCommand({ command: 'pause' });
    setSession((s) => ({ ...s, status: 'PAUSED' }));
  }, []);

  const resume = useCallback(() => {
    websocketService.sendCommand({ command: 'resume' });
    setSession((s) => ({ ...s, status: 'RUNNING' }));
  }, []);

  const step = useCallback((level: 'round' | 'turn' = 'round') => {
    websocketService.sendCommand({ command: 'step', level });
  }, []);

  const retry = useCallback((entityId?: string) => {
    websocketService.sendCommand({ command: 'retry', entity_id: entityId });
    setSession((s) => ({ ...s, status: 'RUNNING', active_fault: null }));
  }, []);

  const stop = useCallback(() => {
    websocketService.sendCommand({ command: 'stop' });
    setSession((s) => ({ ...s, status: 'COMPLETED' }));
  }, []);

  const setSpeed = useCallback((delayMs: number) => {
    websocketService.sendCommand({ command: 'set_speed', delay_ms: delayMs });
    setSession((s) => ({ ...s, delay_ms: delayMs }));
  }, []);

  const exportSimulation = useCallback(async () => {
    if (sessionRef.current.session_id) {
      await apiClient.exportSimulationData(sessionRef.current.session_id);
    }
  }, []);

  const clearFault = useCallback(() => {
    setSession((s) => ({ ...s, active_fault: null }));
  }, []);

  return (
    <SimulationContext.Provider
      value={{
        session,
        createAndLaunchSimulation,
        connectSession,
        disconnectSession,
        pause,
        resume,
        step,
        retry,
        stop,
        setSpeed,
        exportSimulation,
        clearFault,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = (): SimulationContextValue => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};
