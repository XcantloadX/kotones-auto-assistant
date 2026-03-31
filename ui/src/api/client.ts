import { useEffect, useRef, useCallback } from 'react';
import { useConnectionStore } from '../store/connectionStore';

type EventHandler = (data: unknown) => void;

type RpcRequest = {
  id: string;
  method: string;
  params?: Record<string, unknown>;
};

type RpcResponse = {
  id: string;
  result?: unknown;
  error?: { code: number; message: string };
};

type ServerEvent = {
  event: string;
  data: unknown;
};

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
};

let wsInstance: WebSocket | null = null;
const pendingRequests = new Map<string, PendingRequest>();
const eventHandlers = new Map<string, Set<EventHandler>>();

function getWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws`;
}

function generateId(): string {
  return Math.random().toString(36).slice(2);
}

let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let connectionStore: ReturnType<typeof useConnectionStore.getState> | null = null;

function connect() {
  const store = useConnectionStore.getState();
  store.setStatus('connecting');

  const ws = new WebSocket(getWsUrl());
  wsInstance = ws;

  ws.onopen = () => {
    useConnectionStore.getState().setStatus('connected');
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  ws.onclose = () => {
    useConnectionStore.getState().setStatus('disconnected');
    wsInstance = null;
    // Reject all pending requests
    pendingRequests.forEach(({ reject }) => {
      reject(new Error('WebSocket disconnected'));
    });
    pendingRequests.clear();
    // Reconnect after 2 seconds
    reconnectTimer = setTimeout(connect, 2000);
  };

  ws.onerror = () => {
    useConnectionStore.getState().setStatus('error');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data as string) as RpcResponse | ServerEvent;

      if ('event' in msg) {
        // Server-pushed event
        const handlers = eventHandlers.get(msg.event);
        if (handlers) {
          handlers.forEach(h => h(msg.data));
        }
      } else if ('id' in msg) {
        // RPC response
        const pending = pendingRequests.get(msg.id);
        if (pending) {
          pendingRequests.delete(msg.id);
          if (msg.error) {
            pending.reject(new Error(msg.error.message));
          } else {
            pending.resolve(msg.result);
          }
        }
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
}

export function initWs() {
  if (!wsInstance) {
    connect();
  }
}

export function call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T> {
  return new Promise((resolve, reject) => {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) {
      reject(new Error('WebSocket not connected'));
      return;
    }

    const id = generateId();
    const req: RpcRequest = { id, method, params };

    pendingRequests.set(id, {
      resolve: (v) => resolve(v as T),
      reject,
    });

    wsInstance.send(JSON.stringify(req));

    // Timeout after 30 seconds
    setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        reject(new Error(`RPC timeout: ${method}`));
      }
    }, 30000);
  });
}

export function on(event: string, handler: EventHandler): () => void {
  if (!eventHandlers.has(event)) {
    eventHandlers.set(event, new Set());
  }
  eventHandlers.get(event)!.add(handler);

  return () => {
    eventHandlers.get(event)?.delete(handler);
  };
}

/** React hook for subscribing to a server event */
export function useEvent(event: string, handler: EventHandler) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    const off = on(event, (data) => handlerRef.current(data));
    return off;
  }, [event]);
}

/** React hook for using the connection status */
export { useConnectionStore };
