import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Zap, Ban, Loader2 } from 'lucide-react';
import { SimulationSessionState } from '../types/simulation';

interface FastBatchProgressCardProps {
  session: SimulationSessionState;
  onCancel: () => void;
}

export const FastBatchProgressCard: React.FC<FastBatchProgressCardProps> = ({
  session,
  onCancel,
}) => {
  const currentRound = session.current_round;
  const maxRounds = session.max_rounds || 1;
  const percentage = Math.min(100, Math.round((currentRound / maxRounds) * 100));

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <Card className="w-full max-w-md border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-sm">
        <CardHeader className="text-center pb-4">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 text-amber-400">
            <Zap className="h-6 w-6 animate-pulse" />
          </div>
          <div className="flex items-center justify-center space-x-2">
            <CardTitle className="text-xl text-slate-100">Fast Batch Execution</CardTitle>
            <Badge variant="secondary" className="bg-slate-800 text-amber-400">
              Headless Path 1
            </Badge>
          </div>
          <CardDescription className="text-slate-400">
            Running unthrottled benchmark simulation at maximum speed.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Round Indicator */}
          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">
              Simulation Progress
            </p>
            <div className="text-3xl font-bold tracking-tight text-slate-100">
              Round {currentRound.toLocaleString()}{' '}
              <span className="text-lg font-normal text-slate-500">
                / {maxRounds.toLocaleString()}
              </span>
            </div>
            <p className="text-xs text-slate-400">{percentage}% completed</p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <Progress value={currentRound} max={maxRounds} className="h-3 bg-slate-800" indicatorClassName="bg-amber-500" />
          </div>

          {/* Player Snapshot Chips */}
          <div className="grid grid-cols-3 gap-2 pt-2">
            {Object.values(session.tables).map((tbl) => (
              <div
                key={tbl.entity_id}
                className={`rounded-lg border p-2 text-center transition-all ${
                  tbl.is_selected
                    ? 'border-slate-800 bg-slate-950/60'
                    : 'border-slate-900 bg-slate-950/20 opacity-40'
                }`}
              >
                <div className="flex items-center justify-center space-x-1.5 mb-1">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: tbl.carpet_color }}
                  />
                  <span className="text-xs font-semibold truncate text-slate-300">
                    {tbl.entity_id.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs font-mono font-medium text-slate-200">
                  ${Math.round(tbl.current_bankroll)}
                </div>
              </div>
            ))}
          </div>

          {/* Animated Spinner Message */}
          <div className="flex items-center justify-center space-x-2 text-xs text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-amber-400" />
            <span>Processing round settlements & decision records...</span>
          </div>
        </CardContent>

        <CardFooter className="pt-2">
          <Button
            type="button"
            variant="destructive"
            onClick={onCancel}
            className="w-full bg-rose-600/20 text-rose-300 hover:bg-rose-600/30 border border-rose-500/30"
          >
            <Ban className="mr-2 h-4 w-4" />
            Cancel Simulation
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
