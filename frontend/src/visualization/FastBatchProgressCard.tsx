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
      <Card className="w-full max-w-md border-[#2b305c] bg-[#1e2353] shadow-2xl shadow-black/80">
        <CardHeader className="text-center pb-4">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-sm bg-[#5865f2] text-white shadow-lg shadow-[#5865f2]/40">
            <Zap className="h-7 w-7 animate-pulse text-[#fee75c]" />
          </div>
          <div className="flex items-center justify-center space-x-2">
            <CardTitle className="font-display text-xl uppercase tracking-tight text-white">
              Fast Batch Execution
            </CardTitle>
            <Badge variant="magenta" className="text-[10px] font-bold px-2 py-0.5">
              Path 1
            </Badge>
          </div>
          <CardDescription className="text-xs text-[#949ba4]">
            Running unthrottled benchmark simulation at maximum engine speed.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Round Indicator */}
          <div className="text-center space-y-1">
            <p className="text-xs font-bold text-[#949ba4] uppercase tracking-wider">
              Simulation Progress
            </p>
            <div className="font-display text-4xl font-extrabold tracking-tight text-white">
              Round {currentRound.toLocaleString()}{' '}
              <span className="text-xl font-normal text-[#949ba4]">
                / {maxRounds.toLocaleString()}
              </span>
            </div>
            <p className="font-mono text-xs font-bold text-[#35ed7e]">{percentage}% completed</p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <Progress value={currentRound} max={maxRounds} className="h-3" />
          </div>

          {/* Player Snapshot Chips */}
          <div className="grid grid-cols-3 gap-2 pt-2">
            {Object.values(session.tables).map((tbl) => (
              <div
                key={tbl.entity_id}
                className={`rounded-sm border p-2.5 text-center transition-all ${
                  tbl.is_selected
                    ? 'border-[#2b305c] bg-[#0a0d3a]'
                    : 'border-[#2b305c]/40 bg-[#0a0d3a]/30 opacity-40'
                }`}
              >
                <div className="flex items-center justify-center space-x-1.5 mb-1">
                  <span
                    className="h-2 w-2 rounded-full shadow-sm"
                    style={{ backgroundColor: tbl.carpet_color }}
                  />
                  <span className="text-[11px] font-bold truncate text-white uppercase">
                    {tbl.entity_id}
                  </span>
                </div>
                <div className="text-xs font-mono font-extrabold text-[#fee75c]">
                  ${Math.round(tbl.current_bankroll)}
                </div>
              </div>
            ))}
          </div>

          {/* Animated Spinner Message */}
          <div className="flex items-center justify-center space-x-2 text-xs text-[#949ba4]">
            <Loader2 className="h-4 w-4 animate-spin text-[#00b0f4]" />
            <span>Processing round settlements & decision records...</span>
          </div>
        </CardContent>

        <CardFooter className="pt-2 border-t border-[#2b305c]/60">
          <Button
            type="button"
            variant="destructive"
            onClick={onCancel}
            className="w-full h-10 font-bold"
          >
            <Ban className="mr-2 h-4 w-4" />
            Cancel Simulation
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
