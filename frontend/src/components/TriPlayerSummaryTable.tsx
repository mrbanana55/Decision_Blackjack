import React from 'react';
import { EntityId, PlayerTableState, CompletionSummary } from '../types/simulation';
import { Badge } from './ui/badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TriPlayerSummaryTableProps {
  tables: Record<EntityId, PlayerTableState>;
  completionSummary: CompletionSummary | null;
}

export const TriPlayerSummaryTable: React.FC<TriPlayerSummaryTableProps> = ({
  tables,
  completionSummary,
}) => {
  const entityOrder: EntityId[] = ['jev', 'laya', 'optimal'];

  return (
    <div className="w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60 shadow-lg">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-800 bg-slate-900/80 text-xs uppercase tracking-wider text-slate-400">
          <tr>
            <th className="px-4 py-3">Player Entity</th>
            <th className="px-4 py-3 text-right">Final Bankroll</th>
            <th className="px-4 py-3 text-right">Net Profit / Loss</th>
            <th className="px-4 py-3 text-right">Win Rate</th>
            <th className="px-4 py-3 text-right">Optimal Agreement</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-mono text-slate-200">
          {entityOrder.map((entityId) => {
            const table = tables[entityId];
            const summaryData = completionSummary?.players?.[entityId];

            if (!table.is_selected) {
              return (
                <tr key={entityId} className="opacity-40 grayscale bg-slate-900/20">
                  <td className="px-4 py-3.5">
                    <div className="flex items-center space-x-2 font-sans font-medium text-slate-400">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: table.carpet_color }}
                      />
                      <span>{table.name}</span>
                      <Badge variant="outline" className="text-[10px] text-slate-500">
                        Did Not Play
                      </Badge>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-right text-slate-500">--</td>
                  <td className="px-4 py-3.5 text-right text-slate-500">--</td>
                  <td className="px-4 py-3.5 text-right text-slate-500">--</td>
                  <td className="px-4 py-3.5 text-right text-slate-500">--</td>
                </tr>
              );
            }

            const finalBankroll =
              summaryData?.final_bankroll ?? table.current_bankroll;
            const netProfit =
              summaryData?.net_profit ?? (table.current_bankroll - table.starting_bankroll);
            const totalRounds = table.win_loss_push.total;
            const winRate =
              summaryData?.win_rate ??
              (totalRounds > 0 ? (table.win_loss_push.wins / totalRounds) * 100 : 0);
            const rawOpt =
              summaryData?.optimality_rate ??
              (table.optimality_rate <= 1.0 ? table.optimality_rate * 100 : table.optimality_rate);
            const optimalityRate = Number.isFinite(rawOpt) ? rawOpt : 100.0;

            const isPositive = netProfit > 0;
            const isNegative = netProfit < 0;

            return (
              <tr
                key={entityId}
                className="hover:bg-slate-900/40 transition-colors"
              >
                {/* Player Column */}
                <td className="px-4 py-3.5">
                  <div className="flex items-center space-x-2 font-sans font-medium text-slate-100">
                    <span
                      className="h-3 w-3 rounded-full shrink-0"
                      style={{ backgroundColor: table.carpet_color }}
                    />
                    <span>{table.name}</span>
                    {entityId === 'optimal' && (
                      <Badge variant="outline" className="text-[10px] border-emerald-500/40 text-emerald-400">
                        Baseline
                      </Badge>
                    )}
                  </div>
                </td>

                {/* Final Bankroll */}
                <td className="px-4 py-3.5 text-right font-bold text-slate-100">
                  ${Math.round(finalBankroll).toLocaleString()}
                </td>

                {/* Net Profit / Loss */}
                <td className="px-4 py-3.5 text-right">
                  <div className="flex items-center justify-end space-x-1 font-semibold">
                    {isPositive ? (
                      <>
                        <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">+${netProfit.toFixed(0)}</span>
                      </>
                    ) : isNegative ? (
                      <>
                        <TrendingDown className="h-3.5 w-3.5 text-rose-400" />
                        <span className="text-rose-400">-${Math.abs(netProfit).toFixed(0)}</span>
                      </>
                    ) : (
                      <>
                        <Minus className="h-3.5 w-3.5 text-slate-400" />
                        <span className="text-slate-400">$0</span>
                      </>
                    )}
                  </div>
                </td>

                {/* Win Rate */}
                <td className="px-4 py-3.5 text-right font-medium text-slate-300">
                  {winRate.toFixed(1)}%
                </td>

                {/* Optimality Agreement Rate */}
                <td className="px-4 py-3.5 text-right font-medium text-emerald-400">
                  {optimalityRate.toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
