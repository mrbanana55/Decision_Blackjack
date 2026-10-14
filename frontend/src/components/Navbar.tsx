import React, { useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
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
      <header className="sticky top-0 z-30 border-b border-[#2b305c]/80 bg-[#0a0d3a]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Brand mark */}
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-[#5865f2] text-white shadow-lg shadow-[#5865f2]/30">
              <Dices className="h-5 w-5" />
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-display text-lg font-extrabold tracking-tight text-white uppercase">
                Decision Blackjack
              </span>
              <Badge variant="magenta" className="hidden sm:inline-flex text-[10px] uppercase font-bold tracking-wider px-2 py-0.5">
                Benchmark Studio
              </Badge>
            </div>
          </div>

          {/* Global Actions */}
          <div className="flex items-center space-x-2.5">
            {/* Info Button: circle with an i inside */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInfoModalOpen(true)}
              className="h-9 w-9 rounded-full p-0 border-[#2b305c] bg-[#1e2353] text-[#00b0f4] hover:bg-[#5865f2] hover:text-white hover:border-[#5865f2] shadow-sm transition-all"
              title="About Decision Blackjack"
            >
              <Info className="h-4 w-4" />
              <span className="sr-only">About Decision Blackjack</span>
            </Button>

            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={isExporting}
              onClick={handleExportDatabase}
              className="text-xs h-9 px-3.5 border-[#2b305c] bg-[#1e2353] hover:bg-[#262c69] text-white font-semibold"
            >
              {isExporting ? (
                <>
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin text-[#fee75c]" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="mr-1.5 h-3.5 w-3.5 text-[#00b0f4]" />
                  Export Database
                </>
              )}
            </Button>

            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => setDeleteModalOpen(true)}
              className="text-xs h-9 px-3.5"
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5" />
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
