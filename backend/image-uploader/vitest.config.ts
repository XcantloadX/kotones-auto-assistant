/**
 * Vitest 独立配置。
 * 避免加载 vite.config.ts（其中含 @cloudflare/vite-plugin，与 vitest 的 dev 模式冲突）。
 */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
  },
});
