/**
 * Google Drive 集成：使用用户 OAuth2（授权码 → 刷新令牌 → 访问令牌）鉴权，
 * 将文件以 multipart/related 形式上传到指定文件夹。
 *
 * 为什么不用服务账号：自 2025-04 起 Google 新建的服务账号无存储配额，
 * 无法向个人云盘（My Drive）上传文件，只能使用用户 OAuth2 或共享云盘。
 * 用户 OAuth2 上传的文件归属用户本人，占用用户自己的云盘配额。
 */

const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files";
/** drive.file：仅访问本应用创建/被共享给本应用的文件，最小权限。 */
const DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file";

/** Google Drive 所需的环境变量。 */
export interface DriveEnv {
  /** OAuth2 客户端 ID（Google Cloud Console → 凭据 → OAuth 客户端 ID） */
  GOOGLE_CLIENT_ID: string;
  /** OAuth2 客户端密钥 */
  GOOGLE_CLIENT_SECRET: string;
  /** 用户授权后获取的刷新令牌（长期有效，见 scripts/get-refresh-token.mjs） */
  GOOGLE_REFRESH_TOKEN: string;
}

/** 上传文件参数。 */
export interface UploadOptions {
  /** 上传后在 Drive 中的文件名（含扩展名） */
  name: string;
  /** 目标文件夹 ID */
  folderId: string;
  /** 图片 MIME 类型 */
  contentType: string;
  /** 图片二进制内容 */
  content: ArrayBuffer;
}

/** 封装 Google Drive 上传的客户端，每次请求均重新换取访问令牌。 */
export class GoogleDriveClient {
  constructor(private readonly env: DriveEnv) {}

  /**
   * 使用刷新令牌换取访问令牌。
   * 返回的 access_token 约 1 小时有效，刷新令牌本身长期有效。
   */
  private async getAccessToken(): Promise<string> {
    const response = await fetch(GOOGLE_TOKEN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: this.env.GOOGLE_CLIENT_ID,
        client_secret: this.env.GOOGLE_CLIENT_SECRET,
        refresh_token: this.env.GOOGLE_REFRESH_TOKEN,
        grant_type: "refresh_token",
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Google token request failed: ${response.status} ${text}`);
    }

    const data = (await response.json()) as { access_token?: string };
    if (!data.access_token) {
      throw new Error("Google token response missing access_token");
    }
    return data.access_token;
  }

  /** 将图片上传到指定文件夹（multipart/related：JSON 元数据 + 二进制内容）。 */
  async uploadFile(options: UploadOptions): Promise<void> {
    const accessToken = await this.getAccessToken();

    const metadata = JSON.stringify({
      name: options.name,
      parents: [options.folderId],
    });

    const boundary = `ksaa-${crypto.randomUUID()}`;
    const crlf = "\r\n";
    const body = new Blob([
      `--${boundary}${crlf}`,
      `Content-Type: application/json; charset=UTF-8${crlf}${crlf}`,
      metadata,
      `${crlf}--${boundary}${crlf}`,
      `Content-Type: ${options.contentType}${crlf}${crlf}`,
      options.content,
      `${crlf}--${boundary}--${crlf}`,
    ]);

    const url = `${GOOGLE_UPLOAD_URL}?uploadType=multipart&fields=id,name,size`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": `multipart/related; boundary=${boundary}`,
      },
      body,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Google Drive upload failed: ${response.status} ${text}`);
    }
  }
}
