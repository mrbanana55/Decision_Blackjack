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
      <DialogContent className="border-[#2b305c] bg-[#1e2353] text-white max-w-md">
        <DialogHeader className="space-y-3 pb-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-sm bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertCircle className="h-6 w-6" />
          </div>
          <DialogTitle className="text-center text-lg text-rose-200">
            Provider Fault Detected (RNF-02)
          </DialogTitle>
          <DialogDescription className="text-center text-xs text-[#949ba4] leading-relaxed">
            {fault.error_message || `Execution paused due to provider fault for ${fault.entity_id}.`}
          </DialogDescription>
        </DialogHeader>

        <div className="my-2 rounded-sm border border-rose-500/30 bg-[#0a0d3a] p-3 text-xs font-mono text-rose-300 space-y-1">
          <div><strong className="text-white">Entity:</strong> {fault.entity_id.toUpperCase()}</div>
          <div><strong className="text-white">Recoverable:</strong> {fault.is_recoverable ? 'Yes' : 'No'}</div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 pt-3 border-t border-[#2b305c]/60">
          <Button
            type="button"
            variant="outline"
            onClick={onAbort}
            className="w-full sm:w-auto h-9 px-4 text-xs"
          >
            <XCircle className="mr-2 h-4 w-4" />
            Abort Simulation
          </Button>

          {fault.is_recoverable && (
            <Button
              type="button"
              variant="green"
              onClick={onRetry}
              className="w-full sm:w-auto h-9 px-4 text-xs"
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
