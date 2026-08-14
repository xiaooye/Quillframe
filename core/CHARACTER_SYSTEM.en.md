# Character & Relationship System

## Purpose

NovelForge treats characters as stateful agents, not trait labels or plot functions.

A character is modeled through:

```text
facts
+ current desire / long desire
+ values / fears / blind spots
+ knowledge / misbeliefs
+ risk / cost boundaries
+ problem-solving habits
+ relationship-specific behavior
+ voice
+ accumulated consequences
```

The goal is not to produce more biography. The goal is to make different people choose, notice, speak, hesitate, bargain, fail, and recover differently under the same pressure.

## Character facts

Stable/project-authoritative facts may include:

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

Only currently relevant facts belong in a scene context.

## Behavior engine

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

A trait that never changes a choice is metadata, not characterization.

## Knowledge / belief model

Characters should not share the model's global knowledge.

For each important proposition, distinguish:

- knows;
- suspects;
- misbelieves;
- heard as rumor;
- cannot know yet;
- knows but cannot safely reveal;
- knows only through another person's biased account.

Information ownership should materially influence action and dialogue.

## Voice engine

Voice is not a bag of catchphrases.

Useful dimensions:

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

Examples may be stored for reference, but should never become a copy-paste phrase generator.

## Semantic ownership

Any psychological, evaluative, comparative, or summarizing sentence must have a legitimate owner.

Ask:

> Whose mind, voice, knowledge, and social position could truthfully produce this wording now?

If the answer is “the model/narrator wants a clever sentence,” rewrite it.

This prevents narrator intelligence from leaking into characters and prevents every character from sounding like one model with different names.

## Character simulation

Before prose, a meaningful scene should simulate each important participant:

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

The simulation should produce action/response possibilities, not a polished monologue.

## Supporting-character autonomy

A supporting character fails when they exist only to:

- praise the protagonist;
- explain the world;
- block the protagonist on schedule;
- ask setup questions;
- deliver one clue;
- perform a planned emotional beat and then disappear.

Important supporting characters should retain some combination of:

- independent work;
- competing goals;
- relationships not centered on the protagonist;
- information limits;
- emotional aftereffects;
- self-interest;
- initiative;
- ability to correct or surprise the protagonist.

## Character arc

A character arc tracks meaningful state change rather than a sequence of “growth moments.”

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

Arc evidence must come from Accepted behavior. Plans may predict future change but do not settle it.

## Appeal / charisma evidence

Character appeal should be demonstrated, not asserted.

Possible mechanisms:
- competence under cost;
- generosity that costs something;
- wit belonging to the character;
- loyalty under pressure;
- principled refusal;
- vulnerability with consequence;
- social intelligence;
- courage without omniscience;
- surprising initiative;
- ability to make another character more vivid.

Avoid narrator declarations that a character is charismatic, formidable, lovable, or magnetic when the scene has not demonstrated it.

## Presence continuity

Important characters should retain consequences across scenes. Track:

```yaml
last_meaningful_action:
current_work_or_obligation:
current_relationship_residue:
known_information:
open_desire_or_problem:
next_plausible_initiative:
```

This prevents characters from disappearing into storage until the outline needs them.

# Relationship system

Relationships are stateful, asymmetric, and evidence-based.

## REL

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

Do not compress a relationship into a single scalar such as “affection 75.”

## Relationship delta

A meaningful interaction may change:

- trust;
- access/permission;
- willingness to help;
- obligation;
- attraction/aversion;
- power/status;
- shared knowledge;
- interpretation of prior behavior;
- future expectation.

A delta requires Accepted evidence before current state changes.

## Romance / intimacy extension

Romance is not a separate magic system. It extends relationship state with dimensions such as:

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

Age, consent, legal, cultural, and project constraints remain authoritative.

## Dialogue ownership integration

In multi-character scenes, relationship state should alter how people speak:

- who interrupts whom;
- who can joke safely;
- who avoids names/titles;
- who can ask a personal question;
- who explains vs assumes shared knowledge;
- who performs deference;
- who can refuse without explanation.

This is stronger than attaching mechanical speech quirks.

## Core invariant

> Characters remain people when the plot is not directly using them, and relationships remember what previous scenes cost.
