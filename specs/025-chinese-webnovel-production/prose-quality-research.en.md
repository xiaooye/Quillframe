# Chinese webnovel prose and reader calibration

2026-08-28 · Primary mode: `RESEARCH` · **Research proposal; no implementation or quality improvement has been verified.** This note contains no consumer manuscript, private author preference, or novel text. No external skill was installed, external code imported, new production model call made, or existing candidate verdict changed.

Question: why can a coherent chapter with consistent state still lack character presence and reading appeal? The investigation separates concrete writing guidance, presentation in public fiction, and the tasks Quillframe actually sends to models. Exact sources and revisions are in the [source register](prose-quality-sources.yaml).

## Skills worth inspecting

| Source | Useful mechanism | Boundary |
| --- | --- | --- |
| [oh-story writing craft, sections 1 and 8](https://github.com/zenstory-ai/oh-story-claudecode/blob/66d61809084ec4c5902b659af24ce2acdfa2ed42/skills/story-long-write/references/writing-craft.md) | An outline need not determine prose shape. Expand consequential moments, compress transitions, and do not translate every emotion into a bodily reaction. | Its event counts, prop quotas, and fixed viewpoint are not universal gates. |
| [Chinese Webnovel Skills: expansion](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/skills/expand/SKILL.md) and [dialogue](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/skills/dialogue/SKILL.md) | Dialogue reflects identity, purpose, relationships, and distinct voices. | Default first person and prescribed gratification beats cannot replace project intent. |
| [Ani Book: Chinese prose revision](https://github.com/ExplosiveCoderflome/ani-book-skill/blob/44a0eb216eee234101af1984df20726713b7690e/references/chinese-novel-humanization.md) | Repair clusters of explanation and uniform dialogue; restructure sentences while preserving established facts. | Detector scores are not literary quality, and guidance alone is not evidence of effectiveness. |
| [Webnovel Writer: craft catalog](https://github.com/lingfengQAQ/webnovel-writer/blob/2041abad78211e29a67a2f0c64b2a97a747dce57/webnovel-writer/references/csv/%E5%86%99%E4%BD%9C%E6%8A%80%E6%B3%95.csv) | Scene purpose and conversational aims help select what to dramatize. | Attaching an action to every utterance can create redundant reactions. |

[Novel Architect's chapter workflow](https://github.com/zhougz520/novel-architect/blob/8be80352257f98151921d89200e63464759a329f/docs/guides/chapter-workflow.md) also offers promise and payoff records. Keyword or punctuation weights cannot establish actual audience retention.

Skills themselves require judgment. [Human Texture](https://github.com/tance-mang/chinese-webnovel-skills/blob/ecf552f6930e769d8bbf17818ad3d5a864a7a70b/references/human-texture.md) identifies uniform emotional response as a problem; irrationality and unresolved loops should not become prerequisites for believable people.

[oh-story's reaction experiment](https://github.com/zenstory-ai/oh-story-claudecode/blob/66d61809084ec4c5902b659af24ce2acdfa2ed42/demo/craft-stock-reaction-eval/README.md) reports that extra self-check questions alone did not reliably help, whereas changing upstream generation guidance produced directional improvement. It used one chapter, one model, three generations per arm, and reviewers from the same model family. Full outputs are unpublished. We inspected the report, not an independently reproduced result; it does not establish retention or general quality.

## Public opening chapters

The following official, freely accessible first chapters were read alongside official author lessons. Only links and summaries are retained. Original prose, distinctive phrasing, and characters are not placed in generation context.

- [三九音域,《我在精神病院学斩神》, chapter 1](https://fanqienovel.com/reader/6982735801973113351): bystanders' uncertainty, family life, and a medical follow-up alternate without an opening battle. This offers a contrast between suspense and warmth.
- [竹已,《难哄》, chapter 1](https://www.jjwxc.net/onebook.php?novelid=4001734&chapterid=1): domestic inconvenience, a friend's call, and a reunion reveal different responses. Voice and avoidance change relationships rather than merely record activity.
- Fanqie's [opening lesson](https://fanqienovel.com/writer/zone/article/7480087779494346776) relates action and circumstances to the work's central appeal and states limits to its advice. Its [supporting-character lesson](https://fanqienovel.com/writer/zone/article/7651510334422777881) emphasizes independent aims and reasons for action.

These bounded observations do not represent all web fiction or prove retention gains. Quiet scenes, documentary forms, professional procedure, and restrained narration may all be valuable. More events, conflict, or bodily reactions are not universal objectives.

## Gaps in the actual implementation

This inspection concerns commit `2053e854049c00780c4fc2027657a7ec6c7fbd5f`. Findings are classified as `DOCUMENTATION_DISCOVERED_IMPLEMENTATION_GAP`, not completed repairs.

1. **Writing requirements do not sufficiently reach the actual input.** `_stage_instruction` in the [runtime](../../production_runtime/runtime.py) gives draft and realization stages little specific guidance. The [scene projection](../../harness/semantic_workers/contracts/production-loop.json) mainly supplies causal traces. Neither clearly separates an event list from decisions about narrative duration, viewpoint, and pacing. An ablation is needed to establish its effect on generation.
2. **A proposed reward is not an experienced reward.** `reader.pressure` runs before prose generation. Source validation proves provenance, not reader experience. A blind reader must judge the manuscript without seeing the expected answer.
3. **Documentation and production review use different standards.** [Reader Fundamentals RG-15](../../surface/READER_ENGAGEMENT.en.md) allows technically clean but flat fiction to fail. The [registered Reader and independent contracts](../../harness/semantic_workers/contracts/quality.json) lack an equally explicit positive-quality threshold. [Task packaging](../../production_runtime/semantic.py) sends the registered task; it does not automatically load the fundamentals document.
4. **Reading context is not transmitted consistently.** Reader and independent contracts support `genre_profile`, `platform_profile`, and `chapter_position`, but current construction omits them. `reader_grip` is also not an explicit, consistently propagated argument to Writer and pressure. Freeze explicit positioning for each stage. Blind Reader and independent review receive only reader-eligible information, excluding future plans, creator explanations, past verdicts, and hidden answers. Writer and pressure retain their authorized creative inputs while respecting character-private-state boundaries.
5. **Wiring tests do not calibrate literary judgment.** The [flat-fiction fixture](../../evals/cases/reader_safe_but_flat_reject.json) uses an English summary, a special rubric, and `blocks_release=false`. The [production test double](../../tests/test_quillframe_production_runtime.py) supplies a fixed Reader pass. These remain useful engineering tests, but do not establish the real contract's ability to reject flat Chinese chapters.

## Proposed validation order

1. **Inspect actual inputs first.** Capture constructed jobs and verify that relevant writing guidance and explicit reading context reach the appropriate frozen inputs. Use negative tests to keep future plans, creator explanations, prior verdicts, and hidden answers out of Blind Reader and independent review. Preserve authorized plans and repair constraints for writing stages without expanding access to character-private state.
2. **Separate generation from reviewer calibration.** Hold story task, model, and budget fixed while comparing current generation, added realization guidance, and then explicit project positioning. Evaluate reviewer changes separately against fixed complete Chinese texts through the actual registered contracts, measuring both false acceptance and false rejection.
3. **Include counterexamples.** Pair flat chronological narration with richer presentation of the same events; include quiet but rewarding scenes and engaging professional procedure. Hide human labels, randomize identities, balance pair order, and retain reviewer disagreements.
4. **Return to the author.** Model reports cannot replace author judgment. Record actual choices and reasons as hypotheses at the narrowest supported scope. Do not automatically activate preferences, promote general rules, accept manuscripts, or settle state.

This investigation completed source research, code inspection, and a validation proposal only. Behavior changes, full Chinese blind evaluation, and quality gains remain unverified. New documentation and a passing documentation check cannot substitute for that work.
