# Quillframe Studio · Hosted Web surface

状态：Cloud Worker 实现与确定性安全测试已在本地完成；真实 WorkOS/Cloudflare 部署仍为 `awaiting_external`。

## Topology

```text
Hosted SolidJS Studio
→ Cloudflare Worker BFF
   ├─ WorkOS AuthKit
   ├─ WorkspaceCoordinator Durable Object
   ├─ encrypted SessionVault Durable Object
   ├─ encrypted R2 Project bundles
   └─ Python Core Container
→ Host Bridge v11
```

浏览器只拥有 presentation 与显式 user action，不会收到 WorkOS access/refresh token、模型 credential、R2 encryption key 或直接 Durable Object binding。

## Authentication 与 session

Authorization 使用 state、PKCE、single-use auth transaction 与精确 callback URI。BFF 签发带 `HttpOnly`、`Secure`、`SameSite=Lax` 的 opaque `__Host-` cookie；所有改变状态的请求还必须通过 same-origin 与 double-submit CSRF 验证。Session 在 idle 30 分钟或 absolute 8 小时后过期。Logout、显式 session end 与 project deletion 会销毁服务端 session 和 leased secret。

## Project 与 BYOK 边界

Cloud upload 必须由用户显式发起，本地 launch 或 sign-in 都不会触发上传。R2 只保存 encrypted bundle；SessionVault 只保存 AES-GCM ciphertext 与有界 lease。模型 token 不进入 Project bundle、log、receipt、analytics 或 semantic context。Hosted custom endpoint 必须是 public HTTPS，并通过 DNS、redirect、private range、rebinding 与 destination-bound probe 检查。

## Deployment acceptance

Production status 需要真实账号证据：custom auth domain、email/GitHub/Google/passkey、callback/logout、durable restart、encrypted upload/restore/delete、Core Container operation、endpoint validation 与 log redaction。在这些 live check 完成前，不能把实现描述为已部署或 production-ready。
