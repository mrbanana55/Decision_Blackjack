import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useSimulation } from '../context/SimulationContext';
import { VisualizerGrid2x3 } from '../visualization/VisualizerGrid2x3';
import { ControlBar } from '../components/ControlBar';
import { FaultAlertModal } from '../components/FaultAlertModal';
import { InfoModal } from '../components/InfoModal';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Disc, Layers, Info } from 'lucide-react';

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
    <div className="flex-1 flex flex-col bg-slate-950 pb-24">
      {/* Top Session Bar */}
      <div className="border-b border-slate-800 bg-slate-900/60 px-6 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
              <Disc className="h-4 w-4 animate-spin" />
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-slate-100">
                  Tri-Entity Real-Time Visualizer
                </h2>
                <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                  Session: {sessionId?.slice(0, 10)}...
                </Badge>
              </div>
              <p className="text-xs text-slate-400">
                Synchronized execution comparing Jev, Laya, and Basic Strategy
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              <span>Shoe Gen:</span>
              <span className="font-mono font-semibold text-slate-200">
                #{session.shoe_generation}
              </span>
            </div>

            <Badge
              variant={
                session.status === 'RUNNING'
                  ? 'success'
                  : session.status === 'PAUSED_ERROR'
                  ? 'destructive'
                  : 'secondary'
              }
              className="text-xs uppercase"
            >
              {session.status}
            </Badge>

            {/* Info button: circle with an i inside */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInfoModalOpen(true)}
              className="h-7 w-7 rounded-full p-0 border-slate-700 bg-slate-900 text-cyan-400 hover:bg-slate-800 hover:text-cyan-300 shadow-sm"
              title="About Decision Blackjack"
            >
              <Info className="h-3.5 w-3.5" />
              <span className="sr-only">About Decision Blackjack</span>
            </Button>
          </div>
        </div>
      </div>

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
