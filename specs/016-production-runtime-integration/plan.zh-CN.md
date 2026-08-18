# Plan
1. 冻结 live main 与并发 owner map，隔离 UI PR #129。
2. 增加 production runtime contracts 与 immutable Context payload bundle。
3. 增加 tracked Project Context source loader、profile derivation、Context Decision/Greenlight/Freeze orchestration。
4. 每个 mandatory mechanism 只从 frozen stage payload 执行；Candidate 只有在 independent review + user-visible gate 后才持久化。
5. 增加 explicit Context refresh 与 stale-conflict handling。
6. 在现有 Model Runtime 之上增加 Model Service facade，不创建 provider-specific product truth。
7. 升级 Core Host Bridge contract，提供 run/model/document primitives 与明确 unsupported capability projection。
8. 修复 owning persistence layer 的 SQLite connection lifetime。
9. 增加 deterministic/integration/security/backward-compat tests 并跑 full CI。
10. 只有当前 host 存在 eligible provider/credential 时才做 live semantic acceptance，否则记录 PENDING_MODEL。
11. 给 UI PR #129 输出 frontend contract handoff，创建 Draft PR，不 merge。
