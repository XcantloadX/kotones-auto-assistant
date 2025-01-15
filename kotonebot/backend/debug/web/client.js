/**
 * @typedef {Object} ImageData
 * @property {'memory' | 'file'} type - 图片数据类型
 * @property {string[]} value - 图片路径或内存键数组
 */

/**
 * @typedef {Object} VisualData
 * @property {ImageData} image - 图片数据
 * @property {string} name - 可视化标题
 * @property {string} details - 详细文本信息
 */

/**
 * @typedef {Object} VisualEvent
 * @property {'visual'} type - 事件类型
 * @property {VisualData} data - 可视化数据
 */

/**
 * @typedef {Object} ErrorEvent 
 * @property {string} error - 错误信息
 */

/**
 * @typedef {Object} ConnectionStatusEvent
 * @property {boolean} connected - 连接状态
 */

/**
 * @typedef {'visual' | 'connectionStatus'} KotoneDebugEvents
 */

/**
 * @template {KotoneDebugEvents} T
 * @typedef {T extends 'visual' ? VisualEvent : T extends 'connectionStatus' ? ConnectionStatusEvent : never} EventTypeMap
 */

class KotoneDebugClient {
    /** @type {WebSocket} */
    #ws;
    /** @type {Map<string, Function[]>} */
    #eventListeners;
    /** @type {boolean} */
    #isReconnecting;
    /** @type {string} */
    #serverUrl;

    /**
     * @param {string} ip - 服务器IP地址
     */
    constructor(ip) {
        this.#serverUrl = `ws://${ip}/ws`;
        this.#eventListeners = new Map();
        this.#isReconnecting = false;
        this.#connect();
    }

    /**
     * 添加事件监听器
     * @template {KotoneDebugEvents} T
     * @param {T} event - 事件类型
     * @param {(e: EventTypeMap<T>) => void} callback - 回调函数
     */
    addEventListener(event, callback) {
        if (!this.#eventListeners.has(event)) {
            this.#eventListeners.set(event, []);
        }
        this.#eventListeners.get(event).push(callback);
    }

    /**
     * 移除事件监听器
     * @template {KotoneDebugEvents} T
     * @param {T} event - 事件类型
     * @param {(e: EventTypeMap<T>) => void} callback - 回调函数
     */
    removeEventListener(event, callback) {
        if (!this.#eventListeners.has(event)) return;
        const listeners = this.#eventListeners.get(event);
        const index = listeners.indexOf(callback);
        if (index !== -1) {
            listeners.splice(index, 1);
        }
    }

    /**
     * 连接WebSocket服务器
     * @private
     */
    #connect() {
        if (this.#isReconnecting) return;
        this.#isReconnecting = true;

        this.#ws = new WebSocket(this.#serverUrl);
        
        this.#ws.onopen = () => {
            console.log('WebSocket connected');
            this.#isReconnecting = false;
            this.#dispatchEvent('connectionStatus', { connected: true });
        };
        
        this.#ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.error) {
                console.error('WebSocket error:', data.error);
                return;
            }
            
            if (data.type === 'visual') {
                this.#dispatchEvent('visual', data);
            }
        };
        
        this.#ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.#dispatchEvent('connectionStatus', { connected: false });
            // 开始检查服务器状态
            this.#checkServerStatus();
        };
        
        this.#ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.#dispatchEvent('connectionStatus', { connected: false });
        };
    }

    /**
     * 检查服务器状态
     * @private
     */
    async #checkServerStatus() {
        try {
            const response = await fetch('/api/ping');
            if (response.ok) {
                // 服务器恢复了，重新连接
                this.#connect();
            } else {
                setTimeout(() => this.#checkServerStatus(), 2000);
            }
        } catch (e) {
            // 服务器仍然不可用，继续尝试
            setTimeout(() => this.#checkServerStatus(), 2000);
        }
    }

    /**
     * 分发事件
     * @private
     * @param {string} event - 事件类型
     * @param {any} data - 事件数据
     */
    #dispatchEvent(event, data) {
        if (!this.#eventListeners.has(event)) return;
        const listeners = this.#eventListeners.get(event);
        listeners.forEach(callback => callback(data));
    }
}
