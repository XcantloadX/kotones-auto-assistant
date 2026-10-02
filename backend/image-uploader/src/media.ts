/**
 * 媒体类型与文件大小相关的校验辅助工具（图片 + 视频）。
 */

/** 图片与视频共用的上传大小上限：小于 3 MiB */
export const MAX_UPLOAD_BYTES = 3 * 1024 * 1024;

/**
 * 支持的图片 MIME 类型 → 文件扩展名映射。
 * 不在映射表中的类型一律拒绝，确保只能上传图片。
 */
const IMAGE_EXTENSIONS: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/gif": "gif",
  "image/webp": "webp",
  "image/avif": "avif",
  "image/apng": "apng",
  "image/bmp": "bmp",
  "image/svg+xml": "svg",
  "image/tiff": "tif",
  "image/x-icon": "ico",
  "image/heic": "heic",
  "image/heif": "heif",
};

/** 从完整的 Content-Type 头（可能含 charset 等参数）中提取 MIME 类型。 */
function parseMime(contentType: string): string {
  return contentType.split(";")[0]?.trim().toLowerCase() ?? "";
}

/** 判断 Content-Type 是否为受支持的图片类型。 */
export function isImageContentType(contentType: string): boolean {
  return parseMime(contentType) in IMAGE_EXTENSIONS;
}

/**
 * 支持的视频 MIME 类型 → 文件扩展名映射。
 * 仅开放崩溃录屏实际产生的 MP4，其余一律拒绝。
 */
const VIDEO_EXTENSIONS: Record<string, string> = {
  "video/mp4": "mp4",
};

/** 判断 Content-Type 是否为受支持的视频类型。 */
export function isVideoContentType(contentType: string): boolean {
  return parseMime(contentType) in VIDEO_EXTENSIONS;
}

/** 判断 Content-Type 是否为受支持的上传类型（图片或视频）。 */
export function isSupportedContentType(contentType: string): boolean {
  return isImageContentType(contentType) || isVideoContentType(contentType);
}

/** 根据 Content-Type 返回对应文件扩展名（不含点）。 */
export function getFileExtension(contentType: string): string {
  const mime = parseMime(contentType);
  return IMAGE_EXTENSIONS[mime] ?? VIDEO_EXTENSIONS[mime] ?? "bin";
}
