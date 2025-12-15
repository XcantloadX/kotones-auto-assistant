from typing import Optional, Dict, Any

import gradio as gr

# 图标 SVG 定义
ICONS: Dict[str, str] = {
    "success": """<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />""",
    "info": """<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />""",
    "warning": """<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />""",
    "error": """<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />"""
}

class Alert(gr.HTML):
    def __init__(
        self, 
        value: str = "Alert Content", 
        title: Optional[str] = None, 
        variant: str = "info", 
        action_text: Optional[str] = None, 
        show_close: bool = True, 
        visible: bool = True, 
        elem_id: Optional[str] = None, 
        **kwargs: Any
    ):
        """
        继承自 gr.HTML 的自定义 Alert 组件。
        
        Args:
            value: Alert 的主要描述文本。
            title: Alert 的标题（可选）。
            variant: 样式变体，可选 "success", "info", "warning", "error"。
            action_text: 底部操作按钮的文本（可选）。
            show_close: 是否显示关闭按钮。
            visible: 组件初始可见性。
            elem_id: HTML 元素 ID。
            **kwargs: 其他传递给 gr.HTML 的参数。
        """
        
        # 样式已移至 JS on_load 动态注入以避免使用 `css_template` 属性

        # 2. HTML 模板 (HTML Template)
        # 修改点：重构 HTML 结构，将 button 放入 .alert-body-wrapper 中
        html_template = """
        <div class="alert alert-${variant}" role="alert">
            <svg class="alert-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                ${ {
                    'success': `""" + ICONS['success'] + """`,
                    'info': `""" + ICONS['info'] + """`,
                    'warning': `""" + ICONS['warning'] + """`,
                    'error': `""" + ICONS['error'] + """`
                }[variant] }
            </svg>
            
            <div class="alert-body-wrapper">
                ${ title ? `<div class="alert-title">${title}</div>` : '' }
                <div class="alert-description">${value}</div>
                
                ${ action_text ? `
                <div class="alert-actions">
                    <button class="action-btn">${action_text}</button>
                </div>` : '' }
            </div>
            
            ${ show_close ? `
            <button class="close-btn" aria-label="Close">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
            </button>` : '' }
        </div>
        """

        # 3. JS 加载逻辑 (JS on Load)
        js = """
        // 动态注入样式（带去重检查）
        (function(){
            const STYLE_ID = 'kaa-alert-styles';
            if (!document.getElementById(STYLE_ID)) {
                const style = document.createElement('style');
                style.id = STYLE_ID;
                style.innerHTML = `
        .alert {
            display: flex;
            align-items: flex-start; /* 顶部对齐 */
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid transparent;
            margin-bottom: 1rem;
            transition: opacity 0.3s ease;
        }
        
        .alert-icon { 
            width: 1.25rem; 
            height: 1.25rem; 
            margin-right: 0.75rem; 
            flex-shrink: 0; 
        }
        
        .alert-body-wrapper {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.25rem; /* 标题、描述、按钮之间的间距 */
        }
        
        .alert-title { 
            font-weight: 600; 
            font-size: 0.875rem; 
        }
        
        .alert-description { 
            font-size: 0.875rem; 
            line-height: 1.25rem; 
        }
        
        .alert-actions { 
            display: flex; 
            align-items: center; 
            gap: 0.5rem; 
            margin-top: 0.25rem; /* 按钮与上方文字的额外间距 */
        }
        
        /* Variants Colors */
        .alert-success { background-color: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
        .alert-success .alert-icon, .alert-success .action-btn { color: #059669; }
        
        .alert-info { background-color: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
        .alert-info .alert-icon, .alert-info .action-btn { color: #2563eb; }
        
        .alert-warning { background-color: #fffbeb; border-color: #fde68a; color: #92400e; }
        .alert-warning .alert-icon, .alert-warning .action-btn { color: #d97706; }
        
        .alert-error { background-color: #fef2f2; border-color: #fecaca; color: #991b1b; }
        .alert-error .alert-icon, .alert-error .action-btn { color: #dc2626; }

        /* Buttons */
        .action-btn { 
            background: transparent; 
            border: none; 
            font-weight: 600; 
            cursor: pointer; 
            padding: 0; /* 移除 padding 以便像链接一样对齐，或者保留 padding 做成按钮样式 */
            padding-right: 0.5rem;
            font-size: 0.875rem;
            text-align: left;
        }
        .action-btn:hover { text-decoration: underline; }
        
        .close-btn { 
            background: transparent; 
            border: none; 
            cursor: pointer; 
            opacity: 0.6; 
            padding: 0.25rem; 
            margin-left: 0.75rem; /* 离内容稍微远一点 */
            flex-shrink: 0;
            display: flex; 
        }
        .close-btn:hover { opacity: 1; }
        .close-btn svg { width: 1rem; height: 1rem; }

        /* Dark Mode Support */
        body.dark .alert-success { background-color: #064e3b; border-color: #059669; color: #d1fae5; }
        body.dark .alert-success .alert-icon, body.dark .alert-success .action-btn { color: #34d399; }
        
        body.dark .alert-info { background-color: #1e3a8a; border-color: #1d4ed8; color: #dbeafe; }
        body.dark .alert-info .alert-icon, body.dark .alert-info .action-btn { color: #60a5fa; }
        
        body.dark .alert-warning { background-color: #451a03; border-color: #b45309; color: #fef3c7; }
        body.dark .alert-warning .alert-icon, body.dark .alert-warning .action-btn { color: #fbbf24; }
        
        body.dark .alert-error { background-color: #450a0a; border-color: #b91c1c; color: #fee2e2; }
        body.dark .alert-error .alert-icon, body.dark .alert-error .action-btn { color: #f87171; }
                `;
                document.head.appendChild(style);
            }
        })();

        const actionBtn = element.querySelector('.action-btn');
        const closeBtn = element.querySelector('.close-btn');
        const alertBox = element.querySelector('.alert');

        if (actionBtn) {
            actionBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // 防止冒泡
                trigger('click', {
                    action_text: props.action_text,
                    variant: props.variant
                });
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                alertBox.style.opacity = '0';
                setTimeout(() => {
                    alertBox.style.display = 'none';
                    // 触发 change 事件通知后端状态变化
                    trigger('change', { status: 'closed' });
                }, 300);
            });
        }
        """

        super().__init__(
            value=value,
            title=title,
            variant=variant,
            action_text=action_text,
            show_close=show_close,
            html_template=html_template,
            js_on_load=js,
            visible=visible,
            elem_id=elem_id,
            **kwargs
        )

# --- 使用示例 ---

if __name__ == "__main__":
    with gr.Blocks() as demo:
        gr.Markdown("### Alert Component with Typed Arguments & Aligned Layout")

        with gr.Row():
            with gr.Column():
                # 控制器
                msg_input = gr.Textbox(label="Alert Message", value="你似乎还没有创建任何培育方案。你需要先到「方案」里创建一个！")
                title_input = gr.Textbox(label="Title", value="提示")
                variant_input = gr.Dropdown(["success", "info", "warning", "error"], label="Variant", value="info")
                action_input = gr.Textbox(label="Action Button Text", value="去创建")
                update_btn = gr.Button("Update Alert")

            with gr.Column():
                # 组件实例化
                alert = Alert(
                    title="提示",
                    value="你似乎还没有创建任何培育方案。你需要先到「方案」里创建一个！",
                    variant="info",
                    action_text="去创建",
                    elem_id="my-alert"
                )
                
                # 结果显示框
                result_box = gr.Textbox(label="Event Log")

        # 1. 更新 Alert 属性
        def update_props(msg: str, title: str, variant: str, action: str) -> Alert:
            return Alert(value=msg, title=title, variant=variant, action_text=action)
        
        update_btn.click(
            update_props, 
            inputs=[msg_input, title_input, variant_input, action_input], 
            outputs=alert
        )

        # 2. 处理 Action 按钮点击
        def on_action_click(evt: gr.EventData) -> str:
            data: Dict[str, Any] = evt._data # type: ignore
            return f"Action Clicked! Variant: {data.get('variant')}, Action: {data.get('action_text')}"
        
        alert.click(on_action_click, outputs=result_box)

        # 3. 处理 Close 按钮点击
        def on_close(evt: gr.EventData) -> str:
            data: Dict[str, Any] = evt._data # type: ignore
            return f"Alert Closed. Status: {data.get('status')}"
        
        alert.change(on_close, outputs=result_box)

    demo.launch()