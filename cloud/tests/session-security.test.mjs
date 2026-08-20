import assert from "node:assert/strict";
import test from "node:test";

import { SessionVault, SessionVaultError } from "../dist/session-vault.js";
import { WorkspaceCoordinator } from "../dist/workspace-coordinator.js";
import { assertRequestOrigin, securityHeaders, sessionCookie } from "../dist/security.js";
import { MemoryState, keyBase64 } from "./helpers.mjs";

test("SessionVault stores only AES-GCM ciphertext and destroys expired leases", async () => {
  let now = Date.parse("2026-08-19T12:00:00Z");
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64() }, { now: () => now });
  const secret = "model-token-must-never-persist-in-plaintext";
  const receipt = await vault.leaseSecret({ workspace_id: "ws_a", session_id: "s_a", purpose: "model_endpoint", secret });

  assert.equal(receipt.schema, "quillframe_secret_lease_receipt_v1");
  assert.equal(receipt.authority, false);
  assert.doesNotMatch(JSON.stringify([...state.storage.values]), new RegExp(secret));
  assert.equal(await vault.readSecret(receipt.lease_id, { workspace_id: "ws_a", session_id: "s_a" }), secret);

  now += 31 * 60 * 1000;
  await assert.rejects(() => vault.readSecret(receipt.lease_id, { workspace_id: "ws_a", session_id: "s_a" }), (error) => error instanceof SessionVaultError && error.code === "secret_lease_expired");
  assert.equal(state.storage.values.has(`lease:${receipt.lease_id}`), false);
});

test("SessionVault absolute expiry, session destruction, and full deletion are deterministic", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const vault = new SessionVault(state, { SESSION_VAULT_KEY_B64: keyBase64(8) }, { now: () => now });
  const first = await vault.leaseSecret({ workspace_id: "ws", session_id: "session", purpose: "workos_refresh", secret: "refresh-a" });
  const second = await vault.leaseSecret({ workspace_id: "ws", session_id: "session", purpose: "model_endpoint", secret: "token-b" });
  await vault.destroySession({ workspace_id: "ws", session_id: "session" });
  await assert.rejects(() => vault.readSecret(first.lease_id, { workspace_id: "ws", session_id: "session" }));
  await assert.rejects(() => vault.readSecret(second.lease_id, { workspace_id: "ws", session_id: "session" }));
  await vault.leaseSecret({ workspace_id: "ws", session_id: "other", purpose: "model_endpoint", secret: "token-c" });
  await vault.destroyAll();
  assert.equal(state.storage.values.size, 0);
  assert.equal(state.storage.alarm, undefined);
});

test("WorkspaceCoordinator issues opaque hashed sessions and enforces idle/absolute expiry", async () => {
  let now = 1_800_000_000_000;
  const state = new MemoryState();
  const coordinator = new WorkspaceCoordinator(state, {}, { now: () => now });
  const created = await coordinator.createSession({ identity_id: "user_123", workos_session_id: "session_123" });
  assert.match(created.cookie_token, /^[a-f0-9]{24}\.[A-Za-z0-9_-]{43}$/);
  assert.doesNotMatch(JSON.stringify([...state.storage.values]), new RegExp(created.cookie_token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  const active = await coordinator.validateSession(created.cookie_token, created.csrf_token);
  assert.equal(active.workspace_id, created.workspace_id);
  assert.equal(active.authority, false);
  await assert.rejects(() => coordinator.validateSession(created.cookie_token, "wrong"));

  now += 31 * 60 * 1000;
  await assert.rejects(() => coordinator.validateSession(created.cookie_token, created.csrf_token), (error) => error.code === "session_expired");
});

test("cookies, origin validation, and security headers use the hosted BFF boundary", () => {
  const cookie = sessionCookie("opaque", 60);
  assert.match(cookie, /^__Host-qf_session=/);
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /Secure/);
  assert.match(cookie, /SameSite=Lax/);
  assert.doesNotMatch(cookie, /Domain=/i);
  assert.equal(assertRequestOrigin(new Request("https://studio.example/api", { method: "POST", headers: { Origin: "https://studio.example" } }), "https://studio.example"), undefined);
  assert.throws(() => assertRequestOrigin(new Request("https://studio.example/api", { method: "POST", headers: { Origin: "https://evil.example" } }), "https://studio.example"));
  const headers = securityHeaders();
  assert.equal(headers.get("x-content-type-options"), "nosniff");
  assert.match(headers.get("content-security-policy"), /default-src 'none'/);
});
