/**
 * Vite 构建配置。
 *
 * - `cloudflare()`：Cloudflare 官方 Vite 插件，接管 Worker 的 dev/build/deploy，
 *   构建产物（dist/）即最终部署的 bundle，供 Sentry 注入 debug ID。
 * - `sentryVitePlugin()`：在构建时向 bundle/sourcemap 注入 debug ID，
 *   并自动把 sourcemap 上传到 Bugsink（Sentry 兼容，按 debug ID 匹配源码）。
 *
 * 需要 .env 提供：
 *   BUGSINK_URL=        Bugsink 公网地址，如 https://bugsink.1ichika.de
 *   BUGSINK_AUTH_TOKEN= Bugsink 认证令牌
 */
import { defineConfig, loadEnv, type Plugin } from "vite";
import { cloudflare } from "@cloudflare/vite-plugin";
import { sentryVitePlugin } from "@sentry/vite-plugin";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // @sentry/cli 子进程通过 SENTRY_URL / SENTRY_AUTH_TOKEN 环境变量解析连接地址与鉴权。
  // 显式写入 process.env，确保 CLI 拿到正确值（插件内部透传可能被包体积混淆破坏）。
  if (env.BUGSINK_URL) process.env.SENTRY_URL = env.BUGSINK_URL;
  if (env.BUGSINK_AUTH_TOKEN) process.env.SENTRY_AUTH_TOKEN = env.BUGSINK_AUTH_TOKEN;

  const plugins: Plugin[] = [...cloudflare()];

  // 仅在配置了 Bugsink 凭据时才启用 sourcemap 注入/上传，避免本地无 .env 时构建失败
  if (env.BUGSINK_URL && env.BUGSINK_AUTH_TOKEN) {
    plugins.push(
      ...sentryVitePlugin({
        // Bugsink 忽略 org/project，仅按 debug ID 匹配，占位即可
        org: "bugsinkhasnoorgs",
        project: "kaa-image-upload",
        url: env.BUGSINK_URL,
        authToken: env.BUGSINK_AUTH_TOKEN,
        release: {
          name: env.SENTRY_RELEASE ?? "image-uploader@1.0.0",
          create: false,
          finalize: false,
          inject: true,
        },
        // 注意：不要配置 filesToDeleteAfterUpload —— wrangler deploy 需要 dist 中的 .map 存在，
        // 且 Worker 的 dist 产物不会对外托管，保留 map 无泄露风险。
      }),
    );
  } else {
    console.warn("[sentry-vite-plugin] 未配置 BUGSINK_URL/BUGSINK_AUTH_TOKEN，跳过 sourcemap 上传");
  }

  return {
    plugins,
    build: {
      sourcemap: true,
    },
  };
});
