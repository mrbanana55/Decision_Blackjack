import React from 'react';
import { PlayerTableState, EntityId } from '../types/simulation';
import { TableCarpetRow } from './TableCarpetRow';
import { LiveStatsRow } from './LiveStatsRow';

interface VisualizerGrid2x3Props {
  tables: Record<EntityId, PlayerTableState>;
  delayMs?: number;
}

export const VisualizerGrid2x3: React.FC<VisualizerGrid2x3Props> = ({
  tables,
  delayMs = 300,
}) => {
  const entityOrder: EntityId[] = ['jev', 'laya', 'optimal'];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 w-full">
      {entityOrder.map((entityId) => {
        const table = tables[entityId];
        if (!table) return null;

        return (
          <div key={entityId} className="flex flex-col space-y-4">
            {/* Top Row: Table Carpet with exact RGB color and card animations */}
            <TableCarpetRow table={table} delayMs={delayMs} />

            {/* Bottom Row: Comparative Live Stats & 3 Dynamic Graph Bars */}
            <LiveStatsRow table={table} />
          </div>
        );
      })}
    </div>
  );
};
