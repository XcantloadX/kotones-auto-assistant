/**
 * 一次性工具：通过 OAuth2 授权码换取长期有效的刷新令牌。
 *
 * 前置条件：在 Google Cloud Console 创建「OAuth 客户端 ID」（类型：Web 应用），
 * 并把授权回调地址 http://127.0.0.1:8788/oauth2callback 加入「已获授权的重定向 URI」。
 *
 * 用法（优先级：命令行参数 > 环境变量 > .dev.vars）：
 *   node scripts/get-refresh-token.mjs <client_id> <client_secret> [port]
 * 或先在 .dev.vars 中填好 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 后直接运行：
 *   npm run get-refresh-token
 */
import http from "node:http";
import { exec } from "node:child_process";
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";

/** 读取项目根目录下的 .dev.vars（KEY=value 格式，兼容带引号的值）。 */
function loadDotDevVars() {
  try {
    const text = readFileSync(new URL("../.dev.vars", import.meta.url), "utf8");
    const vars = {};
    for (const line of text.split(/\r?\n/)) {
      const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
      if (!match) continue;
      let value = match[2].trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      vars[match[1]] = value;
    }
    return vars;
  } catch {
    return {};
  }
}

const dotVars = loadDotDevVars();
const PORT = Number(process.argv[4] ?? 8788);
const CLIENT_ID = process.argv[2] ?? process.env.GOOGLE_CLIENT_ID ?? dotVars.GOOGLE_CLIENT_ID;
const CLIENT_SECRET =
  process.argv[3] ?? process.env.GOOGLE_CLIENT_SECRET ?? dotVars.GOOGLE_CLIENT_SECRET;

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error(
    "未找到 GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET。\n" +
      "请在 .dev.vars 中填入这两个值后重试，或通过命令行参数传入：\n" +
      "  npm run get-refresh-token -- <client_id> <client_secret>",
  );
  process.exit(1);
}

const REDIRECT_URI = `http://127.0.0.1:${PORT}/oauth2callback`;
const SCOPE = "https://www.googleapis.com/auth/drive.file";
const STATE = randomBytes(16).toString("hex");

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${PORT}`);
  if (url.pathname !== "/oauth2callback") {
    res.writeHead(404).end("Not found");
    return;
  }
  const state = url.searchParams.get("state");
  const code = url.searchParams.get("code");
  const error = url.searchParams.get("error");
  if (state !== STATE) {
    res.writeHead(400).end("state 不匹配，请重新运行");
    return;
  }
  if (error || !code) {
    res.writeHead(400).end(`授权失败: ${error ?? "missing code"}`);
    return;
  }

  try {
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        code,
        redirect_uri: REDIRECT_URI,
        grant_type: "authorization_code",
      }),
    });
    const data = await tokenRes.json();
    if (!tokenRes.ok || !data.refresh_token) {
      throw new Error(`换取令牌失败: ${JSON.stringify(data)}`);
    }
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end("<h3>授权成功，可以关闭此窗口。</h3>");
    console.log("\n=== 刷新令牌（填入 .dev.vars 的 GOOGLE_REFRESH_TOKEN）===");
    console.log(data.refresh_token);
    console.log("========================================================");
    server.close();
  } catch (err) {
    console.error(err);
    res.writeHead(500, { "Content-Type": "text/html; charset=utf-8" }).end("内部错误，请查看终端日志");
    server.close();
  }
});

server.listen(PORT, "127.0.0.1", () => {
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", CLIENT_ID);
  authUrl.searchParams.set("redirect_uri", REDIRECT_URI);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", SCOPE);
  authUrl.searchParams.set("access_type", "offline");
  authUrl.searchParams.set("prompt", "consent");
  authUrl.searchParams.set("state", STATE);
  console.log(`请在浏览器中完成授权：\n${authUrl}\n`);
  const openCmd =
    process.platform === "win32"
      ? `start "" "${authUrl}"`
      : process.platform === "darwin"
        ? `open "${authUrl}"`
        : `xdg-open "${authUrl}"`;
  exec(openCmd);
});
