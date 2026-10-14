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
    <div className="w-full overflow-hidden rounded-xl border border-[#2b305c] bg-[#0a0d3a] shadow-xl">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-[#2b305c] bg-[#1e2353] text-[11px] font-display font-bold uppercase tracking-wider text-[#949ba4]">
          <tr>
            <th className="px-5 py-3.5">Player Entity</th>
            <th className="px-5 py-3.5 text-right">Final Bankroll</th>
            <th className="px-5 py-3.5 text-right">Net Profit / Loss</th>
            <th className="px-5 py-3.5 text-right">Win Rate</th>
            <th className="px-5 py-3.5 text-right">Optimal Agreement</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#2b305c]/50 font-mono text-white">
          {entityOrder.map((entityId) => {
            const table = tables[entityId];
            const summaryData = completionSummary?.players?.[entityId];

            if (!table.is_selected) {
              return (
                <tr key={entityId} className="opacity-40 grayscale bg-[#1e2353]/20">
                  <td className="px-5 py-4">
                    <div className="flex items-center space-x-2.5 font-sans font-medium text-[#949ba4]">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: table.carpet_color }}
                      />
                      <span>{table.name}</span>
                      <Badge variant="secondary" className="text-[10px]">
                        Did Not Play
                      </Badge>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right text-[#949ba4]">--</td>
                  <td className="px-5 py-4 text-right text-[#949ba4]">--</td>
                  <td className="px-5 py-4 text-right text-[#949ba4]">--</td>
                  <td className="px-5 py-4 text-right text-[#949ba4]">--</td>
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
                className="hover:bg-[#1e2353]/50 transition-colors"
              >
                {/* Player Column */}
                <td className="px-5 py-4">
                  <div className="flex items-center space-x-2.5 font-sans font-bold text-white">
                    <span
                      className="h-3 w-3 rounded-full shrink-0 shadow-sm"
                      style={{ backgroundColor: table.carpet_color }}
                    />
                    <span>{table.name}</span>
                    {entityId === 'optimal' && (
                      <Badge variant="cyan" className="text-[10px] px-2 py-0">
                        Baseline
                      </Badge>
                    )}
                  </div>
                </td>

                {/* Final Bankroll */}
                <td className="px-5 py-4 text-right font-extrabold text-white text-base">
                  ${Math.round(finalBankroll).toLocaleString()}
                </td>

                {/* Net Profit / Loss */}
                <td className="px-5 py-4 text-right">
                  <div className="flex items-center justify-end space-x-1 font-bold">
                    {isPositive ? (
                      <>
                        <TrendingUp className="h-4 w-4 text-[#35ed7e]" />
                        <span className="text-[#35ed7e]">+${netProfit.toFixed(0)}</span>
                      </>
                    ) : isNegative ? (
                      <>
                        <TrendingDown className="h-4 w-4 text-rose-400" />
                        <span className="text-rose-400">-${Math.abs(netProfit).toFixed(0)}</span>
                      </>
                    ) : (
                      <>
                        <Minus className="h-4 w-4 text-[#949ba4]" />
                        <span className="text-[#949ba4]">$0</span>
                      </>
                    )}
                  </div>
                </td>

                {/* Win Rate */}
                <td className="px-5 py-4 text-right font-semibold text-white">
                  {winRate.toFixed(1)}%
                </td>

                {/* Optimality Agreement Rate */}
                <td className="px-5 py-4 text-right font-bold text-[#35ed7e]">
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
