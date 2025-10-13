import { io, Socket } from 'socket.io-client';

/**
 * RPC 请求接口
 */
export interface RPCRequest {
  id: string;
  method: string;
  params?: any;
  meta?: {
    v: number;
    ts: number;
  };
}

/**
 * RPC 响应接口
 */
export interface RPCResponse {
  id: string;
  result?: any;
}

/**
 * RPC 错误接口
 */
export interface RPCError {
  id: string;
  error: {
    code: string;
    message: string;
    data?: any;
  };
}

/**
 * RPC 通知接口
 */
export interface RPCNotify {
  topic: string;
  data: any;
  ts: number;
}

/**
 * RPC 流式响应接口
 */
export interface RPCStream {
  id: string;
  event: 'progress' | 'data' | 'end' | 'error';
  data?: any;
  progress?: {
    current: number;
    total: number;
  };
}

/**
 * Socket.IO RPC客户端类
 * 提供与服务器进行RPC通信的功能，包括方法调用、通知订阅、流式响应等
 */
export interface RPCErrorContext {
  type: 'rpc-error' | 'stream-error' | 'connect-failed' | 'timeout' | 'connect-error';
  method?: string;
  id?: string;
  raw?: any;
}

class RPCClient {
  private socket: Socket | null = null;
  private pendingCalls = new Map<string, { resolve: (value: any) => void; reject: (reason: any) => void }>();
  private notifyHandlers = new Map<string, Set<(data: any, ts: number) => void>>();
  private streamHandlers = new Map<string, (stream: RPCStream) => void>();
  private connectionHandlers = new Set<(connected: boolean) => void>();
  private errorHandlers = new Set<(error: Error, context: RPCErrorContext) => void>();

  private emitError(error: Error, context: RPCErrorContext) {
    this.errorHandlers.forEach((h) => {
      try {
        h(error, context);
      } catch (e) {
        console.error('[RPC] error handler error:', e);
      }
    });
  }

  /**
   * RPC客户端构造函数
   * 自动建立与服务器的连接
   */
  constructor() {
    this.connect();
  }

  /**
   * 连接到服务器
   * 开发环境连接当前主机（Vite 会代理），生产环境连接到指定地址
   */
  private connect() {
    // 开发环境连接当前主机（Vite 会代理），生产环境连接到指定地址
    const url = import.meta.env.DEV ? '' : 'http://127.0.0.1:8000';
    
    this.socket = io(url, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
    });

    // 连接事件
    this.socket.on('connect', () => {
      console.log('[RPC] Connected to server');
      this.notifyConnectionHandlers(true);
    });

    this.socket.on('disconnect', () => {
      console.log('[RPC] Disconnected from server');
      this.notifyConnectionHandlers(false);
    });

    this.socket.on('connect_error', (error) => {
      console.error('[RPC] Connection error:', error);
      this.emitError(new Error('Connection error'), { type: 'connect-error', raw: error });
    });

    // RPC 响应
    this.socket.on('rpc/res', (response: RPCResponse) => {
      const pending = this.pendingCalls.get(response.id);
      if (!pending) return;

      pending.resolve(response.result);
      this.pendingCalls.delete(response.id);
    });

    // RPC 错误
    this.socket.on('rpc/err', (error: RPCError) => {
      const pending = this.pendingCalls.get(error.id);
      if (!pending) return;

      const err = new Error(`[${error.error.code}] ${error.error.message}`);
      this.emitError(err, { type: 'rpc-error', id: error.id, raw: error });
      pending.reject(err);
      this.pendingCalls.delete(error.id);
    });

    // 服务端通知
    this.socket.on('rpc/notify', (notify: RPCNotify) => {
      const handlers = this.notifyHandlers.get(notify.topic);
      if (!handlers) return;

      handlers.forEach(handler => {
        try {
          handler(notify.data, notify.ts);
        } catch (err) {
          console.error(`[RPC] Notify handler error for ${notify.topic}:`, err);
        }
      });
    });

    // 流式响应
    this.socket.on('rpc/stream', (stream: RPCStream) => {
      const handler = this.streamHandlers.get(stream.id);
      if (!handler) return;

      try {
        handler(stream);
        if (stream.event === 'end' || stream.event === 'error') {
          if (stream.event === 'error') {
            const msg = typeof stream.data === 'string' ? stream.data : '流式请求出错';
            this.emitError(new Error(msg), { type: 'stream-error', id: stream.id, raw: stream });
          }
          this.streamHandlers.delete(stream.id);
        }
      } catch (err) {
        console.error(`[RPC] Stream handler error for ${stream.id}:`, err);
      }
    });
  }

  /**
   * 等待连接建立
   * @param timeout 超时时间（毫秒），默认为10000ms
   * @returns Promise<void>
   */
  private async waitForConnection(timeout: number = 10000): Promise<void> {
    if (this.socket?.connected) {
      return;
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        cleanup();
        reject(new Error('Connection timeout'));
      }, timeout);

      const onConnect = () => {
        cleanup();
        resolve();
      };

      const cleanup = () => {
        clearTimeout(timeoutId);
        this.socket?.off('connect', onConnect);
      };

      this.socket?.once('connect', onConnect);
    });
  }

  /**
   * 调用 RPC 方法
   * @template T 返回值的类型
   * @param method RPC方法名
   * @param params 方法参数，可选
   * @returns Promise<T> 返回RPC调用的结果
   */
  async call<T = any>(method: string, params?: any): Promise<T> {
    // 等待连接建立（最多等待 10 秒）
    try {
      await this.waitForConnection(10000);
    } catch {
      const err = new Error('Failed to connect to server');
      this.emitError(err, { type: 'connect-failed' });
      throw err;
    }

    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const request: RPCRequest = {
      id,
      method,
      params,
      meta: {
        v: 1,
        ts: Date.now(),
      },
    };

    return new Promise((resolve, reject) => {
      this.pendingCalls.set(id, { resolve, reject });
      
      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingCalls.delete(id);
        const err = new Error(`RPC call timeout: ${method}`);
        this.emitError(err, { type: 'timeout', method });
        reject(err);
      }, 30000); // 30秒超时

      this.socket!.emit('rpc/req', request);

      // 清理超时
      const originalResolve = resolve;
      const originalReject = reject;
      this.pendingCalls.set(id, {
        resolve: (result: any) => {
          clearTimeout(timeout);
          originalResolve(result);
        },
        reject: (error: any) => {
          clearTimeout(timeout);
          originalReject(error);
        },
      });
    });
  }

  /**
   * 订阅通知主题
   * @param topic 通知主题名
   * @param handler 通知处理函数，接收数据和时间戳
   * @returns 取消订阅函数
   */
  on(topic: string, handler: (data: any, ts: number) => void): () => void {
    if (!this.notifyHandlers.has(topic)) {
      this.notifyHandlers.set(topic, new Set());
    }

    this.notifyHandlers.get(topic)!.add(handler);

    // 返回取消订阅函数
    return () => {
      const handlers = this.notifyHandlers.get(topic);
      if (!handlers) return;

      handlers.delete(handler);
      if (handlers.size === 0) {
        this.notifyHandlers.delete(topic);
      }
    };
  }

  /**
   * 订阅流式响应
   * @param id 流式响应ID
   * @param handler 流处理函数
   */
  stream(id: string, handler: (stream: RPCStream) => void) {
    this.streamHandlers.set(id, handler);
  }

  /**
   * 监听连接状态
   * @param handler 连接状态变化处理函数
   * @returns 取消订阅函数
   */
  onConnection(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.add(handler);
    // 立即触发一次当前状态
    handler(this.socket?.connected ?? false);
    
    // 返回取消订阅函数
    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  /**
   * 通知所有连接状态监听器
   * @param connected 连接状态
   */
  private notifyConnectionHandlers(connected: boolean) {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (err) {
        console.error('[RPC] Connection handler error:', err);
      }
    });
  }

  /**
   * 获取连接状态
   * @returns 是否已连接
   */
  get connected(): boolean {
    return this.socket?.connected ?? false;
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.socket?.disconnect();
  }

  /**
   * 订阅全局错误
   */
  onError(handler: (error: Error, context: RPCErrorContext) => void): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }
}

// 导出单例
export const rpcClient = new RPCClient();

// 便捷方法
/**
 * 便捷方法：调用RPC方法
 * @template T 返回值的类型
 * @param method RPC方法名
 * @param params 方法参数，可选
 * @returns Promise<T> 返回RPC调用的结果
 */
export const call = <T = any>(method: string, params?: any) => rpcClient.call<T>(method, params);

/**
 * 便捷方法：订阅通知主题
 * @param topic 通知主题名
 * @param handler 通知处理函数，接收数据和时间戳
 * @returns 取消订阅函数
 */
export const on = (topic: string, handler: (data: any, ts: number) => void) => rpcClient.on(topic, handler);

/**
 * 便捷方法：监听连接状态
 * @param handler 连接状态变化处理函数
 * @returns 取消订阅函数
 */
export const onConnection = (handler: (connected: boolean) => void) => rpcClient.onConnection(handler);

