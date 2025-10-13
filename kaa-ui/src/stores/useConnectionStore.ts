import { create } from 'zustand';
import { onConnection } from '../lib/rpc';

interface ConnectionState {
  connected: boolean;
  setConnected: (connected: boolean) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => {
  // 订阅连接状态
  onConnection((connected) => {
    set({ connected });
  });

  return {
    connected: false,
    setConnected: (connected) => set({ connected }),
  };
});

