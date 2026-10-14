import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { apiClient } from '../services/apiClient';
import { Trash2, AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';

interface DeleteDatabaseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const DeleteDatabaseModal: React.FC<DeleteDatabaseModalProps> = ({
  open,
  onOpenChange,
}) => {
  const [confirmText, setConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [resultMsg, setResultMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isConfirmed = confirmText.trim().toUpperCase() === 'DELETE';

  const handleDelete = async () => {
    if (!isConfirmed) return;
    setIsDeleting(true);
    setErrorMsg(null);
    setResultMsg(null);

    try {
      const res = await apiClient.deleteDatabase();
      const tablesCount =
        res.tables_purged ??
        res.cleared_tables?.length ??
        res.tables_cleared?.length ??
        15;
      const durationStr =
        res.duration_ms !== undefined ? ` in ${res.duration_ms.toFixed(1)}ms` : '';
      const recordsStr =
        res.records_deleted !== undefined && res.records_deleted > 0
          ? `${res.records_deleted.toLocaleString()} records removed across `
          : '';
      setResultMsg(
        `Database purged: ${recordsStr}all ${tablesCount} relational tables cleared${durationStr}.`
      );
      setConfirmText('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete database.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    if (isDeleting) return;
    setConfirmText('');
    setResultMsg(null);
    setErrorMsg(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="border-rose-900/40 bg-slate-900 text-slate-100 max-w-md">
        <DialogHeader className="space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/10 text-rose-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <DialogTitle className="text-center text-lg text-rose-200">
            Delete Database Records
          </DialogTitle>
          <DialogDescription className="text-center text-sm text-slate-300">
            This will permanently delete all simulation history, benchmark runs, player hands, card observations, and decision metrics across all 15 tables. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {resultMsg ? (
          <div className="my-3 flex items-center space-x-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
            <span>{resultMsg}</span>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {errorMsg && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
                {errorMsg}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="confirm-delete" className="text-xs text-slate-300">
                Type <strong className="text-rose-400 font-mono">DELETE</strong> to confirm:
              </Label>
              <Input
                id="confirm-delete"
                placeholder="DELETE"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="font-mono text-sm border-slate-700 bg-slate-950 focus:border-rose-500"
              />
            </div>
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isDeleting}
            className="w-full sm:w-auto border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
          >
            {resultMsg ? 'Close' : 'Cancel'}
          </Button>

          {!resultMsg && (
            <Button
              type="button"
              variant="destructive"
              disabled={!isConfirmed || isDeleting}
              onClick={handleDelete}
              className="w-full sm:w-auto bg-rose-600 hover:bg-rose-500 text-white font-medium"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Purging Database...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Permanently Delete
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
