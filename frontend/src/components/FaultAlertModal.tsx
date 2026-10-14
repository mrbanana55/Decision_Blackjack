import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { AlertCircle, RefreshCw, XCircle } from 'lucide-react';
import { ActiveFault } from '../types/simulation';

interface FaultAlertModalProps {
  fault: ActiveFault | null;
  open: boolean;
  onRetry: () => void;
  onAbort: () => void;
}

export const FaultAlertModal: React.FC<FaultAlertModalProps> = ({
  fault,
  open,
  onRetry,
  onAbort,
}) => {
  if (!fault) return null;

  return (
    <Dialog open={open}>
      <DialogContent className="border-rose-900/50 bg-slate-900/95 text-slate-100 max-w-md">
        <DialogHeader className="space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/10 text-rose-400">
            <AlertCircle className="h-6 w-6" />
          </div>
          <DialogTitle className="text-center text-lg text-rose-200">
            Provider Fault Detected (RNF-02)
          </DialogTitle>
          <DialogDescription className="text-center text-sm text-slate-300">
            {fault.error_message || `Execution paused due to provider fault for ${fault.entity_id}.`}
          </DialogDescription>
        </DialogHeader>

        <div className="my-2 rounded-lg border border-rose-800/40 bg-rose-950/20 p-3 text-xs font-mono text-rose-300">
          <div><strong>Entity:</strong> {fault.entity_id.toUpperCase()}</div>
          <div><strong>Recoverable:</strong> {fault.is_recoverable ? 'Yes' : 'No'}</div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onAbort}
            className="w-full sm:w-auto border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
          >
            <XCircle className="mr-2 h-4 w-4" />
            Abort Simulation
          </Button>

          {fault.is_recoverable && (
            <Button
              type="button"
              onClick={onRetry}
              className="w-full sm:w-auto bg-emerald-600 text-white hover:bg-emerald-500 font-medium"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry Turn
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
