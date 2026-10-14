import { InboundTelemetryEvent, OutboundCommand } from '../types/api';

const WS_BASE_URL =
  import.meta.env.VITE_WS_URL ||
  (window.location.protocol === 'https:' ? 'wss:' : 'ws:') +
    '//' +
    (import.meta.env.VITE_API_HOST || window.location.hostname + ':8000');

export type TelemetryEventHandler = (event: InboundTelemetryEvent) => void;

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private sessionId: string | null = null;
  private listeners: Set<TelemetryEventHandler> = new Set();
  private reconnectTimeout: any = null;
  private shouldReconnect: boolean = false;

  connect(sessionId: string): void {
    if (this.socket && this.sessionId === sessionId) {
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        return;
      }
    }

    this.disconnect();
    this.sessionId = sessionId;
    this.shouldReconnect = true;

    const url = `${WS_BASE_URL}/ws/simulations/${sessionId}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log(`[WebSocket] Connected to session ${sessionId}`);
    };

    this.socket.onmessage = (event) => {
      try {
        const parsed: InboundTelemetryEvent = JSON.parse(event.data);
        this.notify(parsed);
      } catch (err) {
        console.error('[WebSocket] Failed to parse event JSON:', err, event.data);
      }
    };

    this.socket.onclose = (event) => {
      console.log(`[WebSocket] Closed (code: ${event.code}, reason: ${event.reason})`);
      if (this.shouldReconnect && event.code !== 4404 && event.code !== 1000) {
        this.reconnectTimeout = setTimeout(() => {
          if (this.sessionId && this.shouldReconnect) {
            console.log('[WebSocket] Reconnecting...');
            this.connect(this.sessionId);
          }
        }, 1500);
      }
    };

    this.socket.onerror = (err) => {
      console.error('[WebSocket] Socket error:', err);
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onclose = null;
      this.socket.onerror = null;
      if (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING) {
        this.socket.close(1000, 'Client disconnected');
      }
      this.socket = null;
    }
    this.sessionId = null;
  }

  sendCommand(cmd: OutboundCommand): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(cmd));
    } else {
      console.warn('[WebSocket] Cannot send command, socket not open:', cmd);
    }
  }

  subscribe(handler: TelemetryEventHandler): () => void {
    this.listeners.add(handler);
    return () => {
      this.listeners.delete(handler);
    };
  }

  private notify(event: InboundTelemetryEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch (err) {
        console.error('[WebSocket] Listener threw error:', err);
      }
    }
  }

  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketClient();
