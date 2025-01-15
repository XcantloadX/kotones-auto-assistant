/**
 * 解析文本中的图片，将 [img]...[/img] 替换为 <img src="...">
 * @param {string} text 文本
 * @param {(key: string) => string} img2urlCallback 图片键到 URL 的回调函数
 * @returns {string} 解析后的文本
 */
export function parseImages(
    text,
    img2urlCallback = (k) => '/api/read_memory?key=' + k
) {
    const regex = /\[img\](.*?)\[\/img\]/g;
    return text.replace(regex, (match, p1) => {
        return `<img src="${img2urlCallback(p1)}" alt="image">`;
    });
}