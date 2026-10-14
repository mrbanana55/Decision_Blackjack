import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/dialog';
import { Button } from './ui/button';
import { Info, PlayCircle, Code2, Sparkles } from 'lucide-react';

interface InfoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const InfoModal: React.FC<InfoModalProps> = ({ open, onOpenChange }) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-cyan-900/40 bg-slate-900 text-slate-100 max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader className="space-y-2 border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <Info className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <span>About Decision Blackjack</span>
                <span className="rounded bg-cyan-500/20 px-2 py-0.5 text-[10px] font-mono text-cyan-300 border border-cyan-500/30">
                  v0.1.0
                </span>
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-400">
                A real-time AI decision-making benchmark and visualization studio
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-3 text-xs leading-relaxed text-slate-300">
          {/* Section 1: What it does */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800/80 p-3.5 space-y-1.5">
            <div className="flex items-center space-x-2 text-cyan-300 font-semibold text-sm">
              <Sparkles className="h-4 w-4" />
              <span>What It Does</span>
            </div>
            <p className="text-slate-300">
              Decision Blackjack benchmarks and evaluates AI models playing Blackjack against
              mathematical game theory. It pits <strong>Jev</strong> (TypeSafe AI System One),{' '}
              <strong>Laya</strong> (local SLM model), and classical <strong>Basic Strategy</strong>{' '}
              against the exact same card shoes under identical casino rules to measure decision
              quality, adherence to optimal strategy, and long-term financial outcomes.
            </p>
          </div>

          {/* Section 2: How it works */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800/80 p-3.5 space-y-2">
            <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
              <PlayCircle className="h-4 w-4" />
              <span>How It Works</span>
            </div>
            <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
              <li>
                <strong className="text-slate-200">Synchronized Play:</strong> Active players play
                simultaneously at isolated tables from deterministic, seeded multi-deck shoes.
              </li>
              <li>
                <strong className="text-slate-200">Hi-Lo Card Counting:</strong> Every exposed card
                is tracked in real time to calculate deck penetration, remaining cards, running count,
                and true count.
              </li>
              <li>
                <strong className="text-slate-200">Oracle Evaluation:</strong> Every turn action
                (Hit, Stand, Double, Split, Surrender) is evaluated live against the optimal Basic
                Strategy chart, updating optimality rates instantaneously.
              </li>
              <li>
                <strong className="text-slate-200">Live Pacing:</strong> Adjust simulation speed from
                fast batch mode to visualized real-time card dealing with step-by-step turn execution.
              </li>
            </ul>
          </div>

          {/* Section 3: How it is made */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800/80 p-3.5 space-y-2">
            <div className="flex items-center space-x-2 text-purple-400 font-semibold text-sm">
              <Code2 className="h-4 w-4" />
              <span>How It Is Made</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              <div className="rounded border border-slate-800 bg-slate-900/60 p-2.5 space-y-1">
                <span className="font-semibold text-slate-200 block">Frontend Stack</span>
                <span className="text-slate-400 block">
                  React 19 SPA, TypeScript, React Router 8, Tailwind CSS, shadcn/ui components, GSAP timeline animations, and WebSocket streaming.
                </span>
              </div>
              <div className="rounded border border-slate-800 bg-slate-900/60 p-2.5 space-y-1">
                <span className="font-semibold text-slate-200 block">Backend & AI Stack</span>
                <span className="text-slate-400 block">
                  Python 3.12+ FastAPI async architecture, deterministic FSM Blackjack engine, SQLAlchemy 2.0 with SQLite/PostgreSQL, and TypeSafe AI System One.
                </span>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="border-t border-slate-800 pt-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="w-full sm:w-auto border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs"
          >
            Got it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
