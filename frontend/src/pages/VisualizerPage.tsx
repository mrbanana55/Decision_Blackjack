import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useSimulation } from '../context/SimulationContext';
import { VisualizerGrid2x3 } from '../visualization/VisualizerGrid2x3';
import { ControlBar } from '../components/ControlBar';
import { FaultAlertModal } from '../components/FaultAlertModal';
import { InfoModal } from '../components/InfoModal';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Disc, Layers, Info, ArrowLeft } from 'lucide-react';

export const VisualizerPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [infoModalOpen, setInfoModalOpen] = React.useState(false);
  const {
    session,
    connectSession,
    pause,
    resume,
    stop,
    setSpeed,
    retry,
  } = useSimulation();

  useEffect(() => {
    if (sessionId && session.session_id !== sessionId) {
      connectSession(sessionId);
    }
  }, [sessionId, session.session_id, connectSession]);

  useEffect(() => {
    if (session.status === 'COMPLETED' && sessionId) {
      navigate(`/complete/${sessionId}`);
    }
  }, [session.status, sessionId, navigate]);

  const handleStop = () => {
    stop();
    navigate('/');
  };

  return (
    <div className="flex-1 flex flex-col pb-24">
      {/* Top Session Bar */}
      <header className="sticky top-0 z-30 border-b border-[#2b305c]/80 bg-[#0a0d3a]/90 backdrop-blur-md px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleStop}
              className="h-8 px-2 text-[#949ba4] hover:text-white"
              title="Return to Configuration"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              <span className="hidden sm:inline text-xs font-semibold">Exit</span>
            </Button>

            <span className="flex h-9 w-9 items-center justify-center rounded-sm bg-[#5865f2] text-white shadow-md shadow-[#5865f2]/30 font-bold">
              <Disc className="h-4 w-4 animate-spin" />
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="font-display text-base font-extrabold text-white uppercase tracking-tight">
                  Live Visualizer
                </h2>
                <Badge variant="secondary" className="text-[10px] font-mono px-2 py-0.5 border-[#2b305c]">
                  {sessionId?.slice(0, 8)}...
                </Badge>
              </div>
              <p className="text-xs text-[#949ba4] font-medium hidden sm:block">
                Synchronized benchmark comparing Jev, Laya, and Basic Strategy
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 text-xs text-[#949ba4] bg-[#1e2353] border border-[#2b305c] px-2.5 py-1 rounded-pill">
              <Layers className="h-3.5 w-3.5 text-[#00b0f4]" />
              <span className="font-semibold">Shoe:</span>
              <span className="font-mono font-bold text-white">
                #{session.shoe_generation}
              </span>
            </div>

            <Badge
              variant={
                session.status === 'RUNNING'
                  ? 'green'
                  : session.status === 'PAUSED_ERROR'
                  ? 'destructive'
                  : 'secondary'
              }
              className="text-xs uppercase font-extrabold px-3 py-1"
            >
              {session.status}
            </Badge>

            {/* Info button: circle with an i inside */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInfoModalOpen(true)}
              className="h-8 w-8 rounded-full p-0 border-[#2b305c] bg-[#1e2353] text-[#00b0f4] hover:bg-[#5865f2] hover:text-white hover:border-[#5865f2] shadow-sm transition-all"
              title="About Decision Blackjack"
            >
              <Info className="h-4 w-4" />
              <span className="sr-only">About Decision Blackjack</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main 2x3 Visualizer Grid Container */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <VisualizerGrid2x3
          tables={session.tables}
          delayMs={session.delay_ms}
        />
      </main>

      {/* Interactive Bottom Control Bar */}
      <ControlBar
        status={session.status}
        delayMs={session.delay_ms}
        currentRound={session.current_round}
        maxRounds={session.max_rounds}
        onPause={pause}
        onResume={resume}
        onStop={handleStop}
        onSpeedChange={setSpeed}
      />

      {/* RNF-02 Fault Notification & Actionable Retry Modal */}
      <FaultAlertModal
        open={session.status === 'PAUSED_ERROR' && session.active_fault !== null}
        fault={session.active_fault}
        onRetry={() => retry(session.active_fault?.entity_id)}
        onAbort={handleStop}
      />

      {/* Program Information Modal */}
      <InfoModal
        open={infoModalOpen}
        onOpenChange={setInfoModalOpen}
      />
    </div>
  );
};
