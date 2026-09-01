# One-chapter craft review · One new chapter per iteration

This protocol lets an author judge whether evolving craft guidance is approaching the intended reading experience. Each iteration generates and presents one complete chapter that the reviewer has not seen before. It does not generate a baseline companion or require the author to choose the less bad of two failures.

The resulting judgment governs only this sequential improvement chain. Pairwise ablation tooling remains available to verify historical evidence or run a separately authorized engineering experiment; it is no longer the author-review method for this cycle.

## One iteration

1. Freeze one fresh chapter task, its declared reader positioning and the current candidate craft snapshot. The task must use `unit_kind=chapter`; a short excerpt cannot stand in for a chapter.
2. If the previous chapter was returned for revision or rejected, the craft snapshot must change before another task can be prepared. A failed edition cannot simply retry under a new premise.
3. Generate through the full production runtime. Character Enactment, Scene Realization and Reader Pressure must genuinely complete with exact stage receipts bound to the same frozen context; a narrow selector–direct-Writer ablation is not an adequate substitute.
4. Present only the one chapter exposed by `candidate.visible.get` after exact production-release validation. Plans, private character state, unreleased direct candidates, diagnostics, model identity and prior rejected prose remain hidden. Rejected prose never seeds a fresh Writer; bounded local repair receives only exact edit windows.
5. The author records `continue`, `revise`, `reject` or `insufficient_evidence`, with concrete passages and reading effects. No next chapter is prepared until that observation is bound.

[`craft_chapter_review.py`](craft_chapter_review.py) owns freezing, fingerprints, the one-chapter projection, feedback binding and the sequence gate. It never calls a model, makes a prose judgment or turns an author's response into Canon, durable taste or General Craft.

## What the author reviews

There is no composite score. The practical questions are:

- Does the opening enter live business worth following soon enough?
- Do characters have distinct interests and ways of speaking, or does one model voice give everyone polished lines?
- Does action receive a response that changes the next move, or is a procedure handled gracefully on the first attempt?
- Do interiority and narration stay with present judgment, or keep composing a thesis for the scene?
- Is the language natural, concrete and speakable for its declared profile, without literary posing, synthetic balanced claims, ornamental comparison or pseudo-pace fragments?
- By the end, has a resource, fact, relationship, position, risk or next task traceably changed?

`continue` means only that this chapter makes the current direction worth testing again. It is not manuscript acceptance or proof that the framework works. `revise` and `reject` block reuse of the same craft snapshot. `insufficient_evidence` remains unresolved evidence and is never silently counted as a pass.

## Freshness and evidence boundary

A new task cannot rename, continue or extract phrasing from rejected prose. Consumer-project material stays in its authorized local project and is never committed to the generic framework. Generic evaluation tasks must be original, have no gold label and declare that the author had not seen them before freeze.

Direct author feedback on one chapter is valuable concrete evidence, but it still speaks only to that chapter and its declared genre and platform boundary. Consistent results over several iterations may support a stronger hypothesis; they cannot automatically promote the candidate, change the default baseline or imply measured commercial retention.
