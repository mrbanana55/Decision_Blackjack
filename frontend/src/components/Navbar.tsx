import React, { useState } from 'react';
import { Button } from './ui/button';
import { DeleteDatabaseModal } from './DeleteDatabaseModal';
import { InfoModal } from './InfoModal';
import { apiClient } from '../services/apiClient';
import { Dices, Download, Trash2, Loader2, Info } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExportDatabase = async () => {
    setIsExporting(true);
    try {
      await apiClient.exportDatabase();
    } catch (err) {
      console.error('Failed to export whole database:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Brand */}
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Dices className="h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-slate-100">
                Decision Blackjack
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs text-slate-500">
                Benchmark Studio
              </span>
            </div>
          </div>

          {/* Global Startup Actions */}
          <div className="flex items-center space-x-2">
            {/* Info Button: circle with an i inside */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInfoModalOpen(true)}
              className="h-8 w-8 rounded-full p-0 border-slate-700 bg-slate-900 text-cyan-400 hover:bg-slate-800 hover:text-cyan-300 shadow-sm"
              title="About Decision Blackjack"
            >
              <Info className="h-4 w-4" />
              <span className="sr-only">About Decision Blackjack</span>
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isExporting}
              onClick={handleExportDatabase}
              className="border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 text-xs h-8 px-3"
            >
              {isExporting ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin text-amber-400" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="mr-1.5 h-3.5 w-3.5 text-cyan-400" />
                  Export Whole Database
                </>
              )}
            </Button>

            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => setDeleteModalOpen(true)}
              className="bg-rose-600/20 text-rose-300 hover:bg-rose-600/30 border border-rose-500/30 text-xs h-8 px-3"
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5 text-rose-400" />
              Delete Database
            </Button>
          </div>
        </div>
      </header>

      {/* Database Purge Confirmation Modal */}
      <DeleteDatabaseModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
      />

      {/* Program Information Modal */}
      <InfoModal
        open={infoModalOpen}
        onOpenChange={setInfoModalOpen}
      />
    </>
  );
};
