# Bounded prose evaluation · 2026-08-28

This local experiment completed 22 real model calls under framework commit `fa8e429ab2e4a56e1573b934d79443e14c1e614d`. It did **not establish a quality improvement**. The fixture labels are provisional synthetic author hypotheses, not human judgments or market evidence.

## Execution

Model: `gpt-5.5`, reasoning effort `xhigh`; the provider-managed model revision was not pinned. Each call used a fresh CLI invocation. The executor preserved original responses, actual thread identities, request/response hashes, usage and order mappings. All 22 attempts completed without retry; 22 distinct worker threads and 18 semantic result bindings were verified.

The batch comprised 16 rubric-calibration calls, four generation calls, and two registered `reader.compare` calls. Normal tests did not dispatch these calls. This experiment did not execute an independent production gate or grant manuscript release authority.

## Rubric calibration

Four complete synthetic scenes covered quiet family/shop fiction and orbital-maintenance fiction. Current quality pack 8 and archived quality pack 7 each evaluated all four scenes through registered Reader jobs and separate complete production-review rubric snapshots. The snapshots were evaluation jobs, not production-review executions.

| Contract criteria | Quality 7 | Quality 8 | Disagreement with fixture hypotheses in each version |
| --- | --- | --- | --- |
| Reader engagement | 4 pass | 4 pass | Both intended negative controls passed; neither intended positive failed |
| Production-review rubric snapshot | 4 pass | 4 pass | Both intended negative controls passed; neither intended positive failed |

There were no verdict changes between versions. These results do not demonstrate that the revised criteria distinguish mechanical reporting from engaging scene realization. They also do not establish that the provisional negative labels are correct.

## Generation comparison

Both arms used the same synthetic event brief and actual raw-draft/surface instruction functions. The only external change was the presence of `WRITER_REALIZATION_GUIDANCE`; each surface call consumed its own arm's actual raw draft. Neither fixture prose nor hidden labels entered generation.

| Presentation | A | B | Actual judgment |
| --- | --- | --- | --- |
| First | Guidance present | Guidance absent | A, confidence 0.72 |
| Reversed | Guidance absent | Guidance present | A, confidence 0.78 |

The exact texts were swapped. The preferred version changed with presentation order, so this pair does not identify a stable winner. Two judgments of one pair cannot establish a general position-bias rate or literary superiority.

## Consequence

Retain the observations without changing labels, repeating draws until success, or treating a pass as author approval. The engineering changes and their source-bound execution are verified separately from prose quality. A real production draft and the author's reading remain necessary; broader quality claims require better human-grounded calibration and additional independent examples.
