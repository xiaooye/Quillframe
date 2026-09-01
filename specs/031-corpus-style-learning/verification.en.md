# Corpus style learning · Verification record

2026-08-29 · overall status: `engineering_partial_live_evidence_pending` · source-pool evidence routing: `evidence_scope_routed` · semantic/literary status: `not_run` · public release: `blocked`

This record intentionally separates completed research/specification work from evidence that does not yet exist. The files in this directory define the target and preserve the research; they do not establish that Quillframe has learned a style, that V5 has run, that a candidate improves writing, or that a public artifact is legally cleared.

## Evidence actually completed

- Repository governance, the `SYSTEM-IMPROVE` protocol, corpus/adaptive-learning boundaries and bilingual documentation rules were reviewed before drafting.
- The primary sources linked in `research.en.md` and `research.zh-CN.md` were checked at their direct publisher, author, conference or official project pages. The research record distinguishes adopt, adapt and reject decisions.
- The bilingual research, specification, plan and checklist now record the same fixed decisions: retain `STUDY-GENERAL-QUALITY-REBUILD-V5`, create no V6, do not invalidate V5, treat 120 only as a source cohort, use scene-aware adaptive sampling, compile a source-free craft pack, isolate Writer projection, require blind A/B, and keep body/appearance description inside `general` unless actual explicit context establishes another content zone.
- The implementation and specification are aligned to the agreed exact interface names, canonical ten-axis order and version-1 schema names. Deterministic engineering evidence is captured below; it still does not substitute for a real semantic run or literary decision.
- The research/specification drafting pass did not open or read a file under the local novel-copy directory. A later authorized read-only quality audit operated only inside the private boundary; this repository record contains aggregate routing counts only. No complete source work, quotation, paraphrase, title/author identity, path, reconstructive summary or reversible evidence mapping was copied into this spec directory.

## Same-ID V5 reconciliation evidence

- Immediately before the local mutation, `STUDY-GENERAL-QUALITY-REBUILD-V5` was read directly from the private SQLite ledger. It was `proposed`, with 120 `pending` works, a null checklist hash, no invalidation reason and no semantic completion dependency. Its exact proposal fingerprint was `sha256:87cebcbc251992ba7b5ed19714117c53d688524c1114734bfaf204e58f6d856b`.
- A consistent SQLite backup was created in the private backup directory before scanning or refreshing. The backup filename is `corpus-before-style-v5-refresh-20260829-001042.sqlite`; its SHA-256 is `401f075fa9d3875a19e10de8c90b83d6360b9295f88ac817cc571a789521a030` and its size is 856,064 bytes. No source prose or private locator was copied into Git.
- The authorized local collection scan completed over 387 candidate file locators and 382 logical works. It found 384 unchanged source versions, created no version, invalidated no study and persisted no source prose. Seven inputs failed closed: three exceeded the then-current source-size limit, three lacked a required EPUB member and one failed strict text decoding. No filename or source identity is recorded here. The three size-limit cases were TXT and describe the pre-streaming scan; the later 8M+ synthetic verification covers the replacement engineering path but is not evidence that a real V5 style run occurred.
- `refresh_proposed_selection` then atomically refreshed the same study using the exact before fingerprint. It preserved the study and public-study identities, preserved all 120 members, and produced the same proposal fingerprint. The result remains `proposed`, with 120 `pending`, zero selected/studied/invalidated, null checklist hash, and no implicit confirmation, semantic run or public release. No V6 study was created.
- The private diagnostic projection was regenerated and returned exactly 120 local rows. It remains private and is intentionally not serialized into this repository; the historical projection is not a 120-item literary-review gate.
- After all implementation and verification work, a final read-only SQLite query again found the same proposal fingerprint, `proposed` state, exactly 120 `pending` members, null checklist and invalidation fields, zero semantic/style completion receipts and no V6 study.
- The historical read-only cohort signals are now `EVIDENCE_SCOPE_ROUTED`, not a literary `HOLD`. Anonymous routing found one declared/content-language mismatch, three short-or-incomplete signals (one also has serial/range uncertainty), and two restart/concatenation signals. A language mismatch narrows language-specific claims; incomplete or serial material permits local prose/scene evidence but not unsupported whole-work claims; restart or concatenation signals require boundary-aware windows or narrower claims. These routes disclose no source identity and do not automatically exclude a work.
- Full first-pass exposure and a 120-item literary review are not exact-confirmation gates. Hygiene applies only to an AI-requested bounded window: a contaminated window is rejected as a whole and replaced without failing the source pool. Exact confirmation still requires the human to bind the declared rights and scope, profile, complete 120-work pool membership and proposal fingerprint. The recomputed proposal hash remains `sha256:87cebcbc251992ba7b5ed19714117c53d688524c1114734bfaf204e58f6d856b`; the checklist is unlocked, with no confirmation, run or publication.

## Deterministic verification results

- `git diff --check -- specs/031-corpus-style-learning` passed.
- WSL Python 3.14.4 ran `python3 scripts/docs_quality.py`: 0 errors and 21 warnings, all in pre-existing files outside this specification directory.
- WSL Python 3.14.4 ran `python3 scripts/quillframe_docs_quality.py`: 0 errors.
- The five bilingual pairs have matching heading counts (`22/19/14/8/8`), and both research editions contain the same 32 unique direct source URLs.
- The first direct PowerShell invocation, `python scripts/docs_quality.py`, could not start because `python` is not on that shell's `PATH`; WSL then ran the repository check successfully. This was an environment-path failure, not a failed documentation assertion.
- WSL Python 3.14.4 ran the full repository suite with no model call: `python3 -X utf8 -m unittest discover -s tests -p 'test_*.py'` completed 1,064 tests in 697.441 seconds with `OK`.
- Windows bundled Python ran the Writer craft-guidance suite: 24 tests passed. It also ran the recorded-qualification suite: 14 tests passed. The exact cloud operation-matrix regression passed after hosted Corpus operations were brought into parity.
- The focused streaming set passed 47 unit tests: 18 sampling, 23 CorpusLibrary and 6 StyleStudyRunner tests. Historical synthetic diagnostics found that an 8M+ Unicode-character TXT completed without a whole-source read and below 24 MiB peak traced memory (38.7 seconds on Windows; 32.4 seconds under WSL); a separate 7.9M all-TXT route completed sampling in 46.445 seconds and materialization in 9.439 seconds, with traced peaks of 6.177 MiB and 5.715 MiB and an independent-process RSS increase of 18.766 MiB. These measurements diagnose bounded I/O; no CPU, elapsed-time or memory threshold is a corpus-confirmation or literary-quality gate.
- Windows Node with `PYTHONUTF8=1` ran the complete Studio app suite: 117 tests passed. Studio TypeScript completed `tsc --noEmit`. The rebuilt Cloud TypeScript output passed all 8 provenance/operation-matrix tests.
- Python parsed 1,418 repository JSON files outside generated dependency/build directories; WSL PyYAML parsed `HARNESS_MANIFEST.yaml`. Selected Python packages compiled successfully, semantic reference integrity passed with 41 registered contracts, and the semantic router self-test passed without executing a model.
- A clean wheel was built and installed outside the repository. The installed package contained every Style Atlas, release-receipt, transition-receipt, trust-policy and registry resource; its default registry and `unconfigured` trust policy validated successfully. The wheel SHA-256 was `b21143c8cb966bcf951fc9fbabf95fce35cf4619425286561e1e3816b4358680`.
- A direct Windows full-Python attempt was not considered authoritative because that bundled runtime lacks the repository's native no-follow capability and its shell lacked PyYAML/Node discovery. The same repository suite passed in WSL, while Windows-specific focused and frontend suites passed in their supported host environment.

These checks establish deterministic engineering and package integration. They do not change any semantic, literary or release state below.

## Integrated engineering result

- WSL Python 3.14.4 ran `python3 -m unittest tests.test_quillframe_style_contract`: 21 tests passed.
- Every seekable TXT now enters one normalized chunk stream with 256 KiB raw reads, including works below the former in-memory threshold. A public chunk is capped at 262,144 Unicode characters and 1 MiB UTF-8; source totals are capped at 32 million Unicode characters and 128 MiB UTF-8. The decoded stream exists only in an anonymous UTF-32 temporary file for the call, while temporary SQLite stores offsets, precomputed retrieval hints and hashes—not literary scores. Selected bounded passages are returned in an ephemeral same-round cache, so ordinary semantic calls do not rescan the work; only crash/new-process recovery re-materializes exact fingerprinted spans. Oversized EPUB still fails closed with a typed error; this is bounded-materialization evidence, not a prose-learning method or a full-pool exposure requirement.
- Study start, the one-pass sampler, crash/resume re-materialization and publication dependency verification compute raw identity by streaming rather than reading whole source bytes. The bindings cover the exact active governed version and parse/availability state; raw pre/post device, inode, size and modification time; observed byte count and expected SHA-256; decoded full-text SHA-256, Unicode-character count and UTF-8 byte count; prior-manifest passage fingerprints; and each final materialized passage fingerprint/length. Any mismatch fails closed.
- Window hygiene rejects a candidate as a whole when it contains URL/domain, HTML/script or distribution/navigation boilerplate, then deterministically refills from remaining candidates. It never trims suspect lines into a different passage, and materialization repeats the check. Ordinary body/appearance description, including an isolated `巨乳`, is neither hygiene contamination nor an adult-profile signal.
- Windows bundled Python ran the focused Style Atlas publisher, receipt-loader, StyleStudyRunner, Core, Host Bridge and Corpus CLI suites: 64 tests passed and 1 symlink test was skipped on Windows. The separate CorpusLibrary suite passed 20 tests. The production loader accepts only a completion-receipt fingerprint, resolves the study through that receipt, revalidates the latest completed candidate and actual source-file SHA-256 values, then combines the result with a constructor-injected trusted provenance resolver to produce the closed publisher candidate. Forged receipt lookup, post-scan source drift, caller-supplied provenance and unbound/extra-field provenance receipts all fail closed.
- Studio TypeScript completed `tsc --noEmit`, and the focused Corpus bridge/contracts Node suite passed 8 tests. The UI exposes exact preview fingerprint/token for review, has no Style Atlas release action, and does not manufacture gate `PASS` states.
- The publisher security review passed focused adversarial coverage for caller-created trust roots, reused role keys, trust-policy drift, forged/missing receipts, unsigned registry rollback, transition-receipt tampering and failed-commit cleanup. Release and transition receipts are content-addressed, every registry revision binds one event, and trusted loads replay the event chain from genesis. The fixed sibling trust policy is deliberately `unconfigured`, so the repository cannot perform a real release by default.
- The AI-native closure regression passed 138 Corpus/style/Core/Host tests with one Windows symlink skip, 114 style-contract/craft/semantic-context tests, and all 117 Studio Node tests. TypeScript, all five Studio quality checks and the production build also passed. Negative cases prove that non-`continue` axes cannot smuggle activation requests, untouched pool members remain unanalysed, and trusted publication recomputes the complete ordered checklist while rereading source bytes only for the activated cohort.

These results verify bounded construction, closed-schema validation, source-free compilation/projection, receipt-addressed loading and the no-release UI boundary. The loader owns no trust secret and performs no release; the default Core release remains blocked without Host-configured trusted providers. The checks do not establish a real V5 semantic run, blind evaluation, real-corpus leakage pass, literary improvement or public-release authority.

## Current gate matrix

| Gate | Required evidence | Current state |
|---|---|---|
| Research persistence | Bilingual primary-source record with adopt/adapt/reject decisions | **RECORDED** |
| Live V5 status | Read current state; prove same-ID V5 is unconfirmed/unrun before mutation | **RECORDED** |
| Same-ID proposal refresh | Backup, before/after fingerprints, atomic refresh receipt, no V6 and no implicit confirm/run | **PASS** |
| Source pool | Governed identity/version ledger; exact 120 membership used as an addressable pool | **ROUTED; AWAITING EXACT RIGHTS/SCOPE/PROFILE/MEMBERSHIP/FINGERPRINT CONFIRMATION** |
| Typed style API | Exact-schema construction, validation, fingerprint and rejection tests | **PASS** |
| Bounded evidence adapter | Identity binding, bounded materialization, hygiene, replay and receipts | **PASS FOR BOUNDED TXT; OVERSIZED EPUB FAILS CLOSED** |
| Dynamic source-pool scheduling | AI selects the next eligible work/scene-function evidence from gaps and may stop before all 120 on cross-work convergence | **PASS (SYNTHETIC CONTRACT/RUNNER ONLY); LIVE V5 NOT RUN** |
| Semantic synthesis | Bound model/protocol receipts, cross-work support, contrast and counterexample review | **NOT RUN** |
| Source-free compilation | Field-removal, closed-schema, synthetic-example and public-projection tests | **PASS; PUBLIC RELEASE STILL BLOCKED** |
| Leakage protection | Exact, approximate, identity/content and independent semantic checks against real private evidence | **NOT RUN** |
| Runtime isolation | Opt-in mode, frozen selection and negative stage-routing tests | **PASS** |
| Blind causal evaluation | Source-independent held-out tasks, sealed labels, order swap and independent judgments | **MECHANISM PASS; LIVE EVIDENCE NOT RUN** |
| Human literary decision | Explicit author/human promotion or rejection on fresh outputs | **NOT RUN** |
| Public release | Validated source-free projection, package/docs sync, rollback and applicable rights review | **BLOCKED** |

`PENDING` means implementation or deterministic verification has not been credited by this record. `NOT RUN` means the required real semantic or human execution has not occurred. `BLOCKED` means the dependent gates must pass before release; it does not mean the overall project is abandoned.

## Deterministic verification completed

Focused construction/rejection suites, the full repository regression suite, Python compilation, JSON/YAML parsing, both documentation checks, semantic-contract integrity, router self-test, Studio/Cloud TypeScript and Node checks, installed-wheel resource validation and `git diff --check` were run against this working tree. Their exact environments and principal counts are recorded above. `StyleStudyRunnerTests.test_reconcile_continue_activates_exact_model_work_and_stops_large_pool_early` additionally proves on synthetic data that registered `next_evidence_requests` activate the requested eligible work and scene-function hints, untouched members stay `available_unanalysed`, only used source dependencies enter the receipt path, and a 21-work pool stops early. These results complete deterministic engineering gates only; they do not satisfy the live semantic, literary, leakage-against-private-evidence or public-release gates.

## Semantic and literary verification still required

Before exact V5 confirmation, the human must bind the declared rights and scope, profile, complete 120-work membership and exact proposal fingerprint. Language mismatch, incomplete/serial material and restart/concatenation signals remain typed evidence-scope routes during research; they are not pass/fail literary verdicts. Full-pool exposure, a 120-item literary review, and CPU, elapsed-time or memory thresholds are not confirmation gates. Hygiene still rejects an actually selected contaminated window as a whole and requests a replacement.

After exact same-ID V5 confirmation and separate run authorization, the real workflow must preserve receipts for adaptive coverage, semantic observations, evidence-scope routes, contradictions, cross-work candidates, source-free compilation and leakage decisions. AI—not keyword, punctuation or score heuristics—must own scene/style classification, gap analysis, the next evidence request and cross-work convergence. Registered-contract and synthetic-runner evidence now proves that the runner can execute a requested dynamic work cohort and stop before traversing a larger pool; it does not prove that a real model will make sound literary judgments or that V5 has run. Promotion still requires source-independent held-out fiction tasks and a blind, order-swapped control-versus-candidate comparison plus independent leakage review. Review must report content fidelity, causal movement, target mechanism, naturalness, readability, engagement, diversity, originality and leakage separately, including ties and regressions.

The following would be invalid evidence:

- “all 120 works were processed” without scene-function/style-axis coverage and saturation evidence;
- self-review by the same treatment-aware generation path;
- a single showcase opening or cherry-picked favorable output;
- automatic metrics collapsed into one promotion score;
- exact-match leakage checks without approximate, content/entity and semantic review;
- an unblinded author preference presented as the blind result;
- a public projection derived from a materially changed contract while retaining an old approval.

## Release boundary

The complete authorized works remain local/private. Git may receive only the exact closed, source-free projection after all dependency, leakage, evaluation, documentation and human-release gates pass. Noncommercial intent and abstraction reduce neither the need for provenance governance nor the need for an applicable rights review. A leakage pass is a technical risk-control result, not a legal opinion.
