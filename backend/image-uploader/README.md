# 图片上传服务（Cloudflare Worker）

部署在 Cloudflare Workers 上的图片上传接口：

1. 每个 IP 每分钟最多 **5** 次请求（IP 频率限制）
2. 仅允许上传图片（按 `Content-Type` 校验）
3. 单个文件必须 **小于 3 MiB**
4. 每张图片分配一个随机 **UUID** 作为 ID
5. 图片转发上传到 **Google Drive 指定文件夹**，文件名即 `{uuid}.{ext}`
6. 调用方收到 `201 { "id": "<uuid>" }`

## 技术栈

- [Hono](https://hono.dev) — Web 框架
- [Vite](https://vite.dev) + [@cloudflare/vite-plugin](https://developers.cloudflare.com/workers/vite-plugin/) — 构建/开发/部署
- [@sentry/cloudflare](https://www.npmjs.com/package/@sentry/cloudflare) — 错误上报 SDK
- [@sentry/vite-plugin](https://www.npmjs.com/package/@sentry/vite-plugin) — 构建时注入 debug ID 并上传 sourcemap
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) — 部署 CLI
- [Vitest](https://vitest.dev) — 单元测试

## 目录结构

```
backend/image-uploader/
├── src/
│   ├── index.ts           # Worker 入口：路由、校验、限流、转发
│   ├── google-drive.ts    # Google Drive 鉴权（用户 OAuth2）+ multipart 上传
│   └── media.ts           # MIME/扩展名映射、大小限制
├── scripts/
│   └── get-refresh-token.mjs  # 一次性工具：换取用户刷新令牌
├── test/index.test.ts     # 接口测试
├── vite.config.ts         # Vite 配置（cloudflare + sentryVitePlugin）
├── wrangler.jsonc         # Worker 配置（vars + 限流绑定）
├── vitest.config.ts       # 测试配置（避免加载 cloudflare 插件）
└── .env.example           # 构建期环境变量模板（Bugsink 上传 sourcemap 用）
```

## 开发 / 构建 / 部署

```bash
npm run dev        # 本地开发（vite dev，等价于原 wrangler dev，端口 8787）
npm run build      # 构建到 dist/（含 sourcemap + debug ID 注入 + 上传 Bugsink）
npm run deploy     # = npm run build && wrangler deploy
```

## 一、Google Cloud 准备（用户 OAuth2）

> 说明：服务账号自 2025-04 起无存储配额，无法上传到个人云盘；本服务改用**用户 OAuth2**，
> 上传的文件归属你自己、占用你自己的云盘配额，个人免费 Gmail 账号即可。

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 创建项目，启用 **Google Drive API**。
2. 左侧菜单 **API 和服务** → **凭据** → **创建凭据** → **OAuth 客户端 ID**：
   - 应用类型：**Web 应用**
   - 已获授权的重定向 URI：`http://127.0.0.1:8788/oauth2callback`
   - 创建后复制 **客户端 ID** 和 **客户端密钥**
3. **OAuth 同意屏幕**：将你自己的 Google 账号添加为测试用户（或发布应用），否则授权时报错。
4. 获取**刷新令牌**（只需一次，长期有效）：
   ```bash
   # 方式一：先在 .dev.vars 填好 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET，直接运行
   npm run get-refresh-token
   # 方式二：命令行传入
   npm run get-refresh-token -- <client_id> <client_secret>
   ```
   浏览器会打开 Google 授权页，选择你的账号并同意，终端即打印 `GOOGLE_REFRESH_TOKEN`。
5. 在 Google Drive 中创建目标文件夹，从地址栏复制文件夹 ID：
   ```
   https://drive.google.com/drive/folders/<FOLDER_ID>
   ```
   `GOOGLE_DRIVE_FOLDER_ID` 即 `<FOLDER_ID>`（无需分享给任何人）。

> 使用最小权限 scope `drive.file`：本应用仅能访问它自己创建的文件。

## 二、本地开发

```bash
npm install
Copy-Item .dev.vars.example .dev.vars   # Windows PowerShell，填入真实值
Copy-Item .env.example .env             # 填入 BUGSINK_URL / BUGSINK_AUTH_TOKEN
npm run dev
```

本地启动后：

```bash
curl -X POST http://localhost:8787/upload \
  -H "Content-Type: image/png" \
  --data-binary @./test.png
# => {"id":"3f2e8b1a-...."}
```

## 三、部署到 Cloudflare

1. 登录并创建 Worker：
   ```bash
   npx wrangler login
   npx wrangler deploy
   ```
2. 配置全部 **密钥**（每次部署后只需设置一次）：
   ```bash
   npx wrangler secret put GOOGLE_CLIENT_ID
   npx wrangler secret put GOOGLE_CLIENT_SECRET
   npx wrangler secret put GOOGLE_REFRESH_TOKEN
   npx wrangler secret put GOOGLE_DRIVE_FOLDER_ID
   npx wrangler secret put BUGSINK_DSN
   ```
3. 本地开发时这些值统一放 `.dev.vars`（wrangler 会自动加载并覆盖同名变量）。

> 限流绑定 `namespace_id` 是自定义的整数标识（当前为 `1001`），在你的账号内需唯一；多个 Worker 共用同一 `namespace_id` 会共享计数器。

## 四、API

### `POST /upload`

请求：
- `Content-Type` 必须为受支持的图片类型（`image/png`、`image/jpeg`、`image/webp`、`image/gif` 等）
- Body 为图片二进制，大小 < 3 MiB

响应：
- `201` → `{ "id": "<uuid>" }`
- `400` → 请求体为空
- `413` → 文件超过 3 MiB
- `415` → 非图片类型
- `429` → 超过 IP 频率限制（每分钟 5 次）
- `502` → Google Drive 转发失败

### `GET /health`

- `200` → `{ "status": "ok" }`

## 五、错误上报（Bugsink）

通过 [Sentry Cloudflare SDK](https://www.npmjs.com/package/@sentry/cloudflare) 上报异常到
[Sentry 兼容的](https://www.bugsink.com/sentry-sdk-compatible/) Bugsink：

- `BUGSINK_DSN` 环境变量（`wrangler secret` / `.dev.vars`）配置 DSN
- 异常（如 Google Drive 上传失败）自动捕获，并附带 `image_id` tag 便于定位
- `tracesSampleRate: 0.1` 采集 10% 请求 trace
- 需要 `compatibility_flags = ["nodejs_compat"]`（已在 `wrangler.jsonc` 中）

### Sourcemap（trace 显示原始源码）

构建时 `@sentry/vite-plugin` 向 bundle 注入 debug ID 并自动把 sourcemap 上传到 Bugsink
（按 debug ID 匹配，无需配置 release）。上传需要 `.env` 提供：

- `BUGSINK_URL`（如 `https://bugsink.1ichika.de`）
- `BUGSINK_AUTH_TOKEN`

> 前提：Bugsink 服务端 `BASE_URL` 必须配置为公网地址（如 `https://bugsink.1ichika.de`）。
> 若仍是默认值 `http://localhost:8000`，sentry-cli 会被引导去连 localhost 导致上传失败
> （错误事件上报不受影响，只有 sourcemap 上传依赖 `BASE_URL`）。

> 注意：DSN 中的 host 必须填**公网可访问**的 Bugsink 地址（如 `https://bugsink.1ichika.de/`），
> 部署到 Cloudflare 后 `localhost` 指向的就不是你的本机了。

## 六、质量检查

```bash
npm run typecheck   # TypeScript 类型检查
npm test            # 运行单元测试
```
