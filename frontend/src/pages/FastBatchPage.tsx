import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useSimulation } from '../context/SimulationContext';
import { FastBatchProgressCard } from '../visualization/FastBatchProgressCard';

export const FastBatchPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { session, connectSession, stop } = useSimulation();

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

  const handleCancel = () => {
    stop();
    navigate('/');
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 bg-slate-950">
      <FastBatchProgressCard session={session} onCancel={handleCancel} />
    </div>
  );
};
