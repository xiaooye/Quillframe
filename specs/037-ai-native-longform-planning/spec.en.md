# AI-native long-form planning v2

Quillframe needs a planning contract that can support multi-million-character fiction without asking an author or model to pre-script the whole novel. The system therefore keeps distant plans coarse, makes the current narrative unit concrete, and freezes only the current chapter's executable scene script.

## Contract

The planning order is:

1. story foundation and initial character/relationship arcs;
2. book direction;
3. volume promise and net situation change;
4. narrative unit loop;
5. chapter contract;
6. ordered scene script;
7. scene-by-scene prose production and settlement.

Story design and literary judgment remain model-owned. Rust validates only typed completeness, identity, ordering, references, fingerprints, CAS and authority boundaries.

`BookPlan` owns a typed `StoryFoundation`, `CharacterArcPlan` records and `RelationshipArcPlan` records. These are active planning artifacts, not settled character or relationship state, and must not be copied into the authoritative `characters` or `relationships` projections.

`ChapterPlan` is split into `ChapterContract` and `SceneScript`. A scene records goal, opposition, turn, choice, consequence, value shift, information change, entry/exit state and intended reader/emotional effect. This is an executable semantic contract, not prewritten dialogue or prose.

## Inheritance and freezing

The existing Book → Volume → Unit → Chapter fingerprint chain remains the single source of hierarchical planning truth. WriterPack continues to bind the exact four active proposals. It deterministically derives scene briefs from the frozen `SceneScript`; callers may not substitute different scene content under the same scene ID and ordinal.

Changing an active ancestor makes descendants ineligible for a new WriterPack until they are explicitly replanned and reactivated. No compatibility adapter, dual reader or state upgrader is added.

## State cutover

Typed plan proposal becomes `quillframe_typed_plan_proposal_v2`, hierarchical plan lock becomes `quillframe_hierarchical_plan_lock_v2`, and WriterPack becomes `quillframe_writer_pack_v4`.

Project schema fragment 024 records `ai-native-longform-v2`. A Project database missing that exact fragment fails closed on open. Existing Project data is not migrated silently.

## Acceptance

- Book plans reject missing foundations, duplicate character IDs, and relationship arcs whose two participants are not distinct known characters.
- Chapter plans reject incomplete contracts, unordered scene scripts, and scenes missing causal state-change fields.
- Plan and WriterPack fingerprints cover every new field.
- WriterPack scene briefs are derived from the frozen chapter script and reject substituted content.
- The Rust production test completes hierarchical plan activation, scene generation, review, acceptance and settlement without a live model provider.

