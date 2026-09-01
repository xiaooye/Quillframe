import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import {
  canonicalBridgeBody,
  canonicalJsonBytes,
  canonicalJson,
  deriveProofProjectId,
  signCoreProof,
  verifyCoreProof,
  CoreProofError,
  HOSTED_CORPUS_OPERATIONS,
  HOSTED_USER_TASTE_OPERATIONS,
  PROJECT_REQUIRED_OPERATIONS,
  PROJECT_NULL_OPERATIONS,
} from "../dist/core-provenance.js";

const key = new Uint8Array(32).fill(7);
const baseRequest = {
  schema: "quillframe_host_bridge_request_v11",
  bridge_version: "11",
  request_id: "request_1",
  operation: "project.open",
  surface: "hosted_web",
  args: { project_id: "project_1" },
  authority: false,
};

function claims(bodySha256, overrides = {}) {
  return {
    schema: "quillframe_core_proof_v1",
    key_id: "current",
    method: "POST",
    path: "/bridge",
    body_sha256: bodySha256,
    workspace_id: "workspace_1",
    session_id: "session_1",
    project_id: "project_1",
    scope: "novel",
    issued_at: 1_800_000_000_000,
    expires_at: 1_800_000_030_000,
    nonce: "nonce_1",
    ...overrides,
  };
}

test("canonicalBridgeBody rejects duplicate keys and non-canonical bytes", () => {
  assert.throws(() => canonicalBridgeBody('{"a":1,"a":2}'), CoreProofError);
  assert.throws(() => canonicalBridgeBody('{ "a": 1 }'), CoreProofError);
  assert.throws(() => canonicalBridgeBody('{"é":1}'), CoreProofError);
  assert.throws(() => canonicalJson({ value: Number.NaN }), CoreProofError);
  assert.throws(() => canonicalJson({ "é": 1 }), CoreProofError);
  assert.throws(() => canonicalJson({ "中文": 1 }), CoreProofError);
  const body = canonicalJsonBytes({ b: 2, a: 1 });
  assert.deepEqual(canonicalBridgeBody(body), { bytes: body, value: { a: 1, b: 2 } });
});

test("canonical JSON preserves lexicographic integer keys and special object keys", () => {
  const value = JSON.parse('{"2":"two","10":"ten","nested":{"__proto__":{"2":2,"10":10},"constructor":"text"}}');
  const expected = '{"10":"ten","2":"two","nested":{"__proto__":{"10":10,"2":2},"constructor":"text"}}';
  assert.equal(canonicalJson(value), expected);
  const parsed = canonicalBridgeBody(expected).value;
  assert.deepEqual(parsed, value);
  assert.equal(Object.hasOwn(parsed.nested, "__proto__"), true);
  assert.equal(Object.getPrototypeOf(parsed.nested), Object.prototype);
  assert.throws(() => canonicalBridgeBody('{"2":2,"10":10}'), (error) => error.code === "body_not_canonical");
});

test("canonical serializer rejects unsupported and malformed values with typed errors", async () => {
  for (const value of [undefined, () => {}, Symbol("unsupported"), { value: undefined }, { value: "\ud800" }, { value: "\udc00" }]) {
    assert.throws(() => canonicalJson(value), (error) => error instanceof CoreProofError && error.code === "body_json_invalid");
  }
  assert.equal(canonicalJson("ASCII"), '"ASCII"');
  assert.equal(canonicalJson("中文"), '"中文"');
  assert.equal(canonicalJson("😀"), '"😀"');
  for (const value of ["null", "[]", "1"]) {
    const claims = Buffer.from(value, "utf8").toString("base64url");
    await assert.rejects(() => verifyCoreProof(`qfcp1.current.${claims}.AA`, {
      keyId: "current", key, now: 1_800_000_000_000, method: "POST", path: "/bridge", body: new Uint8Array(),
    }), (error) => error instanceof CoreProofError);
  }
});

test("proof signs and verifies exact claims and raw canonical body", async () => {
  const body = canonicalBridgeBody(canonicalJsonBytes(baseRequest));
  const bodySha = await crypto.subtle.digest("SHA-256", body.bytes);
  const hash = `sha256:${Array.from(new Uint8Array(bodySha), (v) => v.toString(16).padStart(2, "0")).join("")}`;
  const proof = await signCoreProof({ claims: claims(hash), key });
  const verified = await verifyCoreProof(proof, { keyId: "current", key, now: 1_800_000_000_010, method: "POST", path: "/bridge", body: body.bytes });
  assert.equal(verified.project_id, "project_1");
  await assert.rejects(() => verifyCoreProof(proof, { keyId: "current", key, now: 1_800_000_000_010, method: "POST", path: "/bridge?changed", body: body.bytes }), CoreProofError);
  await assert.rejects(() => verifyCoreProof(proof, { keyId: "current", key, now: 1_800_000_000_010, method: "POST", path: "/bridge", body: new TextEncoder().encode('{"changed":1}') }), CoreProofError);
  await assert.rejects(() => verifyCoreProof(`${proof}=`, { keyId: "current", key, now: 1_800_000_000_010, method: "POST", path: "/bridge", body: body.bytes }), CoreProofError);
});

test("proof verifier accepts only exact path query and identity claims", async () => {
  const body = canonicalBridgeBody(canonicalJsonBytes({ ...baseRequest, operation: "project.open" }));
  const bodySha = await crypto.subtle.digest("SHA-256", body.bytes);
  const hash = `sha256:${Array.from(new Uint8Array(bodySha), (v) => v.toString(16).padStart(2, "0")).join("")}`;
  const proof = await signCoreProof({ claims: claims(hash, { path: "/bridge?b=2&a=1" }), key });
  const options = { keyId: "current", key, now: 1_800_000_000_010, method: "POST", path: "/bridge?b=2&a=1", body: body.bytes };
  assert.equal((await verifyCoreProof(proof, options)).path, "/bridge?b=2&a=1");
  await assert.rejects(() => verifyCoreProof(proof, { ...options, path: "/bridge?a=1&b=2" }), CoreProofError);
  await assert.rejects(() => verifyCoreProof(proof, { ...options, path: "/bridge?b=2%26a=1" }), CoreProofError);
});

test("operation matrix derives project binding without a sentinel", () => {
  assert.equal(deriveProofProjectId("project.open", baseRequest), "project_1");
  assert.equal(deriveProofProjectId("project.open", { ...baseRequest, args: { project_id: "a..b" } }), "a..b");
  for (const project_id of ["a:b", "_leading", "a".repeat(65), "with space"]) {
    assert.throws(
      () => deriveProofProjectId("project.open", { ...baseRequest, args: { project_id } }),
      (error) => error instanceof CoreProofError && error.code === "proof_project_invalid",
    );
  }
  assert.equal(deriveProofProjectId("project.list", { ...baseRequest, operation: "project.list", args: {} }), null);
  assert.throws(() => deriveProofProjectId("project.list", { ...baseRequest, operation: "project.list", args: { project_id: null } }), CoreProofError);
  assert.throws(() => deriveProofProjectId("project.open", { ...baseRequest, args: {} }), CoreProofError);
  assert.throws(() => deriveProofProjectId("project.restore", { ...baseRequest, operation: "project.restore", args: { bundle_path: "x" } }), CoreProofError);
});

test("hosted corpus capability allowlist excludes scans and rejects local paths recursively", () => {
  const request = (operation, args) => ({ ...baseRequest, operation, args });
  assert.equal(deriveProofProjectId("corpus.selection.propose", request("corpus.selection.propose", { collection_id: "collection_1", profile: "general" })), null);
  assert.equal(deriveProofProjectId("corpus.selection.propose", request("corpus.selection.propose", { study_id: "study_1", profile: "general" })), null);
  assert.equal(deriveProofProjectId("corpus.study.status", request("corpus.study.status", { study_id: "study_1" })), null);
  assert.throws(
    () => deriveProofProjectId("corpus.collection.scan", request("corpus.collection.scan", { collection_path: "C:\\novels" })),
    (error) => error instanceof CoreProofError && error.code === "proof_operation_invalid",
  );
  assert.throws(
    () => deriveProofProjectId("corpus.selection.propose", request("corpus.selection.propose", { collection_id: "collection_1", profile: "general", rights: { local_path: "C:\\novels" } })),
    (error) => error instanceof CoreProofError && error.code === "proof_local_path_forbidden",
  );
  assert.throws(
    () => deriveProofProjectId("corpus.public.validate", request("corpus.public.validate", { bundle: { source_path: "/tmp/private" } })),
    (error) => error instanceof CoreProofError && error.code === "proof_local_path_forbidden",
  );
  assert.throws(
    () => deriveProofProjectId("corpus.public.validate", request("corpus.public.validate", { bundle: { location: "C:\\private\\manifest.json" } })),
    (error) => error instanceof CoreProofError && error.code === "proof_local_path_forbidden",
  );
});

test("operation matrix matches the Host Bridge v11 contract", () => {
  const contract = JSON.parse(fs.readFileSync(new URL("../../studio/host_bridge_contract.json", import.meta.url), "utf8"));
  const required = Object.entries(contract.operations).filter(([, metadata]) => metadata.required_args?.includes("project_id")).map(([name]) => name).sort();
  const nullScoped = Object.entries(contract.operations).filter(([, metadata]) => !metadata.required_args?.includes("project_id") && metadata.allowed_surfaces?.includes("hosted_web") || !metadata.required_args?.includes("project_id") && !metadata.allowed_surfaces).map(([name]) => name).filter((name) => name !== "project.restore").sort();
  assert.deepEqual(PROJECT_REQUIRED_OPERATIONS, required);
  assert.deepEqual(PROJECT_NULL_OPERATIONS, nullScoped);
  assert.equal(PROJECT_NULL_OPERATIONS.includes("project.restore"), false);
  const hostedCorpus = Object.entries(contract.operations).filter(([name, metadata]) => name.startsWith("corpus.") && metadata.allowed_surfaces?.includes("hosted_web")).map(([name]) => name).sort();
  const hostedUserTaste = Object.entries(contract.operations).filter(([name, metadata]) => (name.startsWith("learning.user_taste.") || name.startsWith("learning.auto_activation_policy.")) && metadata.allowed_surfaces?.includes("hosted_web")).map(([name]) => name).sort();
  assert.deepEqual(HOSTED_CORPUS_OPERATIONS, hostedCorpus);
  assert.deepEqual(HOSTED_USER_TASTE_OPERATIONS, hostedUserTaste);
  assert.equal(HOSTED_CORPUS_OPERATIONS.includes("corpus.collection.scan"), false);
  assert.equal(HOSTED_CORPUS_OPERATIONS.includes("corpus.selection.private_preview"), false);
  assert.equal(Object.hasOwn(contract.operations, "corpus.selection.private_preview"), false);
  assert.deepEqual(contract.operations["corpus.selection.propose"].required_args, ["profile"]);
  assert.equal(contract.invariants.corpus_selection_propose_requires_one_of_collection_or_study, true);
});
