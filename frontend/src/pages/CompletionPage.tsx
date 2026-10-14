import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useSimulation } from '../context/SimulationContext';
import { TriPlayerSummaryTable } from '../components/TriPlayerSummaryTable';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { apiClient } from '../services/apiClient';
import { CheckCircle2, Download, PlusCircle, Loader2 } from 'lucide-react';

export const CompletionPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { session } = useSimulation();
  const [isExporting, setIsExporting] = useState(false);

  const handleExportData = async () => {
    if (!sessionId) return;
    setIsExporting(true);
    try {
      await apiClient.exportSimulationData(sessionId);
    } catch (err) {
      console.error('Failed to export simulation data:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleNewSimulation = () => {
    navigate('/');
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 bg-slate-950">
      <Card className="w-full max-w-4xl border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-md">
        <CardHeader className="text-center pb-4">
          <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl text-slate-100 font-bold">
            Simulation Benchmark Completed
          </CardTitle>
          <CardDescription className="text-slate-400">
            Completed {session.completion_summary?.total_rounds ?? session.current_round} simulated rounds. Session ID:{' '}
            <span className="font-mono text-slate-300">{sessionId}</span>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Tri-Player Comparative Metrics Table */}
          <TriPlayerSummaryTable
            tables={session.tables}
            completionSummary={session.completion_summary}
          />
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-4 border-t border-slate-800">
          {/* Action 1: Export Simulation Data */}
          <Button
            type="button"
            variant="secondary"
            disabled={isExporting}
            onClick={handleExportData}
            className="w-full sm:w-auto h-10 px-5 border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-100 font-medium"
          >
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-amber-400" />
                Preparing Export...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4 text-cyan-400" />
                Export Simulation Data
              </>
            )}
          </Button>

          {/* Action 2: New Simulation */}
          <Button
            type="button"
            onClick={handleNewSimulation}
            className="w-full sm:w-auto h-10 px-6 bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-md shadow-emerald-950/40"
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            New Simulation
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
