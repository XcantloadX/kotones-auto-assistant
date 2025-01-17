/**
 * 渲染文本，将 [img]...[/img] 替换为 <img src="...">
 * @param {string} text 文本
 * @param {(key: string) => string} img2urlCallback 图片键到 URL 的回调函数
 * @returns {string} 渲染后的文本
 */
export function render(
    text,
    img2urlCallback = (k) => '/api/read_memory?key=' + k
) {
    // 解析 [img] 标签
    text = text.replace(/\[img\](.*?)\[\/img\]/g, (match, p1) => {
        return `<img src="${img2urlCallback(p1)}" alt="image">`;
    });

    return text;
}

/**
 * 加载组件
 * @param {string} componentPath 组件路径
 */
export function loadComponent(componentPath) {
    fetch(componentPath)
        .then(response => response.text())
        .then(html => {
            const div = document.createElement('div');
            const frag = document.createRange().createContextualFragment(html);
            document.body.appendChild(frag);

        })
        .catch(error => {
            console.error(`加载组件 ${componentName} 失败:`, error);
        });
}
