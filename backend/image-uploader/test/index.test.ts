/**
 * 上传接口测试。
 * 通过注入 mock 的限流绑定与 mock 的 Google Drive API（fetch）来验证各分支逻辑。
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { app, type Env } from "../src/index";
import { MAX_UPLOAD_BYTES } from "../src/media";

const ACCESS_TOKEN = "test-access-token";

/** 构造测试用 Env，限流绑定默认为“放行”。 */
function createMockEnv(overrides: Partial<Env> = {}): Env {
  return {
    GOOGLE_DRIVE_FOLDER_ID: "folder-123",
    GOOGLE_CLIENT_ID: "client-id",
    GOOGLE_CLIENT_SECRET: "client-secret",
    GOOGLE_REFRESH_TOKEN: "refresh-token",
    UPLOAD_RATE_LIMITER: {
      limit: vi.fn(async () => ({ success: true })),
    },
    ...overrides,
  } as Env;
}

/** mock Google 的 token 与 upload 接口，并返回 fetch 调用记录。 */
function mockDriveApi() {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url.includes("oauth2.googleapis.com/token")) {
        return new Response(JSON.stringify({ access_token: ACCESS_TOKEN }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("upload/drive/v3/files")) {
        return new Response(JSON.stringify({ id: "drive-file-id" }), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** 构造一个图片类型的请求体。 */
function imageBody(): Uint8Array {
  return new TextEncoder().encode("fake-png-bytes");
}

describe("GET /health", () => {
  it("返回 ok", async () => {
    const env = createMockEnv();
    const res = await app.request("http://localhost/health", {}, env);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});

describe("POST /upload 校验", () => {
  let env: Env;

  beforeEach(() => {
    env = createMockEnv();
  });

  it("非图片 Content-Type 返回 415", async () => {
    const res = await app.request(
      "http://localhost/upload",
      {
        method: "POST",
        headers: { "content-type": "text/plain" },
        body: new TextEncoder().encode("hello"),
      },
      env,
    );
    expect(res.status).toBe(415);
  });

  it("Content-Length 超过 3MB 返回 413", async () => {
    const body = new Uint8Array(MAX_UPLOAD_BYTES + 1);
    const req = new Request("http://localhost/upload", {
      method: "POST",
      headers: { "content-type": "image/png" },
      body,
    });
    const res = await app.request(req, {}, env);
    expect(res.status).toBe(413);
  });

  it("实际字节数超过 3MB（流式请求体）返回 413", async () => {
    const chunk = new Uint8Array(1024 * 1024);
    let sent = 0;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (sent >= MAX_UPLOAD_BYTES + 1) {
          controller.close();
          return;
        }
        const n = Math.min(chunk.length, MAX_UPLOAD_BYTES + 1 - sent);
        controller.enqueue(chunk.subarray(0, n));
        sent += n;
      },
    });
    const res = await app.request(
      "http://localhost/upload",
      // Node 的 fetch 要求流式请求体携带 duplex: "half"（Worker 运行时无此限制）
      { method: "POST", headers: { "content-type": "image/png" }, body: stream, duplex: "half" } as RequestInit,
      env,
    );
    expect(res.status).toBe(413);
  });

  it("空请求体返回 400", async () => {
    const res = await app.request(
      "http://localhost/upload",
      { method: "POST", headers: { "content-type": "image/png" } },
      env,
    );
    expect(res.status).toBe(400);
  });

  it("触发 IP 频率限制返回 429", async () => {
    const limitedEnv = createMockEnv({
      UPLOAD_RATE_LIMITER: {
        limit: vi.fn(async () => ({ success: false })),
      },
    });
    const res = await app.request(
      "http://localhost/upload",
      {
        method: "POST",
        headers: { "content-type": "image/png" },
        body: imageBody(),
      },
      limitedEnv,
    );
    expect(res.status).toBe(429);
  });
});

describe("POST /upload 成功路径", () => {
  it("上传成功并返回随机 UUID", async () => {
    const fetchMock = mockDriveApi();
    const env = createMockEnv();

    const res = await app.request(
      "http://localhost/upload",
      {
        method: "POST",
        headers: { "content-type": "image/png" },
        body: imageBody(),
      },
      env,
    );

    expect(res.status).toBe(201);
    const data = (await res.json()) as { id: string };
    // 必须是合法的 UUID v4
    expect(data.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );

    // 应调用 token 接口与 upload 接口各一次
    const calls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(calls.some((u) => u.includes("oauth2.googleapis.com/token"))).toBe(true);
    const uploadCall = fetchMock.mock.calls.find(([input]) =>
      String(input).includes("upload/drive/v3/files"),
    )!;
    // 上传请求需携带 Bearer 令牌
    expect((uploadCall[1] as RequestInit).headers).toMatchObject({
      Authorization: `Bearer ${ACCESS_TOKEN}`,
    });
  });

  it("Google Drive 上传失败返回 502", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("oauth2.googleapis.com/token")) {
          return new Response(JSON.stringify({ access_token: ACCESS_TOKEN }), { status: 200 });
        }
        return new Response("server error", { status: 500 });
      }),
    );
    const env = createMockEnv();

    const res = await app.request(
      "http://localhost/upload",
      {
        method: "POST",
        headers: { "content-type": "image/jpeg" },
        body: imageBody(),
      },
      env,
    );
    expect(res.status).toBe(502);
  });
});
