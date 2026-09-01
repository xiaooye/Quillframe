# Corpus style learning research

2026-08-28 · `SYSTEM-IMPROVE` research record · primary sources checked through 2026-08-28 · no local source prose inspected for this document.

The central finding is that corpus size is not learning depth. `STUDY-GENERAL-QUALITY-REBUILD-V5` may bind 120 distinct works as a governed source set, but that number cannot establish that Quillframe has learned prose style. Depth must instead be demonstrated by coverage across scene functions and style dimensions, convergence across unrelated works, counterexamples, held-out generalization, causal improvement in blind comparison, and resistance to source leakage.

This record separates three levels that are often conflated: story architecture, scene mechanics, and prose realization. Plot frameworks can help diagnose promises or scene movement; they do not by themselves describe sentence music, narrative distance, diction, attention, embodied description, or voice.

The resulting target must remain AI-native. Model contracts own scene/style classification, evidence scope, coverage gaps, next-sample choice and cross-work convergence wherever text understanding is required. The Python runner owns only source identity/version binding, minimum bounded requested-passage materialization, hygiene, hard budgets and receipts; schema and leakage gates remain deterministic release controls rather than literary judgment. V5's 120 works are an addressable source pool rather than a learning-depth or literary-quality queue. Registered-contract and synthetic-runner tests now demonstrate dynamic cohort activation from `next_evidence_requests`, requested scene-function retrieval, truthful unused `available_unanalysed` members and early convergence before exhausting a larger pool. This engineering evidence does not mean real V5 was confirmed or run, a style was learned, blind evaluation or independent leakage review passed, or publication occurred.

## 01 · Research method and evidence boundary

The review prioritizes creator-owned craft material, official platform guidance, peer-reviewed papers, proceedings pages and project-owned research pages. Popularity is only a discovery signal. A framework's own claims are not treated as experimental proof, and results from email, summarization, advertising copy, screenplays or short stories are not silently generalized to book-length Chinese web fiction.

The implementation decision for each source is one of:

- **Adopt** — the mechanism fits Quillframe's authority, privacy and provider-neutral boundaries with no structural change.
- **Adapt** — keep the useful mechanism but change its scope, representation, evidence or execution boundary.
- **Reject for this phase** — do not implement now because the method invites imitation/leakage, requires model internals or weights, confounds content with style, or lacks suitable evidence.

No external source grants Framework-write authority. Every General Craft result remains a candidate until the repository's promotion and evaluation gates pass.

## 02 · Craft and content-creation frameworks

### Prose craft: adopt the dimensions, not an author's voice

[Ursula K. Le Guin's official page for *Steering the Craft*](https://www.ursulakleguin.com/steering-the-craft) describes craft from the sound of language through sentence construction and point of view, with exercises rather than a universal formula. This is the strongest fit for the missing prose layer.

**Adopt:** sound and rhythm, sentence construction, repetition, point of view, narrative distance and controlled practice as first-class observation axes. The corpus system should ask what an effect does and under which conditions, not whether prose matches a preferred average.

**Reject:** named-author imitation, signature-cadence targets and quotations as Writer prompts.

### Reader promise: adapt Promise–Progress–Payoff

[Brandon Sanderson's official 2025 plot lecture](https://www.brandonsanderson.com/blogs/blog/brandon-sandersons-2025-guide-to-plot-lecture-2) separates tone, story, character/conflict and structural promises, then discusses progress and payoff. A later [official character lecture](https://www.brandonsanderson.com/blogs/blog/customizing-your-character-brandon-sandersons-writing-lecture-6-2025) explicitly notes that voice or humor can outrank plot mechanics in some books.

**Adapt:** connect promise, progress evidence and payoff to Reader Expectation and chapter/scene evaluation. Preserve multiple promise kinds and allow a quiet, voice-led or reflective work to weight them differently.

**Reject:** treating Promise–Progress–Payoff as a line-style model or mandatory beat quota.

### Scene change: adapt Story Grid and Scene–Sequel/MRU

[Story Grid's Five Commandments](https://store.storygrid.com/product/five-commandments-storytelling/) identify an inciting incident, turning-point progressive complication, crisis, climax and resolution. [Randy Ingermanson's practitioner explanation of Scene, Sequel and Motivation–Reaction Units](https://www.advancedfictionwriting.com/articles/writing-the-perfect-scene/) separates external objective stimulus from internal/subjective reaction and distinguishes action-oriented and reaction-oriented scene movement.

**Adapt:** use these as optional diagnostic lenses for causal turns, value change, stimulus/reaction ordering, processing time and decision. They can label evidence about scene function and paragraph causality.

**Reject:** requiring every scene to exhibit one exact five-step shape, every setback to be a disaster, or every paragraph boundary to obey MRU doctrine. These practitioner frameworks are useful hypotheses, not universal literary laws.

### Macro outlining: keep optional and outside style learning

[Save the Cat's official 15-beat guide](https://savethecat.com/get-started) provides a macro roadmap from Opening Image to Final Image. [Randy Ingermanson's Snowflake Method](https://www.advancedfictionwriting.com/articles/snowflake-method/) iteratively expands a one-sentence premise into character and scene planning; its creator explicitly says different writers should ignore methods that do not work for them.

**Adapt:** expose these as opt-in planning or diagnosis profiles where a Project requests them.

**Reject for style learning:** do not infer prose guidance from beat placement, force a novel into fifteen beats, or use macro outline conformity as a quality score.

### Web-serial platform evidence: profile signals, not universal truth

The [official 2026 Wattys rules](https://bmth58fl.media.zestyio.com/Wattys-2026-Rules.pdf) use equally weighted judging criteria for hook, goals/motivation/conflict, voice/personality, webnovel quality/flow and readability. This is useful evidence that a major platform distinguishes voice and flow from plot mechanics. It is a contest rubric, not a controlled reader-retention study.

[Tapas's official featuring guidance](https://help.tapas.io/hc/en-us/articles/115004574534-How-do-I-get-my-novel-featured) describes its bite-sized reading environment and recommends shorter episodes; its [first-episode tutorial](https://tapas.io/newsfeed/176) calls the opening a promise to the reader and stresses specificity, readable editing and a reason to continue while stating that the tips are not fixed rules.

**Adapt:** represent platform and publication context as an applicability profile. Opening immediacy, episode length, flow, update cadence and forward pull may be assessed when the current Project selects that context.

**Reject:** global word-count targets, compulsory cliffhangers, a fixed “golden three chapters,” or the claim that contest criteria prove universal prose quality.

## 03 · What modern AI research says style is

### Style is multidimensional and contextual

[“Style is NOT a single variable”](https://aclanthology.org/2021.acl-long.185/) studies interactions among style variables and argues against treating style dimensions as independent scalar switches. [Personalized Text Generation with Fine-Grained Linguistic Control](https://arxiv.org/abs/2402.04914) likewise moves beyond coarse labels such as formality, domain and sentiment toward lexical and syntactic attributes. [Interpreting Style Representations via Style-Eliciting Prompts](https://aclanthology.org/2026.findings-acl.2039/) curates 1,010 features across 26 categories and shows the value of modular, composable natural-language style interfaces, while warning that descriptions directly inferred by an LLM can reflect bias and hallucination.

**Adopt:** a typed, multi-axis `StyleContract` with composable conditions, evidence, counterevidence and uncertainty. Separate deterministic observations from semantic claims.

**Reject:** one “style score,” one averaged web-novel voice, or independent sliders assumed not to interact.

### Verified preference descriptions are more useful than raw examples

[PROSE](https://proceedings.mlr.press/v267/aroca-ouellette25a.html) iteratively refines preference descriptions and verifies them across multiple writing samples. On the paper's summarization and email tasks, it improves generation quality over CIPHER by 33%, and combining it with in-context examples improves over in-context learning alone by up to 9%. These tasks are not fiction, so the reported gains cannot be copied to Quillframe as an expected effect size.

**Adopt:** iterative claim refinement, verification against multiple samples, deletion of unsupported specificity, and interpretable preference descriptions.

**Adapt:** apply the loop to anonymous mechanism claims across scene-function strata and unrelated works, not to identity imitation.

### Structured writing sheets beat an undifferentiated exemplar

[Mythos / “Whose story is it?”](https://aclanthology.org/2025.ijcnlp-long.82/) organizes inferred characteristics into an Author Writing Sheet and evaluates personalized story generation across plot, creativity, development and language use. Its final dataset contains 3.6K stories by 112 authors; the paper reports a 78% win rate for capturing historical style and 59% for similarity to ground-truth stories. The paper's explicit objective is author imitation, which conflicts with Quillframe's public General Corpus boundary.

**Adapt:** use a structured Claim–Evidence sheet, multiple dimensions, human validation and evidence-linked refinement.

**Reject:** author persona simulation, named-author sheets, source-identifying traits and the paper's imitation objective.

### Few-shot imitation is not deep learning

[“Catch Me If You Can? Not Yet”](https://arxiv.org/abs/2509.14543) evaluates more than 40,000 generations per model and over 400 real-world authors. It finds that few-shot in-context imitation performs better on structured formats than on nuanced informal blog/forum styles. [A 2026 preregistered post-editing study](https://aclanthology.org/2026.acl-long.2030/) finds that human edits move generated text toward the writer's style, but the result remains closer to LLM text and less diverse than unassisted human writing.

**Adopt:** evaluate subtle style on held-out works and preserve diversity as a separate outcome.

**Reject:** declaring success because a model can mimic visible punctuation or because an author recognizes some of their edits in model prose.

## 04 · Retrieval, tuning and representation choices

### Retrieval-augmented generation

[LaMP](https://aclanthology.org/2024.acl-long.399/) shows that retrieving relevant items from user profiles can improve personalized tasks. [LongLaMP](https://longlamp-benchmark.github.io/) extends the question to long-form generation and emphasizes that this setting remains underexplored. Retrieval is useful for selecting evidence during private analysis, but raw source retrieval into Writer context entangles story content, entities and style.

**Adapt:** retrieve anonymous `StyleContract` and craft-card mechanisms by current scene need. Retrieval may also choose private evidence for an analyst, inside the rights and ephemeral-materialization boundary.

**Reject:** raw-novel RAG into Writer, public embeddings derived from source prose, or automatic top-k injection. Persistent storage never means prompt eligibility.

### Disentanglement and activation steering

[StyleVector](https://aclanthology.org/2025.acl-long.353/) explicitly diagnoses content/style entanglement in historical text. It reports an 8% relative personalized-generation improvement and 1,700× lower per-user storage than PEFT by steering internal activations.

**Adapt conceptually:** contrast source behavior with neutral or counterexample behavior so claims describe a transferable mechanism rather than content.

**Reject for this phase:** activation intervention requires access to a compatible model's internal states and would break Quillframe's provider-neutral runtime. It also does not remove the rights and imitation questions attached to the source data.

### LoRA / PEFT

[StyleTunedLM](https://aclanthology.org/2024.inlg-main.34/) shows that parameter-efficient tuning can align lexical, syntactic and surface properties and uses named-entity masking to reduce content memorization. The need for masking itself demonstrates the content/style entanglement risk. [WriterAgent / WriterLoRA](https://aclanthology.org/2026.findings-acl.968/) goes further with hierarchical and cumulative modules for language style, characters and plot, but explicitly targets imitative novel generation.

**Reject for this phase:** do not train SFT/LoRA adapters on the local novels, do not publish weights, and do not construct named-author adapters. Quillframe must first prove that source-free contracts improve writing without source imitation.

### Preference optimization

[Direct Preference Optimization](https://proceedings.neurips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html) offers a simpler single-stage way to optimize a policy from chosen/rejected pairs. [GRAVITY](https://aclanthology.org/2026.eacl-long.348/) demonstrates profile-grounded synthetic preference pairs, although its book-description domain and demographic/profile assumptions do not establish fiction style quality.

**Adapt later:** if an open-weight, local-model path is separately authorized, train only on source-free synthetic tasks plus explicit user choices, with held-out and leakage evaluation.

**Reject for this phase:** no DPO, SFT or synthetic-pair tuning before the contract-and-blind-eval path works; no inferred demographic stereotype may stand in for an individual's preference.

## 05 · Memorization, leakage and public-release implications

[Deduplicating Training Data Makes Language Models Better](https://aclanthology.org/2022.acl-long.577/) reports that over 1% of unprompted output from models trained on duplicated corpora copied training text verbatim, and deduplication reduced memorized emission by about tenfold. [RAVEN](https://aclanthology.org/2023.tacl-1.38/) finds generated passages that duplicate more than 1,000 words. [The INLG 2023 memorization study](https://aclanthology.org/2023.inlg-main.3/) demonstrates that a perfect exact-match blocking defense can still leak training information through approximate or style-transfer outputs. [TACL 2025 work on fine-tuning memorization](https://aclanthology.org/2025.tacl-1.66/) finds that memorization can emerge early and uses an n-gram signal for early stopping and regularization.

The consequence is architectural, not merely a final text filter:

- originals remain local and private;
- raw ranges are ephemeral and question-bounded;
- Writer receives no raw range, quotation, title, creator, path, entity inventory or source embedding;
- public cards use a closed schema and synthetic, unrelated examples only;
- novelty checks combine exact n-grams, character n-grams/MinHash, entity and content overlap, and semantic similarity;
- work-family deduplication occurs before train/development/holdout assignment;
- a leakage pass is necessary but never described as a legal conclusion.

Abstraction, anonymity and non-commercial use reduce risk; they do not automatically establish publication rights.

## 06 · Evaluation research

[Evaluating Style Transfer for Text](https://aclanthology.org/N19-1049/) separates style strength, content preservation and naturalness, and demonstrates tradeoffs among them. [ExPerT](https://aclanthology.org/2025.findings-acl.900/) extracts atomic aspects with evidence and evaluates both content and writing-style alignment; it reports 7.2% better alignment with human judgment than prior evaluators and high explanation usability. These results support interpretable, aspect-level evaluation, not a single judge or scalar.

[LongStoryEval](https://aclanthology.org/2025.acl-long.799/) studies 600 books averaging 121K tokens and compares aggregation, incremental update and summary-based evaluation. Aggregation and summary approaches perform better in that benchmark, with aggregation stronger on detail and summaries more efficient. [Dramatron](https://deepmind.google/research/publications/13609/) shows that hierarchical prompt chaining can support long-form script co-creation, while its own project materials report formulaic output and discuss plagiarism and bias.

**Adopt:** multi-level evaluation, atomic evidence, whole-work aggregation, independent blind comparison, explicit human judgment and separate leakage checks.

**Adapt:** use summaries only as an efficient second view; preserve detail-level aggregates so a polished summary cannot hide local failure.

**Reject:** one LLM judge, one aggregate style score, self-review by the same informed Writer, or short-scene success as proof of book-length quality.

## 07 · Consolidated adopt / adapt / reject decision

| Decision | Mechanism | Quillframe implementation consequence |
| --- | --- | --- |
| Adopt | Multi-axis, interpretable style representation | Add a typed `StyleContract`; retain deterministic metrics and semantic claims separately. |
| Adopt | Iterative claim refinement and cross-sample verification | A claim needs multiple independent work-family refs, counterevidence and holdout support. |
| Adopt | Scene-function and position-aware coverage | Sample dialogue, action, interiority, exposition, transition, environment, relationship, body/appearance, opening and closure rather than fixed character offsets alone. |
| Adapt | Plot, promise and scene frameworks | Use as optional diagnostic lenses and applicability tags, never prose laws. |
| Adapt | Retrieval | Retrieve source-free mechanisms for the current scene; raw evidence is analyst-only and ephemeral. |
| Adapt | Structured writing sheets | Create anonymous Claim–Evidence craft sheets, not author personas. |
| Adapt later | Preference pairs / DPO | Only source-free synthetic pairs and explicit user decisions on a separately authorized open-weight path. |
| Reject now | Raw-excerpt RAG | It increases content/style entanglement and leakage pressure. |
| Reject now | Corpus LoRA/SFT or WriterLoRA | It is model-specific, harder to inspect and rollback, and too close to identity/content imitation. |
| Reject now | Activation steering | Valuable research direction, but incompatible with provider-neutral external APIs. |
| Reject | Named-author imitation | It conflicts with Corpus policy and the purpose of transferable General Craft. |
| Reject | Quantity-based completion | 120 works establish a governed source ledger, not style-learning sufficiency. |

## 08 · Resulting research model

The proposed learning loop is:

```text
governed, exactly confirmed V5 available source pool
→ AI requests minimum-sufficient evidence
→ deterministic identity binding + bounded ephemeral materialization
→ AI scene/style classification, evidence scope and gap judgment
→ per-work claims, variants and counterexamples
→ AI chooses the next sample or advances to cross-family verification and held-out challenge
→ source-free StyleContract
→ synthetic mechanism examples + multilayer novelty checks
→ context-selected craft candidate
→ baseline / current craft / candidate blind comparison
→ human-authorized promotion or rollback
```

### AI-native semantic-output maintenance invariants

The semantic pipeline establishes three method rules that do not depend on whether any particular live run later converges:

- `claim.scene_functions` is an open set of semantic applicability labels. A claim may use the scene-function wording needed to preserve its actual boundary. The canonical ten-function list is a bounded evidence-retrieval taxonomy for sampling and `next_evidence_requests`, not a closed ontology for source-free claims. The runner therefore enforces bounded, non-empty and unique strings without forcing claim labels into the retrieval taxonomy.
- For each Structured Outputs invocation, the provider-facing schema projection narrows opaque evidence-reference fields to a dynamic `enum` containing only IDs already supplied by that frozen job. This is a transport constraint, not a registered-contract mutation: the original `output_contract`, frozen job and its fingerprint remain unchanged, and the returned judgment is validated again against the original declared contract and the runner's payload bindings.
- Supporting and counterexample ID sets must be explicitly disjoint. The supported JSON Schema subset cannot express value-level disjointness between sibling arrays, so the registered rubric states the rule, central result binding and the runner reject violations, and execution retries the semantic judgment. Deterministic code must never delete, move or relabel an ID to make a model judgment appear valid.

Maintenance provenance is non-semantic: the before/after check for these compatibility repairs found the persisted completed job/result evidence fingerprints unchanged. The transport-only specialization and stricter rejection path rewrote no frozen job, accepted judgment or source binding. This proves only that maintenance preserved prior evidence; it does not claim run completion, convergence, writing-quality improvement, leakage clearance, promotion or release.

A language mismatch limits language-specific claims; a short, serial or incomplete work cannot support unsupported whole-work structure claims; and restart or concatenation signals require a boundary, a non-crossing sample or a narrower claim. These are evidence-scope routes, not literary-quality failures. Only invalid rights, source identity or the safety boundary of an actually requested passage blocks that source or evidence.

Learning depth is sufficient only when all of the following are evidenced:

1. required scene-function × style-axis cells have meaningful coverage;
2. new independent works yield few unsupported new claims and mostly refine confidence or boundaries;
3. claims reproduce across unrelated work families and survive counterexamples;
4. held-out works support the mechanism without revealing source identity;
5. the candidate produces a reproducible blind improvement without harming Canon, content fidelity, naturalness, diversity or originality;
6. exact, approximate, entity/content and semantic leakage gates pass;
7. a human-authorized promotion records version, provenance and rollback.

Until those gates pass, the truthful state is `review` or `semantic_pending`, not “style learned.”
