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
import { Badge } from './ui/badge';
import { Info, PlayCircle, Code2, Sparkles } from 'lucide-react';

interface InfoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const InfoModal: React.FC<InfoModalProps> = ({ open, onOpenChange }) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-[#2b305c] bg-[#1e2353] text-white max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader className="space-y-2 border-b border-[#2b305c]/80 pb-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-sm bg-[#5865f2] text-white shadow-lg shadow-[#5865f2]/30">
              <Info className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="flex items-center space-x-2 text-xl">
                <span>About Decision Blackjack</span>
                <Badge variant="magenta" className="text-[10px] font-mono px-2 py-0.5">
                  v0.1.0
                </Badge>
              </DialogTitle>
              <DialogDescription className="text-xs text-[#949ba4]">
                A real-time AI decision-making benchmark and visualization studio
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-3 text-xs leading-relaxed text-slate-200">
          {/* Section 1: What it does */}
          <div className="rounded-xl bg-[#0a0d3a]/80 border border-[#2b305c] p-4 space-y-2">
            <div className="flex items-center space-x-2 text-[#ec48bd] font-display font-bold text-sm uppercase tracking-wide">
              <Sparkles className="h-4 w-4" />
              <span>What It Does</span>
            </div>
            <p className="text-[#949ba4] leading-relaxed">
              Decision Blackjack benchmarks and evaluates AI models playing Blackjack against
              mathematical game theory. It pits <strong className="text-white">Jev</strong> (TypeSafe AI System One),{' '}
              <strong className="text-white">Laya</strong> (local SLM model), and classical <strong className="text-white">Basic Strategy</strong>{' '}
              against the exact same card shoes under identical casino rules to measure decision
              quality, adherence to optimal strategy, and long-term financial outcomes.
            </p>
          </div>

          {/* Section 2: How it works */}
          <div className="rounded-xl bg-[#0a0d3a]/80 border border-[#2b305c] p-4 space-y-2.5">
            <div className="flex items-center space-x-2 text-[#35ed7e] font-display font-bold text-sm uppercase tracking-wide">
              <PlayCircle className="h-4 w-4" />
              <span>How It Works</span>
            </div>
            <ul className="space-y-2 text-[#949ba4] list-disc list-inside">
              <li>
                <strong className="text-white">Synchronized Play:</strong> Active players play
                simultaneously at isolated tables from deterministic, seeded multi-deck shoes.
              </li>
              <li>
                <strong className="text-white">Hi-Lo Card Counting:</strong> Every exposed card
                is tracked in real time to calculate deck penetration, remaining cards, running count,
                and true count.
              </li>
              <li>
                <strong className="text-white">Oracle Evaluation:</strong> Every turn action
                (Hit, Stand, Double, Split, Surrender) is evaluated live against the optimal Basic
                Strategy chart, updating optimality rates instantaneously.
              </li>
              <li>
                <strong className="text-white">Live Pacing:</strong> Adjust simulation speed from
                fast batch mode to visualized real-time card dealing with step-by-step turn execution.
              </li>
            </ul>
          </div>

          {/* Section 3: How it is made */}
          <div className="rounded-xl bg-[#0a0d3a]/80 border border-[#2b305c] p-4 space-y-2.5">
            <div className="flex items-center space-x-2 text-[#00b0f4] font-display font-bold text-sm uppercase tracking-wide">
              <Code2 className="h-4 w-4" />
              <span>How It Is Made</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
              <div className="rounded-sm border border-[#2b305c] bg-[#1e2353]/60 p-3 space-y-1">
                <span className="font-bold text-white block">Frontend Stack</span>
                <span className="text-[#949ba4] block leading-relaxed">
                  React 19 SPA, TypeScript, React Router 8, Tailwind CSS, shadcn/ui components, GSAP timeline animations, and WebSocket streaming.
                </span>
              </div>
              <div className="rounded-sm border border-[#2b305c] bg-[#1e2353]/60 p-3 space-y-1">
                <span className="font-bold text-white block">Backend & AI Stack</span>
                <span className="text-[#949ba4] block leading-relaxed">
                  Python 3.12+ FastAPI async architecture, deterministic FSM Blackjack engine, SQLAlchemy 2.0 with SQLite/PostgreSQL, and TypeSafe AI System One.
                </span>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="pt-3">
          <Button
            type="button"
            variant="primary"
            onClick={() => onOpenChange(false)}
            className="w-full sm:w-auto h-9 px-6 text-xs"
          >
            Got it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
