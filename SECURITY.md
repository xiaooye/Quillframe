# Security Policy

Quillframe handles model credentials, manuscript/project data, local files, tool execution, and durable SQLite state. Please treat security reports and reproduction data accordingly.

## Reporting a vulnerability

**Do not open a public issue for an unpatched vulnerability, exploit details, credentials, or private project data.**

Preferred route:

1. If GitHub shows **Report a vulnerability** / Private Vulnerability Reporting for this repository, use that private Security Advisory flow.
2. If that private GitHub flow is not available, contact the repository owner privately using a contact method exposed on the owner's GitHub profile. Do not post the vulnerability details publicly while trying to establish contact.

Please include only what is necessary to reproduce and assess the issue:

- affected Quillframe version and/or exact commit SHA;
- affected surface (`quillframe`, Model Runtime, Agent Runtime, Core, Studio, site/docs, persistence, deployment, etc.);
- operating system/runtime versions where relevant;
- impact and realistic attack preconditions;
- minimal reproduction steps or proof of concept;
- expected vs actual security boundary;
- whether secrets or private project data may already have been exposed.

Please avoid destructive testing, accessing data that is not yours, or persistence beyond the minimum needed to confirm the issue.

## Secrets

An **Access Token is a secret** even though the ordinary Model Service setup surface is only `API Endpoint + Access Token`.

Resolved token values must not enter:

- prompts or model-visible Context;
- Model Service snapshots;
- AgentJob / AgentResult;
- semantic job packets;
- checkpoints, receipts, logs, or fingerprints;
- SQLite durable state;
- client-side browser storage;
- Vite/JavaScript bundles.

Durable Model Service state stores a credential reference only. The host resolves the actual credential just in time for inference.

Do not paste real tokens into issues, PRs, screenshots, test fixtures, terminal transcripts, or documentation examples. If a token is accidentally exposed, revoke/rotate it with the issuing service rather than relying on repository deletion alone.

## Hosted deployments

Hosted secrets must remain server-side. Anything placed in client-exposed Vite environment variables, static assets, generated JavaScript, or public deployment configuration should be assumed readable by users.

A hosted Quillframe UI must communicate with an authenticated Core/API boundary; it must not rely on ephemeral serverless/container disk as durable SQLite storage.

## Project and SQLite data

A Quillframe project database can contain manuscript text, project structure, state, provenance, and other author data. Treat `~/.quillframe/`, project `project.sqlite` files, backups, blobs, and exports as potentially sensitive.

For bug/security reports:

- prefer a minimal synthetic project;
- redact manuscript text and personal information;
- do not attach a real project database unless a private channel has been established and the data is necessary;
- remove absolute paths, tokens, and unrelated logs where possible.

## Model and tool boundaries

Model output, AgentResult, ToolReceipt, Checkpoint, autosave, and persistence do not grant Canon, Settlement, Project, or Framework-write authority. A vulnerability that bypasses permission, checkpoint, receipt, before-state, consume-once, fingerprint, or authority checks is security-relevant even if the resulting content appears plausible.

Repository/process tools should continue to fail closed around secret-bearing paths and unsafe execution environments. Redirect/network-policy bypasses around Model API endpoints are also security-relevant.

## Supported versions

Security fixes target the active `1.0.0-dev.x` prerelease line unless the repository explicitly documents otherwise. When reporting a problem, always include the exact version/SHA because behavior may change before 1.0 release acceptance.

## Public disclosure

Please allow time for triage and a fix before public disclosure. Once a fix or mitigation is available, maintainers may publish a Security Advisory with appropriate credit, subject to the reporter's preference and the details safe to disclose.
