import {
  CreateSimulationPayload,
  OutboundCommand,
  PurgeDatabaseResponse,
  SimulationResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async createSimulation(payload: CreateSimulationPayload): Promise<SimulationResponse> {
    const res = await fetch(`${this.baseUrl}/api/simulations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Failed to create simulation: ${res.statusText}`);
    }

    return res.json();
  }

  async controlSimulation(sessionId: string, command: OutboundCommand): Promise<any> {
    const res = await fetch(`${this.baseUrl}/api/simulations/${sessionId}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Control command failed: ${res.statusText}`);
    }

    return res.json();
  }

  async exportSimulationData(sessionId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/export/simulations/${sessionId}`);
    if (!res.ok) {
      throw new Error(`Export failed: ${res.statusText}`);
    }

    const blob = await res.blob();
    const disposition = res.headers.get('content-disposition');
    let filename = `simulation_${sessionId}_export.json`;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    this.triggerDownload(blob, filename);
  }

  async exportDatabase(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/export/database`);
    if (!res.ok) {
      throw new Error(`Database export failed: ${res.statusText}`);
    }

    const blob = await res.blob();
    const disposition = res.headers.get('content-disposition');
    let filename = `decision_blackjack_full_export_${new Date().toISOString().slice(0, 10)}.json`;
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    this.triggerDownload(blob, filename);
  }

  async deleteDatabase(): Promise<PurgeDatabaseResponse> {
    const res = await fetch(`${this.baseUrl}/api/database`, {
      method: 'DELETE',
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Failed to purge database: ${res.statusText}`);
    }

    return res.json();
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}

export const apiClient = new ApiClient();
