# 008 Plan · State Integrity P0

1. 冻结/同步 exact current Framework main；开发期间绝不修改下游 Project lock。
2. 先稳定 #69 property write-source policy、deterministic route 与 legacy compatibility。
3. 重新读取 current-main state graph、Settlement、memory invalidation、quality-evolution、dependency、resume mechanisms。
4. 将 #63 实现成 non-authoritative durable ledger；只有 fingerprint-bound explicit dependency evidence 才能开 debt。
5. Open/discharge/supersede/waive 全部要求幂等 + evidence binding，并证明 restart 不会重复 work。
6. Open debt 默认 advisory；只有具体 workflow 明确声明 debt-free precondition 才能成为 blocker，不能做全局 resume lock。
7. 先把 state-integrity executable test 接进 normal full CI；语义全绿后再补 Framework manifest discovery。
8. 持续同步 concurrent main，不覆盖 Studio/runtime 工作；promotion 前审 exact diff + public CI。

Rollback：revert P0 并删除/重建 derived debt DB；既有 Canon、Settlement transaction、Project files 与 locks 不变。
