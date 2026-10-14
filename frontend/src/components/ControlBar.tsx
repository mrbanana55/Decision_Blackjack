import React from 'react';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { Play, Pause, Square, Download, FastForward } from 'lucide-react';
import { SimulationLifecycle } from '../types/simulation';
import { apiClient } from '../services/apiClient';

interface ControlBarProps {
  status: SimulationLifecycle;
  delayMs: number;
  currentRound: number;
  maxRounds: number;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSpeedChange: (speed: number) => void;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  status,
  delayMs,
  currentRound,
  maxRounds,
  onPause,
  onResume,
  onStop,
  onSpeedChange,
}) => {
  const isPaused = status === 'PAUSED' || status === 'PAUSED_ERROR';
  const isCompleted = status === 'COMPLETED';

  const handleExportDb = async () => {
    try {
      await apiClient.exportDatabase();
    } catch (err) {
      console.error('Database export error:', err);
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-[#2b305c]/80 bg-[#0a0d3a]/95 px-4 py-3 shadow-2xl backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
        {/* Left: Round Progress Status */}
        <div className="flex items-center space-x-3">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#949ba4]">
              Round Progress
            </span>
            <div className="flex items-center space-x-1.5 font-mono text-base font-extrabold text-white">
              <span>{currentRound.toLocaleString()}</span>
              <span className="text-[#949ba4]">/</span>
              <span className="text-[#949ba4]">{maxRounds.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Center: Play/Pause, Step & Speed Range Slider */}
        <div className="flex flex-1 max-w-md items-center justify-center space-x-4">
          {/* Pause / Resume Button */}
          <Button
            type="button"
            size="sm"
            variant={isPaused ? "green" : "default"}
            disabled={isCompleted}
            onClick={isPaused ? onResume : onPause}
            className={`h-9 px-5 font-bold shadow-md ${
              isPaused
                ? 'bg-[#35ed7e] text-black hover:bg-[#2ecc71]'
                : 'bg-[#5865f2] text-white hover:bg-[#4752c4]'
            }`}
          >
            {isPaused ? (
              <>
                <Play className="mr-1.5 h-4 w-4 fill-current" />
                Resume
              </>
            ) : (
              <>
                <Pause className="mr-1.5 h-4 w-4 fill-current" />
                Pause
              </>
            )}
          </Button>

          {/* Speed Slider */}
          <div className="flex flex-1 flex-col space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center text-[#949ba4] font-medium">
                <FastForward className="mr-1 h-3.5 w-3.5 text-[#00b0f4]" />
                Pacing Delay
              </span>
              <span className="font-mono text-xs text-[#00b0f4] font-bold">
                {delayMs === 0 ? '0 ms (Instant)' : `${delayMs} ms`}
              </span>
            </div>
            <Slider
              min={0}
              max={2000}
              step={50}
              value={delayMs}
              onValueChange={onSpeedChange}
              className="w-full"
            />
          </div>
        </div>

        {/* Right: Stop & Database Export */}
        <div className="flex items-center space-x-2">
          {/* Stop / Abort Button */}
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={onStop}
            className="h-9 px-3.5"
          >
            <Square className="mr-1.5 h-3.5 w-3.5 fill-current" />
            Stop
          </Button>

          {/* Export Database Button */}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleExportDb}
            className="h-9 px-3.5 border-[#2b305c] bg-[#1e2353] hover:bg-[#262c69] text-white font-semibold"
          >
            <Download className="mr-1.5 h-3.5 w-3.5 text-[#00b0f4]" />
            Export DB
          </Button>
        </div>
      </div>
    </div>
  );
};
