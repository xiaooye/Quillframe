# Character & Relationship System · Independent people, asymmetric relationships, bounded knowledge

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>CHARACTER STATE</kbd>&nbsp;&nbsp;<kbd>RELATIONSHIP STATE</kbd>&nbsp;&nbsp;<kbd>KNOWLEDGE BOUNDARIES</kbd></p>

Quillframe treats important characters as **stateful agents with their own goals, knowledge, limits, work, relationships, and consequences**. A character is not a trait card and a supporting character is not a delivery mechanism for the protagonist's plot.

> **Boundary ✦** This system defines generic character/relationship mechanics and simulation inputs. The consuming project owns the actual people, their Accepted history, and their current authoritative state.

## 01 · What this system owns

The Character & Relationship System defines mechanics for:

- stable character facts and changeable behavior state;
- current and long-term desire;
- knowledge, suspicion, rumor, misbelief, and information limits;
- values, fears, blind spots, risk/cost boundaries, and problem-solving habits;
- voice as relationship- and pressure-sensitive behavior;
- presence continuity across scenes;
- character arcs and demonstrated appeal;
- asymmetric relationship state;
- relationship deltas supported by Accepted evidence;
- scene-level Character Simulation;
- evidence-bounded integrity checks.

It does not own:

- global story truth;
- Canon settlement;
- research truth;
- planning authority;
- runtime/session memory;
- narrator omniscience;
- the result of an independent semantic gate.

## 02 · Character state has layers

A useful character model separates relatively stable identity from changeable behavior state.

### Stable / project-authoritative facts

```yaml
names:
birth:
age_by_period:
family:
origin:
class_or_social_position:
occupation:
education:
languages:
legal_status:
health:
material_conditions:
biography:
```

Only facts relevant to the current task belong in active context.

### Behavioral state

```yaml
current_desire:
long_desire:
fear:
what_they_protect:
values: []
biases: []
blind_spots: []
first_response_to_trouble:
problem_solving_habit:
risk_tolerance:
acceptable_cost:
unacceptable_cost:
professional_strength:
professional_boundary:
knowledge_boundary:
misbeliefs: []
```

A trait that never changes a choice, perception, tactic, relationship, or cost boundary is mostly metadata.

## 03 · Agenda before adjectives

For every important participant in a scene, answer concrete questions:

```yaml
character_id:
what_do_they_want_now:
what_do_they_think_is_happening:
what_are_they_wrong_about:
what_can_they_leverage:
what_will_they_not_pay:
what_are_they_doing_physically_or_professionally:
what_will_make_them_change_tactic:
what_residue_do_they_carry_from_prior_scenes:
```

The point is not to generate a psychological essay. It is to make action and response **different because the people are different**.

Two characters facing the same pressure should not automatically notice the same thing, accept the same cost, choose the same tactic, or explain themselves in the same way.

## 04 · Knowledge is state, not model access

Characters must not inherit the model's global context.

For any proposition that matters, distinguish whether the character:

- knows it;
- suspects it;
- misbelieves something else;
- heard it as rumor;
- cannot know it yet;
- knows it but cannot safely reveal it;
- knows only another person's biased account.

World truth and character belief are different state domains.

```text
world truth ≠ POV access ≠ character knowledge ≠ character belief ≠ rumor
```

Information ownership should materially affect action and dialogue. If a scene works only because a character knows what the model knows, the scene has failed before prose realization.

## 05 · Voice is behavior under conditions

Voice is not a list of catchphrases.

Useful dimensions include:

```yaml
address_terms:
vocabulary_range:
words_they_would_not_use:
sentence_length_tendency:
directness:
interrupt_or_wait:
what_they_avoid_saying:
stress_voice_change:
voice_by_relationship: {}
language_or_dialect:
professional_register:
humor_mechanism:
```

Voice should change naturally with:

- whom the character is speaking to;
- what they want;
- what they know;
- status and permission;
- urgency and risk;
- whether they are hiding, bargaining, testing, teaching, comforting, or attacking.

Reference examples may help calibrate a voice, but they must never become a phrase-reuse machine.

## 06 · Semantic ownership

Any psychological, evaluative, comparative, interpretive, or summarizing sentence needs a legitimate owner.

Ask:

> Whose mind, voice, knowledge, profession, class position, and relationship could truthfully produce this wording **now**?

If the answer is “the model wants a clever sentence,” the sentence is unowned.

This rule prevents:

- narrator intelligence leaking into a focal character;
- one model voice appearing under different names;
- historical/social knowledge appearing before a character could possess it;
- relationship judgments being stated from nowhere.

Semantic ownership is a prose and simulation invariant, not merely a style preference.

## 07 · Supporting-character autonomy

A supporting character collapses when they exist only to:

- praise or validate the protagonist;
- explain the world;
- block the protagonist on schedule;
- ask setup questions;
- deliver a clue;
- perform one emotional beat and disappear.

Important supporting characters should retain some combination of:

- independent work or obligation;
- goals that do not center the protagonist;
- relationships elsewhere in the world;
- information limits and private knowledge;
- self-interest;
- emotional aftereffects;
- initiative;
- ability to surprise, correct, refuse, bargain with, or outmaneuver the protagonist.

Autonomy does not require equal page time. It requires **causal existence when off-center**.

## 08 · Presence continuity

Important characters should not disappear into storage until the outline needs them again.

Track enough state to make re-entry plausible:

```yaml
last_meaningful_action:
current_work_or_obligation:
current_relationship_residue:
known_information:
open_desire_or_problem:
next_plausible_initiative:
```

Presence continuity asks: *what is this person doing, carrying, owing, expecting, or trying while the camera is elsewhere?*

The answer can be sparse. It should not be zero.

## 09 · Character arcs require evidence

A character arc is a state trajectory, not a list of scheduled “growth moments.”

```yaml
id:
character_id:
scope:
arc_type: growth|flat|negative|corruption|mixed
start_state:
start_misbelief_or_limit:
latent_strength:
pressure_sources: []
turning_points: []
choices_that_prove_change: []
cost_of_change:
end_state:
status:
```

Plans may propose future turning points. Current arc state changes only when Accepted behavior provides evidence.

A character does not “become braver” because a plan says so. The project should be able to point to choices, costs, refusals, failures, or changed behavior that establish the shift.

## 10 · Appeal is demonstrated

Character appeal should be evidenced in scene behavior.

Possible mechanisms include:

- competence under cost;
- generosity that costs something;
- wit that belongs to the character;
- loyalty under pressure;
- principled refusal;
- vulnerability with consequence;
- social intelligence;
- courage without omniscience;
- surprising initiative;
- making another character more vivid.

Avoid narrator declarations that someone is charismatic, formidable, lovable, brilliant, or magnetic when the scene has not demonstrated the claim.

## 11 · Relationship state is asymmetric

Relationships are stateful and usually asymmetric. Do not compress them into one scalar such as “affection = 75.”

```yaml
id:
participants: []
relationship_type:
current_state:
trust_by_side: {}
status_by_side: {}
permissions_by_side: {}
obligations_by_side: {}
known_private_information: {}
conflict_points: []
shared_history_refs: []
current_expectations: {}
last_meaningful_change:
evidence_refs: []
status:
```

One person may trust more, know more, owe more, want more intimacy, grant less permission, or interpret the same history differently.

That asymmetry is often where scene energy comes from.

## 12 · Relationship deltas need Accepted evidence

A meaningful interaction may change:

- trust;
- access or permission;
- willingness to help;
- obligation;
- attraction or aversion;
- power or status;
- shared knowledge;
- interpretation of prior behavior;
- future expectation.

A planned interaction may predict a delta. A Review Draft may depict a delta. **Current relationship state changes only after Accepted evidence and the project's normal settlement path.**

## 13 · Romance and intimacy extend relationship state

Romance is not a separate magic system. It adds dimensions such as:

```yaml
attraction_by_side: {}
romantic_awareness_by_side: {}
jealousy_or_exclusivity:
physical_intimacy_permission:
emotional_intimacy_permission:
public_private_gap:
relationship_definition:
future_expectation:
```

Age, consent, legal, cultural, and project-specific constraints remain authoritative.

## 14 · Relationship state changes dialogue ownership

In a multi-character scene, relationship state should affect:

- who interrupts whom;
- who can joke safely;
- who uses a title, surname, nickname, or no name;
- who can ask a personal question;
- who is allowed to correct whom;
- what must be said indirectly;
- what help can be requested without explanation;
- which silence is ordinary and which is costly.

Dialogue becomes easier to attribute when people have different agendas, knowledge, tasks, social permissions, and histories.

Speaker tags can clarify syntax. They cannot substitute for ownership.

## 15 · Character Simulation output

Before prose, Character Simulation should produce a bounded operational view rather than polished prose.

Useful output:

```yaml
participants:
  CHAR-X:
    current_goal:
    model_of_situation:
    knowledge:
    misbelief_or_gap:
    leverage:
    unacceptable_cost:
    task_or_position:
    likely_first_tactic:
    tactic_change_trigger:
    relationship_constraints:
    residue:
plausible_collisions: []
surprise_opportunities: []
knowledge_conflicts: []
```

The simulation should make conflicts and possible reactions legible while leaving sentence-level realization to the drafting stage.

## 16 · Character Integrity audit interface

Quillframe may run a bounded Character Integrity audit after a candidate exists. The audit checks evidence such as:

- agenda alignment;
- knowledge boundary;
- voice drift;
- relationship position;
- spatial/task state;
- whether a surprise is consistent rather than random.

The audit receives only the candidate excerpt and the typed character/relationship state required for the judgment. It must not receive hidden gold, private chain-of-thought, writer scratchpads, or regression bad examples.

The result is a typed finding. It does **not** mutate character state and does not automatically satisfy an independent semantic gate.

See [Quality Evolution](../docs/quality-evolution.en.md).

## 17 · Failure semantics

Route failure to the owning mechanism:

- character knows impossible information → knowledge/state repair or Character Simulation;
- everyone chooses the same tactic → agenda/cost/problem-solving differentiation;
- supporting character is a function → restore independent agenda, work, limits, and initiative;
- dialogue attribution collapses → repair ownership/task/voice before adding tags everywhere;
- relationship jumps without evidence → revert current state and repair plan/settlement;
- planned arc change appears as current fact → restore Plan ≠ Canon boundary;
- prose contains unowned judgments → POV/semantic-ownership rewrite;
- integrity audit rejects a candidate → repair the identified owner; do not change Canon to fit the draft.

## 18 · Invariants

1. Important characters retain independent agenda and information boundaries.
2. Character knowledge never defaults to model knowledge.
3. Relationship state may be asymmetric.
4. Plans do not update current character/relationship state.
5. Current-state deltas require Accepted evidence and project settlement.
6. Voice belongs to a person under conditions, not to a catchphrase template.
7. Semantic judgments require a legitimate POV/voice owner.
8. Quality audits diagnose; they do not grant authority.

## 19 · Related contracts

- [Story System](STORY_SYSTEM.en.md) — planning scale and Scene Card responsibilities.
- [Canon & State Model](CANON_STATE.en.md) — authority, Accepted evidence, and settlement.
- [Surface Fundamentals](../surface/FUNDAMENTALS.en.md) — speaker drift, functional-character collapse, and semantic-role failure.
- [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) — character-owned energy, surprise, relationship movement, and reader investment.
- [Quality Evolution](../docs/quality-evolution.en.md) — bounded Character Integrity diagnostics and repair routing.
