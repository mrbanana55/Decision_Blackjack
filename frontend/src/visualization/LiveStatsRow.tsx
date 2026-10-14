import React from 'react';
import { PlayerTableState } from '../types/simulation';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

interface LiveStatsRowProps {
  table: PlayerTableState;
}

export const LiveStatsRow: React.FC<LiveStatsRowProps> = ({ table }) => {
  const {
    entity_id,
    is_selected,
    current_bet,
    last_action,
    last_comparison,
    current_bankroll,
    starting_bankroll,
    net_profit_delta,
    optimality_rate,
    win_loss_push,
    relative_bankroll_pct,
  } = table;

  // Render disabled and darkened state if player is not selected
  if (!is_selected) {
    return (
      <Card className="border-slate-800/50 bg-slate-900/30 opacity-40 grayscale select-none">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs text-slate-500 font-medium">Current Bet: --</span>
            <Badge variant="outline" className="border-slate-800 text-slate-600 text-xs">
              DISABLED
            </Badge>
          </div>
          <div className="text-center py-6 text-xs text-slate-600">
            Player deselected from active simulation
          </div>
        </CardContent>
      </Card>
    );
  }

  // Action badge variant mapper
  const getActionVariant = (action: string | null) => {
    if (!action) return 'secondary';
    const act = action.toUpperCase();
    if (act === 'HIT') return 'hit';
    if (act === 'STAND') return 'stand';
    if (act === 'DOUBLE') return 'double';
    if (act === 'SPLIT') return 'split';
    if (act === 'SURRENDER') return 'surrender';
    return 'default';
  };

  // Bar 2: Win / Loss / Push calculations
  const totalRounds = win_loss_push.total || 0;
  const winPct = totalRounds > 0 ? Math.round((win_loss_push.wins / totalRounds) * 100) : 0;
  const pushPct = totalRounds > 0 ? Math.round((win_loss_push.pushes / totalRounds) * 100) : 0;
  const lossPct =
    totalRounds > 0 ? Math.max(0, 100 - winPct - pushPct) : 0;

  // Bar 3: Relative Bankroll capped percentage for 200% bar
  const relBankrollClamped = Math.min(200, Math.max(0, relative_bankroll_pct));
  const relBarFill = Math.min(100, (relBankrollClamped / 200) * 100);

  // Bankroll delta display
  const isProfit = net_profit_delta > 0;
  const isLoss = net_profit_delta < 0;
  const netDeltaFormatted = isProfit
    ? `+$${net_profit_delta.toFixed(0)}`
    : isLoss
    ? `-$${Math.abs(net_profit_delta).toFixed(0)}`
    : '$0';

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-lg backdrop-blur-sm">
      <CardContent className="p-4 space-y-3.5">
        {/* Top Header: Current Bet & Action Badge */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-slate-400 font-medium">Bet:</span>
            <span className="text-sm font-bold font-mono text-amber-400">
              ${current_bet > 0 ? current_bet.toLocaleString() : '0'}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium">Action:</span>
            {last_action ? (
              <Badge variant={getActionVariant(last_action) as any} className="font-bold tracking-wide">
                {last_action.toUpperCase()}
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-slate-400 text-xs">
                WAITING
              </Badge>
            )}
          </div>
        </div>

        {/* Shoe Metrics: Remaining Cards, Running Count, True Count */}
        <div className="grid grid-cols-3 gap-1.5 rounded-md bg-slate-950/70 border border-slate-800/80 px-2 py-1.5 text-center shadow-inner">
          <div className="flex flex-col items-center justify-center">
            <span className="text-[9px] uppercase font-semibold text-slate-400 tracking-wider">
              Remaining
            </span>
            <span className="font-mono text-xs font-bold text-slate-200">
              {table.cards_remaining !== undefined ? table.cards_remaining : '--'}
            </span>
          </div>
          <div className="flex flex-col items-center justify-center border-x border-slate-800/80">
            <span className="text-[9px] uppercase font-semibold text-slate-400 tracking-wider">
              Count
            </span>
            <span
              className={`font-mono text-xs font-bold ${
                (table.running_count ?? 0) > 0
                  ? 'text-emerald-400'
                  : (table.running_count ?? 0) < 0
                  ? 'text-rose-400'
                  : 'text-slate-300'
              }`}
            >
              {(table.running_count ?? 0) > 0
                ? `+${table.running_count}`
                : table.running_count ?? 0}
            </span>
          </div>
          <div className="flex flex-col items-center justify-center">
            <span className="text-[9px] uppercase font-semibold text-slate-400 tracking-wider">
              True Count
            </span>
            <span
              className={`font-mono text-xs font-bold ${
                (table.true_count ?? 0) > 0
                  ? 'text-cyan-400'
                  : (table.true_count ?? 0) < 0
                  ? 'text-amber-400'
                  : 'text-slate-300'
              }`}
            >
              {(table.true_count ?? 0) > 0
                ? `+${table.true_count.toFixed(1)}`
                : (table.true_count ?? 0).toFixed(1)}
            </span>
          </div>
        </div>

        {/* Basic Strategy Comparison Banner */}
        <div className="rounded-md border border-slate-800 bg-slate-950/60 px-2.5 py-1.5">
          {entity_id === 'optimal' ? (
            <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-medium">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              <span>Ground Truth Basic Strategy</span>
            </div>
          ) : last_comparison ? (
            last_comparison.is_optimal ? (
              <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-medium">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>✓ Matches Optimal Strategy</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1.5 text-xs text-rose-400 font-medium">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>
                  ✗ Deviates: Recommended{' '}
                  <strong className="underline">{last_comparison.optimal_action.toUpperCase()}</strong>
                </span>
              </div>
            )
          ) : (
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <span>Evaluating live decisions against basic strategy...</span>
            </div>
          )}
        </div>

        {/* Bankroll & Net P/L */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Bankroll:</span>
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold text-slate-100 text-sm">
              ${Math.round(current_bankroll).toLocaleString()}
            </span>
            <span
              className={`font-mono text-xs font-semibold ${
                isProfit
                  ? 'text-emerald-400'
                  : isLoss
                  ? 'text-rose-400'
                  : 'text-slate-400'
              }`}
            >
              ({netDeltaFormatted})
            </span>
          </div>
        </div>

        {/* 3 Dynamic Graph Bars */}
        <div className="space-y-2.5 pt-1 border-t border-slate-800/80">
          {/* Bar 1: Optimality Rate */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium">Strategy Optimality Rate</span>
              <span className="font-mono font-semibold text-emerald-400">
                {((Number.isFinite(optimality_rate) ? (optimality_rate <= 1.0 ? optimality_rate * 100 : optimality_rate) : 100.0)).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-500 ease-out"
                style={{
                  width: `${Math.min(
                    100,
                    Math.max(
                      0,
                      Number.isFinite(optimality_rate)
                        ? optimality_rate <= 1.0
                          ? optimality_rate * 100
                          : optimality_rate
                        : 100.0
                    )
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* Bar 2: Win / Loss / Push Distribution */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium">Outcome Distribution</span>
              <span className="font-mono text-[10px] text-slate-300">
                W: {winPct}% | P: {pushPct}% | L: {lossPct}%
              </span>
            </div>
            <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className="bg-emerald-500 transition-all duration-300"
                style={{ width: `${winPct}%` }}
                title={`Wins: ${win_loss_push.wins}`}
              />
              <div
                className="bg-slate-500 transition-all duration-300"
                style={{ width: `${pushPct}%` }}
                title={`Pushes: ${win_loss_push.pushes}`}
              />
              <div
                className="bg-rose-500 transition-all duration-300"
                style={{ width: `${lossPct}%` }}
                title={`Losses: ${win_loss_push.losses}`}
              />
            </div>
          </div>

          {/* Bar 3: Relative Bankroll vs Initial */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium">Bankroll vs Starting</span>
              <span className="font-mono font-semibold text-cyan-400">
                {relative_bankroll_pct.toFixed(0)}%
                <span className="text-[10px] text-slate-500 ml-1">
                  (of ${starting_bankroll})
                </span>
              </span>
            </div>
            <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800">
              {/* Midpoint marker at 50% width = 100% bankroll */}
              <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-500/50 z-10" />
              <div
                className={`h-full transition-all duration-500 ease-out ${
                  relative_bankroll_pct >= 100
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-400'
                    : 'bg-gradient-to-r from-rose-500 to-amber-500'
                }`}
                style={{ width: `${relBarFill}%` }}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
