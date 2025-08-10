import { baseURL } from "./http";

export type AppEvent<T = unknown> = { type: string; data: T; ts: number };

export type EventsOptions = {
  path?: string;
  onEvent: (ev: AppEvent) => void;
  onError?: (err: unknown) => void;
  vitalPolls?: (() => Promise<void>)[];
};

export function startSSE(options: EventsOptions) {
  const path = options.path ?? "/api/v1/events";
  let stopped = false;
  let es: EventSource | null = null;
  let retry = 0;
  let pollTimer: number | null = null;

  const backoff = () => Math.min(30000, 1000 * Math.pow(2, retry)) + Math.floor(Math.random() * 500);

  const startPolling = () => {
    if (pollTimer != null) return;
    pollTimer = window.setInterval(async () => {
      if (stopped) return;
      await Promise.all(options.vitalPolls?.map((fn) => fn()) ?? []);
    }, 3000);
  };

  const stopPolling = () => {
    if (pollTimer != null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  };

  const connect = () => {
    if (stopped) return;
    try {
      es = new EventSource(baseURL + path, { withCredentials: false });
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          options.onEvent(data);
        } catch {}
      };
      es.onerror = async () => {
        es?.close();
        es = null;
        retry++;
        options.onError?.(new Error("sse error"));
        startPolling();
        setTimeout(connect, backoff());
      };
      es.onopen = () => {
        retry = 0;
        stopPolling();
      };
    } catch (e) {
      options.onError?.(e);
      startPolling();
      setTimeout(connect, backoff());
    }
  };

  // 如果浏览器不支持 SSE，直接降级为轮询
  if (!("EventSource" in window)) {
    startPolling();
  } else {
    connect();
  }

  return () => {
    stopped = true;
    es?.close();
    stopPolling();
  };
} 