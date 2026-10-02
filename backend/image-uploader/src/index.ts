/**
 * Cloudflare Worker 入口：媒体上传服务（图片 + 视频）。
 *
 * 流程：
 *  1. IP 频率限制（每分钟每 IP 最多 5 次，图片视频共用）
 *  2. 校验 Content-Type 必须是受支持的图片或视频类型
 *  3. 校验文件大小 < 3 MiB（图片视频统一；同时检查
 *     Content-Length 与实际读取的字节数）
 *  4. 生成随机 UUID 作为文件 ID
 *  5. 转发上传到 Google Drive 指定文件夹
 *  6. 返回 { "id": "<uuid>" }
 */
import { Hono } from "hono";
import * as Sentry from "@sentry/cloudflare";
import { GoogleDriveClient } from "./google-drive";
import {
  MAX_UPLOAD_BYTES,
  getFileExtension,
  isSupportedContentType,
} from "./media";

/** Worker 环境变量与绑定（GOOGLE_DRIVE_FOLDER_ID / UPLOAD_RATE_LIMITER 由 wrangler types 生成）。 */
export interface Env extends CloudflareBindings {
  /** OAuth2 客户端 ID */
  GOOGLE_CLIENT_ID: string;
  /** OAuth2 客户端密钥 */
  GOOGLE_CLIENT_SECRET: string;
  /** 用户授权后获取的刷新令牌 */
  GOOGLE_REFRESH_TOKEN: string;
  /** Bugsink（Sentry 兼容）DSN，例：http://<public_key>@<host>:8000/<project_id> */
  BUGSINK_DSN: string;
}

export const app = new Hono<{ Bindings: Env }>();

/** 健康检查。 */
app.get("/health", (c) => c.json({ status: "ok" }));

/** 媒体上传接口（图片/视频）。 */
app.post("/upload", async (c) => {
  // 1. IP 频率限制：每分钟每 IP 最多 5 次
  const ip = c.req.header("cf-connecting-ip") ?? "unknown";
  const { success } = await c.env.UPLOAD_RATE_LIMITER.limit({ key: ip });
  if (!success) {
    return c.json({ error: "Too many requests, please try again later." }, 429);
  }

  // 2. 仅允许图片与视频
  const contentType = c.req.header("content-type") ?? "";
  if (!isSupportedContentType(contentType)) {
    return c.json({ error: "Only image and video uploads are allowed." }, 415);
  }

  // 3a. 依据 Content-Length 快速拒绝超大文件（图片视频统一 3MB）
  const contentLength = Number(c.req.header("content-length") ?? "0");
  if (contentLength > MAX_UPLOAD_BYTES) {
    return c.json({ error: "File size exceeds the 3MB limit." }, 413);
  }

  // 3b. 读取请求体，并核对实际字节数（防止伪造 Content-Length）
  const body = await c.req.arrayBuffer();
  if (body.byteLength === 0) {
    return c.json({ error: "Empty request body." }, 400);
  }
  if (body.byteLength > MAX_UPLOAD_BYTES) {
    return c.json({ error: "File size exceeds the 3MB limit." }, 413);
  }

  // 4. 生成随机 UUID 作为文件 ID，Drive 中的文件名也使用该 ID
  const mediaId = crypto.randomUUID();
  const extension = getFileExtension(contentType);

  // 5. 转发上传到 Google Drive
  const drive = new GoogleDriveClient(c.env);
  try {
    await drive.uploadFile({
      name: `${mediaId}.${extension}`,
      folderId: c.env.GOOGLE_DRIVE_FOLDER_ID,
      contentType,
      content: body,
    });
  } catch (err) {
    console.error("Failed to upload to Google Drive", err);
    // 上报到 Bugsink，附带文件 ID 便于排查
    Sentry.withScope((scope) => {
      scope.setTag("media_id", mediaId);
      scope.setLevel("error");
      Sentry.captureException(err);
    });
    return c.json({ error: "Failed to store file." }, 502);
  }

  // 6. 返回文件 ID
  return c.json({ id: mediaId }, 201);
});

// 用 withSentry 包装整个 Hono app：自动上报未捕获异常并采集 trace。
// BUGSINK_DSN 未配置时 SDK 自动降级为空操作，不影响正常请求。
export default Sentry.withSentry(
  (env: Env) => ({
    dsn: env.BUGSINK_DSN,
    tracesSampleRate: 0.1,
  }),
  {
    fetch: app.fetch.bind(app),
  } satisfies ExportedHandler<Env>,
);
