import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

type ToastLevel = 'success' | 'danger' | 'warning' | 'info';

interface ToastItem {
  id: string;
  level: ToastLevel;
  message: string;
  title?: string;
  durationMs: number;
}

export interface ToastContextType {
  success: (message: string, title?: string, durationMs?: number) => void;
  error: (message: string, title?: string, durationMs?: number) => void;
  warning: (message: string, title?: string, durationMs?: number) => void;
  info: (message: string, title?: string, durationMs?: number) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
}

export const ToastProvider: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timeoutsRef = useRef<Map<string, number>>(new Map());
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set());

  const removeToast = useCallback((id: string) => {
    // 先触发退场动画
    setVisibleIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    const handle = timeoutsRef.current.get(id);
    if (handle) {
      window.clearTimeout(handle);
      timeoutsRef.current.delete(id);
    }
    // 等待动画结束后再移除节点
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 220);
  }, []);

  const addToast = useCallback((level: ToastLevel, message: string, title?: string, durationMs: number = 3500) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const item: ToastItem = { id, level, message, title, durationMs };
    setToasts((prev) => [item, ...prev].slice(0, 8));
    // 下一帧再标记为可见，触发入场动画
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setVisibleIds((prev) => {
          const next = new Set(prev);
          next.add(id);
          return next;
        });
      });
    });
    const handle = window.setTimeout(() => removeToast(id), durationMs);
    timeoutsRef.current.set(id, handle);
  }, [removeToast]);

  const contextValue = useMemo<ToastContextType>(() => ({
    success: (message, title, durationMs) => addToast('success', message, title, durationMs),
    error: (message, title, durationMs) => addToast('danger', message, title, durationMs),
    warning: (message, title, durationMs) => addToast('warning', message, title, durationMs),
    info: (message, title, durationMs) => addToast('info', message, title, durationMs),
  }), [addToast]);

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: 'fixed',
          top: 12,
          right: 12,
          zIndex: 1080,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          pointerEvents: 'none',
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            style={{
              pointerEvents: 'auto',
              minWidth: 260,
              maxWidth: 420,
              backgroundColor: '#fff',
              borderLeft: `4px solid ${
                t.level === 'success' ? '#198754' :
                t.level === 'danger' ? '#dc3545' :
                t.level === 'warning' ? '#ffc107' : '#0dcaf0'}`,
              boxShadow: '0 6px 16px rgba(0,0,0,0.15)',
              borderRadius: 6,
              padding: '10px 36px 10px 12px',
              position: 'relative',
              transition: 'transform 200ms ease, opacity 200ms ease',
              transform: visibleIds.has(t.id) ? 'translateY(0)' : 'translateY(-6px)',
              opacity: visibleIds.has(t.id) ? 1 : 0,
            }}
          >
            <button
              aria-label="关闭通知"
              onClick={() => removeToast(t.id)}
              style={{
                position: 'absolute',
                top: 6,
                right: 6,
                width: 24,
                height: 24,
                border: 'none',
                background: 'transparent',
                color: '#6c757d',
                cursor: 'pointer',
                borderRadius: 4,
              }}
            >
              ×
            </button>
            {t.title && (
              <div style={{ fontWeight: 600, marginBottom: 4 }}>
                {t.title}
              </div>
            )}
            <div style={{ fontSize: 14, color: '#333' }}>{t.message}</div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};


