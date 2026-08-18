# Plan
1. 冻结 live main 与并发 owner map；将 Studio consumer PR #130 与 Core implementation 隔离。
2. 增加 production runtime contracts，以及与 Context Freeze 绑定的 immutable Context payload bundle。
3. 增加 tracked Project Context source loading、semantic profile derivation、Context Decision / Greenlight / Freeze orchestration。
4. 每个 mandatory production mechanism 只消费 frozen stage payload；Candidate 只有在 pre-independent qualification、真正外部独立的 `quality.production_review` 与 user-visible gate 全部通过后才持久化。
5. 增加 explicit Context refresh / supersession 与 stale-conflict handling。
6. 在现有 Generic Model Runtime 之上增加 Model Service facade，不创建 provider-specific product truth。
7. 将 typed Core Host Bridge 升级到 v8：除 production/model/document primitives 外，补齐 canonical project/document list、Candidate Review projection、Reject、Request Revision 与只读 Settlement preflight。
8. Request Revision 必须 durable 但不自动串模式：不得静默启动 REVISE run。
9. 加固 credential output boundary，并修复 owning persistence layer 的 SQLite connection lifetime hygiene。
10. 增加 deterministic/integration/security/backward-compatibility tests，并运行完整 Core、Studio、docs/site CI。
11. 对 exact clean runtime tree 做 deterministic Framework bundle 双构建与 exact fingerprint verification。
12. 只有当前 host 确实存在 eligible configured provider 时才做 live semantic acceptance；否则记录 `PENDING_MODEL / awaiting_external`，不得把 fixture 当作 live evidence。
13. 为 Studio PR #130 输出 v8 frontend contract handoff，清掉 review/security gate；Core PR 只有在明确授权后 merge，然后让 Studio consumer 从 fresh main rebase/integrate。
