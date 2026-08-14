<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Production Pipeline · from bounded context to a user-visible chapter</strong></p>
  <p><kbd>CONTEXT FREEZE</kbd>&nbsp;&nbsp;<kbd>SIMULATION</kbd>&nbsp;&nbsp;<kbd>RAW DRAFT</kbd>&nbsp;&nbsp;<kbd>QA</kbd>&nbsp;&nbsp;<kbd>CONTINUITY</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Production Pipeline

> 🌸 **A NovelForge chapter is produced as a gated state transition, not a single prompt completion.** Each phase owns a specific class of decision, and failures route back to the phase that can actually fix them.

---

## 01 · The production graph

```text
Context Freeze
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ Surface Lint A
→ post-generation Regression / Independent Review
→ Rewrite or Regenerate
→ Surface Lint B
→ Reader Engagement
→ Continuity Audit
→ User-visible Gate
```

Raw Draft is an internal artifact. The first text produced by the Writer is never automatically the text shown to the user.

---

## 02 · Context Freeze

The run first resolves the exact Framework and live Project authority, then creates a sparse Context Manifest.

The manifest includes only what the current chapter actually needs:

- relevant project/profile rules;
- accepted Canon and current-state slices;
- active chapter/unit plan and Scene Card;
- required characters and relationships;
- directly relevant research claims;
- unresolved dependencies or continuity obligations.

It deliberately excludes unrelated future data, whole-project dumps, hidden eval labels, negative regression examples, and the manager's entire conversation history.

**Output:** frozen task-scoped context + artifact fingerprints.

**Failure route:** context/authority repair before generation starts.

---

## 03 · Story / Canon Preflight

Before prose generation, NovelForge checks whether the planned scene is legal relative to current authority and story state.

Typical questions:

- Is the scene based on an active plan rather than an already-settled event that contradicts it?
- Does it require knowledge, resources, relationships, or locations that do not exist yet?
- Are there unresolved dependencies that must be honored?
- Is the proposed state change compatible with current Canon?
- Is the requested task actually DRAFT/REVISE rather than a hidden SETTLE or PLAN operation?

**Output:** a valid story problem for the current run.

**Failure route:** Story/Plan or authority correction. Do not “write through” a broken state model.

---

## 04 · Scene Simulation

Scene Simulation solves the event logic before sentence generation.

It determines:

- who enters the scene and why;
- what each participant is trying to achieve;
- what pressure is active;
- what information can move;
- what choice/error/obstacle changes the state;
- what cost or consequence follows;
- what the scene must accomplish without forcing a predetermined wording.

The goal is not to write prose in outline form. It is to make sure the scene has a causal engine before the Writer touches style.

**Output:** event/state trajectory.

**Failure route:** regenerate the scene model, not the sentences.

---

## 05 · Character Simulation

Important characters are simulated as independent agents inside the story world, not as obedient functions of the outline.

Each character carries, as applicable:

- agenda;
- voice;
- knowledge boundary;
- current task;
- spatial position;
- incentives and interests;
- relationship state;
- emotional aftermath from prior events.

A plan can propose what a character might do. Character Simulation decides whether that behavior is actually owned by the character under current state.

**Output:** character-owned actions/reactions and information boundaries.

**Failure route:** Character Simulation or upstream Story/Plan if the scene requires out-of-character behavior to work.

---

## 06 · Reader Pressure

Reader Pressure asks a different question from “what happens?”: **why should the reader care about this scene now?**

It establishes the chapter's expected pressure/reward structure, such as:

- an unresolved threat or desire;
- a meaningful promise to the reader;
- immediate uncertainty with consequences;
- relationship tension;
- a decision whose cost matters;
- a reveal, reversal, failure, or earned payoff;
- tonal contrast that prevents monotonous escalation.

**Output:** reader-facing pressure and reward targets.

**Failure route:** if the scene is safe but flat, return here and to Scene Simulation.

---

## 07 · Event-first Raw Draft

Only after story, character, and reader pressure are resolved does the Writer generate prose.

“Event-first” means the draft should realize state-changing events, choices, mistakes, reactions, consequences, and information movement before optimizing ornamental surface texture.

Raw Draft is intentionally protected from post-generation regression bad-example priming. Negative regression fixtures are not loaded before this point.

**Output:** internal Raw Draft.

**Visibility:** never shown directly as the finished artifact.

---

## 08 · Surface Realization + Lint A

Surface Realization brings the event-first draft into the project's prose profile while enforcing generic anti-AI failure mechanisms.

Lint A checks for obvious implementation problems before expensive semantic review. It may trigger local repair when the defect is isolated.

If problems cluster, the scene should be regenerated instead of receiving dozens of cosmetic patches.

**Output:** first surface-realized candidate.

---

## 09 · Regression + Independent Review

Only after a Raw Draft has been frozen can post-generation regression evidence be loaded. This avoids priming the Writer with known bad examples.

Post-generation checks can include:

- project-specific negative regressions;
- framework regressions;
- independent semantic review;
- capability/eval cases relevant to the active failure mechanisms.

Mandatory independent review uses a separate invocation/session and binds the result to the candidate fingerprint.

**Output:** typed defects/verdicts tied to a specific candidate.

**Failure route:** owning mechanism, not generic “make it better.”

---

## 10 · Rewrite vs. regenerate

NovelForge distinguishes repair scale.

**Local rewrite** is appropriate when a defect is isolated and the underlying scene mechanism remains sound.

**Whole-scene regeneration** is appropriate when surface defects cluster, the event logic is weak, character ownership is broken, or the reader-pressure structure is missing.

This distinction prevents patch accumulation from hiding a fundamentally bad scene.

---

## 11 · Surface Lint B

After repair, surface checks run again so the repair itself cannot reintroduce known realization failures.

Lint B is not a rubber stamp. A repaired scene can still fail and route back again.

---

## 12 · Reader Engagement gate

Reader Engagement evaluates the repaired candidate as a reading experience rather than as a code artifact.

A candidate can fail here even if it passed Surface Fundamentals. The most important special case is SAFE-BUT-FLAT: technically clean prose with insufficient pressure, payoff, contrast, causal movement, or forward pull.

**Failure route:** Reader Pressure + Scene Simulation, not sentence decoration.

---

## 13 · Continuity Audit

Continuity evaluates whether the candidate can coexist with the current project state.

It checks, as applicable:

- character knowledge and presence;
- locations and movement;
- relationship changes;
- obligations/resources/injuries/deadlines;
- chronology;
- open threads and foreshadowing;
- emotional/event aftermath;
- dependencies on accepted prior chapters.

A continuity failure may require state repair, story repair, or regeneration. It cannot be solved merely by declaring the new contradiction Canon.

---

## 14 · User-visible Gate

The candidate becomes user-visible only after every mandatory gate for the active task is resolved.

Possible truthful outcomes include:

- review artifact / complete result;
- `awaiting_user`;
- `awaiting_external`;
- `semantic_pending`;
- `failed_gate`;
- `settlement_incomplete`.

A missing mandatory reviewer is not a PASS. An unresolved continuity failure is not “production-ready.”

---

## 15 · Acceptance is not automatic settlement

A user-visible Review Draft still does not automatically mutate Canon. Settlement is a separate high-authority transaction triggered only by explicit acceptance or an explicit Canon-change request.

That transaction freezes the accepted artifact, derives a state delta, validates exact before-state, checks dependency impact, records write intent/checkpoint, performs the authorized write, rebuilds derived views, verifies post-conditions, and records a trace.

This keeps generation/review and Canon mutation deliberately separate.

---

## 16 · Why the pipeline is this strict

The pipeline is designed around recurring long-form AI failure modes:

- future-plan leakage into current truth;
- characters knowing what only the manager knows;
- polished prose hiding inert scene design;
- writer self-review masquerading as independence;
- regression examples contaminating first-pass generation;
- repeated local patches degrading scene coherence;
- session memory silently mutating story authority;
- accidental side-effect repetition after resume.

The cost is more execution ceremony. The benefit is that each class of failure has a visible owner and a repair path.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Simulate first. Draft second. Judge independently. Expose only what passed. 🌸</sub>
</div>
