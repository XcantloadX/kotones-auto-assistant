# Bugsink API 使用笔记

## 认证与基础约定

- 认证头：`Authorization: Bearer $BUGSINK_TOKEN`（检查环境变量与 .env）
- **必须用 API 路径**，不要抓网页 URL：网页端 `/issues/issue/...` 走 session cookie，用 Token 访问会被 302 重定向到登录页。
- 正确基址：`https://<实例域名>/api/canonical/0/`
- Token 有 capabilities 和 scope（可限定单个 project）：缺能力返回 `403`，无效 token 返回 `401`。
- 列表接口统一 cursor 分页：响应 `{next, previous, results}`，按 `next` 的完整 URL 翻页，不要自己拼 cursor。
- 栈帧接口可用 `Accept: text/markdown` 获取适合阅读 / 喂给模型的渲染结果。

```sh
export BUGSINK_URL=https://<实例域名>
export BUGSINK_TOKEN=<token>
api() { curl -sf -H "Authorization: Bearer $BUGSINK_TOKEN" "$@"; }
```

## 典型排查流程

1. 查看 issue 详情（拿到 project、计数、解决/静音状态）：

```sh
api "$BUGSINK_URL/api/canonical/0/issues/<issue-uuid>/" | python3 -m json.tool
```

关键字段：`friendly_id`、`project`、`calculated_type` / `calculated_value`（异常类型和消息）、`digested_event_count`、`stored_event_count`、`first_seen` / `last_seen`、`is_resolved` / `is_muted`。

2. 列出该 issue 的事件，取最新一条：

```sh
api "$BUGSINK_URL/api/canonical/0/events/?issue=<issue-uuid>" | python3 -m json.tool
```

事件按时间倒序返回，第一条即最新；每条有 `id`、`event_id`、`timestamp`、`digest_order`。

3. 用事件 `id` 拉栈帧（Markdown 最直观）：

```sh
api -H "Accept: text/markdown" \
  "$BUGSINK_URL/api/canonical/0/events/<event-uuid>/stacktrace/"
```

Markdown 含：异常类型与消息、每一帧的 `文件:行号 in 函数`、源码上下文、Locals 变量。JSON 事件响应里的 `stacktrace_md` 字段也是同一份渲染。

> Locals / 栈帧可能包含凭据、路径、用户数据，外发前留意。

4. 定位到代码 → 修复 → 跑相关测试。
5. 修复完成后，**主动询问用户是否需要将 issue 标记为「下个版本解决」**（`resolve-next`），不要自行操作：

```sh
api -X POST "$BUGSINK_URL/api/canonical/0/issues/<issue-uuid>/resolve-next/"
```

## 常用 API 速查

基址：`$BUGSINK_URL/api/canonical/0`

### Issues

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/issues/?project=<id>&sort=last_seen&order=desc` | 列出问题。`project` 必填；`sort` 可选 `digest_order` / `digested_event_count` / `last_seen`；`order` 为 `asc` / `desc` |
| GET | `/issues/{id}/` | 单个问题详情 |
| DELETE | `/issues/{id}/` | 删除问题 |
| POST | `/issues/{id}/resolve/` | 标记已解决 |
| POST | `/issues/{id}/resolve-latest/` | 解决到最新版本 |
| POST | `/issues/{id}/resolve-next/` | 解决到下一个版本 |
| POST | `/issues/{id}/reopen/` | 重新打开 |
| POST | `/issues/{id}/mute/` | 永久静音 |
| POST | `/issues/{id}/unmute/` | 取消静音 |
| POST | `/issues/{id}/mute-for/` | 静音一段时间 |
| POST | `/issues/{id}/mute-until/` | 静音直到事件量达到阈值 |

`mute-for` body：`{"period_name": "day", "nr_of_periods": 3}`（静音 3 天）。

`mute-until` body 示例（`period_name` 取值 `year` / `month` / `week` / `day` / `hour` / `minute`）：

```json
{ "period_name": "day", "nr_of_periods": 1, "gte_threshold": 10 }
```

### Events

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/events/?issue=<issue-uuid>` | 某 issue 的事件列表（`issue` 必填） |
| GET | `/events/{id}/` | 完整事件 payload（含 `stacktrace_md`） |
| GET | `/events/{id}/stacktrace/` | 栈帧渲染；加 `Accept: text/markdown` 得到 Markdown |

### Comments

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/issue-comments/` | 给 issue 加评论 |

Body：

```json
{ "issue": "<issue-uuid>", "comment": "已在 vX.Y.Z 修复" }
```

### Projects / Teams / Releases

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/projects/` | 列出（可按 `?team=` 过滤）/ 创建项目 |
| GET/PATCH | `/projects/{id}/` | 查看 / 更新项目 |
| GET | `/teams/` | 列出团队 |
| GET/PATCH | `/teams/{id}/` | 查看 / 更新团队 |
| GET | `/releases/?project=<id>` | 列出 release |
| POST | `/releases/` | 创建 release（`{"project": 1, "version": "vX.Y.Z"}`） |
| GET | `/releases/{id}/` | release 详情 |

> `projects:read`、`projects:manage`、`teams:read`、`teams:manage` 需要 global token；project 级 token 连自己的 project 都列不出来，只能直接使用已知的 project id。

### Sentry 兼容接口

仅用于 SDK 上报和 debug 文件上传，日常排查用不到：

- `POST /api/{project_pk}/store/`、`/envelope/`、`/minidump/`、`/security/`：事件上报
- `/api/0/organizations/{org}/chunk-upload/`、`/artifactbundle/assemble/`、`/api/0/projects/{org}/{project}/files/difs/assemble/`：sourcemap / debug file
- `GET /api/0/`：兼容性探测

## Capabilities 对照

| 能力 | 允许的操作 |
| --- | --- |
| `issues:read` | 列出 / 查看 issue |
| `events:read` | 列出 / 查看 event、栈帧 |
| `issues:comment` | 加评论 |
| `issues:triage` | resolve / reopen / mute / unmute |
| `issues:delete` | 删除 issue |
| `releases:read` / `releases:create` | 读 / 建 release |
| `projects:read` / `projects:manage` | 读 / 建改 project（需 global token） |
| `teams:read` / `teams:manage` | 读 / 建改 team（需 global token） |
| `debug-files:upload` | 上传 sourcemap / debug file |

## 补充入口

- 网页端的 Markdown 摘要（session 登录后可用）：`/issues/issue/<issue-uuid>/md/`，加 `?download` 下载 `.md`。
- 实例自身的 OpenAPI schema：`$BUGSINK_URL/api/canonical/0/schema/`，Swagger UI：`/api/canonical/0/schema/swagger-ui/`。不同版本字段以实例 schema 为准。
