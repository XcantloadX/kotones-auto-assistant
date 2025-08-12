import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig, loadEnv } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [tailwindcss(), reactRouter(), tsconfigPaths()],
    server: {
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true,
        },
      },
    },
  };
});
