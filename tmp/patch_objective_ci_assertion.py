#!/usr/bin/env python3
from pathlib import Path
p=Path('.github/workflows/novelforge-contracts.yml')
text=p.read_text(encoding='utf-8')
old="assert set(sc['typed_input_contracts'])=={'reader.reaction','reader.engagement_audit','quality.semantic_rule_audit','quality.production_review','learning.promotion_review','character.action_propose','quality.compare','quality.ablation_compare','continuity.commitment_audit','relationship.memory_reconcile','context.select','learning.preference_interpret','scene.realization_project','editor.repair_spec'}"
new="assert set(sc['typed_input_contracts'])=={'reader.reaction','reader.engagement_audit','quality.candidate_self_audit','quality.semantic_rule_audit','quality.production_review','learning.promotion_review','character.action_propose','quality.compare','quality.ablation_compare','continuity.commitment_audit','relationship.memory_reconcile','context.select','learning.preference_interpret','scene.realization_project','editor.repair_spec'}"
if text.count(old)!=1: raise SystemExit('typed_input_contracts assertion drift')
p.write_text(text.replace(old,new,1),encoding='utf-8')
print('final contracts workflow assertion patched')
