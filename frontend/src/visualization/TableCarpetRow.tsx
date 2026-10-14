import React from "react";
import { PlayerTableState } from "../types/simulation";
import { CardView } from "../components/CardView";
import { Badge } from "../components/ui/badge";
import { Shuffle } from "lucide-react";

interface TableCarpetRowProps {
  table: PlayerTableState;
  delayMs?: number;
}

export const TableCarpetRow: React.FC<TableCarpetRowProps> = ({
  table,
  delayMs = 300,
}) => {
  const {
    name,
    carpet_color,
    is_selected,
    dealer_cards,
    dealer_is_busted,
    player_hands,
  } = table;

  // Deselected Player: Empty table showing carpet background without cards/animations
  if (!is_selected) {
    return (
      <div
        className="relative flex h-[340px] flex-col items-center justify-center rounded-xl p-4 shadow-inner border border-white/10 overflow-hidden"
        style={{
          backgroundColor: carpet_color,
          backgroundImage:
            "radial-gradient(circle at center, rgba(255,255,255,0.08) 0%, rgba(0,0,0,0.3) 100%)",
        }}
      >
        <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px]" />
        <div className="relative z-10 flex flex-col items-center space-y-2 text-center">
          <span className="font-display text-sm font-bold tracking-wide text-white/90 drop-shadow">
            {name}
          </span>
          <span className="rounded-pill bg-black/50 px-3 py-1 text-xs font-semibold text-white/70 border border-white/20">
            Table Inactive
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative flex h-[340px] flex-col justify-between rounded-xl p-4 shadow-xl border border-white/20 overflow-hidden select-none"
      style={{
        backgroundColor: carpet_color,
        backgroundImage:
          "radial-gradient(circle at center, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.25) 100%)",
      }}
    >
      {/* Shuffling Deck Overlay when this table finishes deck / new shoe is being loaded */}
      {table.is_shuffling && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/80 backdrop-blur-sm transition-all duration-300">
          <div className="flex flex-col items-center space-y-2.5 p-5 text-center rounded-xl bg-[#0a0d3a]/95 border border-[#5865f2] shadow-2xl shadow-[#5865f2]/40">
            <Shuffle className="h-8 w-8 text-[#35ed7e] animate-spin" />
            <span className="font-display text-base font-extrabold tracking-wider text-white uppercase">
              Shuffling Deck
            </span>
            <span className="text-xs text-[#949ba4] font-medium">
              Loading Shoe #{table.shoe_generation || 1}...
            </span>
          </div>
        </div>
      )}

      {/* Top Banner: Entity Name, Shoe Gen & Status */}
      <div className="flex items-center justify-between pb-1.5 border-b border-black/20">
        <div className="flex items-center space-x-2">
          <span className="font-display text-sm font-extrabold tracking-wide text-slate-900 drop-shadow-sm">
            {name}
          </span>
          <span className="rounded-pill bg-black/30 px-2 py-0.5 text-[10px] font-mono font-bold text-slate-900 border border-black/15">
            Shoe #{table.shoe_generation || 1}
          </span>
        </div>
        <div className="flex items-center space-x-1.5">
          {table.is_shuffling ? (
            <div className="flex items-center space-x-1 px-2.5 py-0.5 rounded-pill bg-[#35ed7e] text-black font-extrabold text-[10px] animate-pulse shadow-sm">
              <Shuffle className="h-3 w-3 animate-spin" />
              <span>SHUFFLING</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 bg-black/25 px-2 py-0.5 rounded-pill">
              <span className="h-2 w-2 rounded-full bg-[#35ed7e] animate-pulse" />
              <span className="text-[10px] font-bold text-slate-900 uppercase">
                Live
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Dealer Cards Area */}
      <div className="flex flex-col items-center justify-center space-y-1.5 pt-1">
        <div className="flex items-center space-x-2">
          <span className="font-display text-xs font-bold uppercase tracking-wider text-slate-800">
            Dealer
          </span>
          {dealer_is_busted && (
            <span className="rounded-pill bg-rose-600 px-2 py-0.5 text-[10px] font-bold text-white">
              BUST
            </span>
          )}
        </div>
        <div className="flex min-h-[84px] items-center justify-center space-x-1.5 overflow-x-auto py-1">
          {dealer_cards.length === 0 ? (
            <div className="h-20 w-14 rounded-md border-2 border-dashed border-black/20 flex items-center justify-center text-[10px] text-black/40 font-medium">
              Shoe
            </div>
          ) : (
            dealer_cards.map((c) => (
              <CardView key={c.id} card={c} delayMs={delayMs} />
            ))
          )}
        </div>
      </div>

      {/* Player Hands Area (Supports Splits 1-4) */}
      <div className="flex flex-col items-center justify-end space-y-1 pt-1">
        <div className="flex w-full items-center justify-center space-x-3 overflow-x-auto">
          {player_hands.map((hand, idx) => (
            <div
              key={hand.hand_id}
              className={`flex flex-col items-center rounded-lg p-1.5 transition-all ${
                player_hands.length > 1
                  ? "bg-black/20 border border-white/20 min-w-[120px]"
                  : ""
              }`}
            >
              {/* Hand Status Badges */}
              <div className="flex items-center space-x-1 mb-1">
                {player_hands.length > 1 && (
                  <span className="text-[10px] font-bold text-slate-900">
                    H{idx + 1}:
                  </span>
                )}
                {hand.cards.length > 0 && (
                  <span className="rounded-pill bg-black/40 px-2 py-0.5 font-mono text-xs font-bold text-white border border-white/20">
                    {hand.is_busted
                      ? "BUST"
                      : hand.is_blackjack
                        ? "BJ"
                        : hand.total > 0
                          ? hand.total
                          : "--"}
                  </span>
                )}
                {hand.is_doubled && (
                  <Badge
                    variant="double"
                    className="text-[9px] px-1.5 py-0 font-bold"
                  >
                    2X
                  </Badge>
                )}
                {hand.is_surrendered && (
                  <Badge
                    variant="surrender"
                    className="text-[9px] px-1.5 py-0 font-bold"
                  >
                    SURR
                  </Badge>
                )}
              </div>

              {/* Hand Cards */}
              <div className="flex min-h-[84px] items-center justify-center space-x-1">
                {hand.cards.length === 0 ? (
                  <div className="h-20 w-14 rounded-md border-2 border-dashed border-black/20 flex items-center justify-center text-[10px] text-black/40 font-medium">
                    Waiting
                  </div>
                ) : (
                  hand.cards.map((c) => (
                    <CardView key={c.id} card={c} delayMs={delayMs} />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
