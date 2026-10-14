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
    <div className="flex-1 flex flex-col items-center justify-center p-6">
      <Card className="w-full max-w-4xl border-[#2b305c] bg-[#1e2353] shadow-2xl shadow-black/80 backdrop-blur-md">
        <CardHeader className="text-center pb-4">
          <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-sm bg-[#35ed7e]/20 text-[#35ed7e] border border-[#35ed7e]/40 shadow-lg shadow-[#35ed7e]/20">
            <CheckCircle2 className="h-9 w-9" />
          </div>
          <CardTitle className="font-display text-2xl sm:text-3xl text-white font-extrabold uppercase tracking-tight">
            Simulation Benchmark Completed
          </CardTitle>
          <CardDescription className="text-xs text-[#949ba4]">
            Completed {session.completion_summary?.total_rounds ?? session.current_round} simulated rounds. Session ID:{' '}
            <span className="font-mono text-white font-semibold">{sessionId}</span>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Tri-Player Comparative Metrics Table */}
          <TriPlayerSummaryTable
            tables={session.tables}
            completionSummary={session.completion_summary}
          />
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-5 border-t border-[#2b305c]/80">
          {/* Action 1: Export Simulation Data */}
          <Button
            type="button"
            variant="secondary"
            disabled={isExporting}
            onClick={handleExportData}
            className="w-full sm:w-auto h-11 px-5 text-sm font-semibold border-[#2b305c] bg-[#0a0d3a] hover:bg-[#1e2353] text-white"
          >
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin text-[#fee75c]" />
                Preparing Export...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4 text-[#00b0f4]" />
                Export Simulation Data
              </>
            )}
          </Button>

          {/* Action 2: New Simulation (Electric green highest-intent button) */}
          <Button
            type="button"
            variant="green"
            onClick={handleNewSimulation}
            className="w-full sm:w-auto h-11 px-6 text-sm font-extrabold shadow-lg shadow-[#35ed7e]/20"
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            New Simulation
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
