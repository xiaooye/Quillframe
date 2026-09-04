use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, BookPlan, CoreError, CoreResult, PlanBody};

pub const BOOK_SETUP_SCHEMA: &str = "quillframe_book_setup_v1";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BookSetupSourceEvidence {
    pub source_id: String,
    pub source_kind: String,
    pub source_uri: String,
    pub source_revision: String,
    pub content_fingerprint: String,
    pub role: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterVoiceProfile {
    pub baseline: String,
    pub with_intimates: String,
    pub with_authority: String,
    pub under_pressure: String,
    pub avoids_saying: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterBible {
    pub character_id: String,
    pub display_name: String,
    pub story_function: String,
    pub external_want: String,
    pub private_need: String,
    pub fear_or_shame: String,
    pub false_belief: String,
    pub values: Vec<String>,
    pub public_mask: String,
    pub default_strategy: String,
    pub pressure_leak: String,
    pub defense_or_humor: String,
    pub voice: CharacterVoiceProfile,
    pub knowledge_boundaries: Vec<String>,
    pub non_negotiables: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RelationshipBible {
    pub relationship_id: String,
    pub participant_ids: Vec<String>,
    pub shared_history: String,
    pub current_surface: String,
    pub hidden_debt: String,
    pub power_balance: String,
    pub forbidden_topic: String,
    pub default_pattern: String,
    pub participant_tactics: BTreeMap<String, String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WorldSeed {
    pub seed_id: String,
    pub topic: String,
    pub rule: String,
    pub narrative_pressure: String,
    pub unknowns: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct MacroPartSeed {
    pub part_id: String,
    pub ordinal: u32,
    pub title: String,
    pub story_engine: String,
    pub protagonist_role: String,
    pub entry_state: String,
    pub terminal_state: String,
    pub terminal_climax_id: String,
    pub minimum_capacity_characters: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VolumeTurnSeed {
    pub turn_id: String,
    pub phase: String,
    pub event: String,
    pub consequence: String,
    pub advanced_arc_ids: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct VolumeBlueprintSeed {
    pub volume_id: String,
    pub ordinal: u32,
    pub macro_part_id: String,
    pub title: String,
    pub time_scope: String,
    pub dramatic_question: String,
    pub entry_state: String,
    pub main_plot: String,
    pub major_turns: Vec<VolumeTurnSeed>,
    pub active_arc_ids: Vec<String>,
    pub climax_id: String,
    pub irreversible_exit_state: String,
    pub next_volume_handoff: String,
    pub minimum_capacity_characters: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ArcMilestoneSeed {
    pub volume_id: String,
    pub change: String,
    pub consequence: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NarrativeArcKind {
    MainPlot,
    Subplot,
    Business,
    Political,
    Relationship,
    Romance,
    Character,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NarrativeArcSeed {
    pub arc_id: String,
    pub kind: NarrativeArcKind,
    pub title: String,
    pub participant_ids: Vec<String>,
    pub initial_state: String,
    pub terminal_state: String,
    pub milestones: Vec<ArcMilestoneSeed>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ClimaxSeed {
    pub climax_id: String,
    pub volume_id: String,
    pub escalation_tier: u32,
    pub converging_arc_ids: Vec<String>,
    pub decisive_choice_or_action: String,
    pub irreversible_consequence: String,
    pub resulting_equilibrium: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FixedEndingSeed {
    pub central_question_answer: String,
    pub protagonist_final_choice: String,
    pub protagonist_final_state: String,
    pub world_final_state: String,
    pub final_cost: String,
    pub final_image: String,
    pub final_climax_id: String,
    pub resolved_arc_ids: Vec<String>,
    pub intentionally_open_arc_ids: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterCharmBeatSeed {
    pub volume_id: String,
    pub function: String,
    pub visible_behavior: String,
    pub cost_or_consequence: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterCharmArcSeed {
    pub character_id: String,
    pub core_appeal: String,
    pub central_contradiction: String,
    pub signature_modes: Vec<String>,
    pub vulnerability: String,
    pub terminal_transformation: String,
    pub beats: Vec<CharacterCharmBeatSeed>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct MacroCanonPolicy {
    pub mutable_scope: String,
    pub revision_requires_author_approval: bool,
    pub revision_requires_new_setup_fingerprint: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProgressionLadderSeed {
    pub ladder_id: String,
    pub name: String,
    pub stages: Vec<String>,
    pub allowed_movements: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RollingOutlinePolicy {
    pub committed_chapters: u32,
    pub planned_chapters: u32,
    pub directional_chapters: u32,
    pub refresh_after_accepted_chapters: u32,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CastEvolutionPolicy {
    pub initial_core_target_min: u32,
    pub initial_core_target_max: u32,
    pub active_volume_drivers_min: u32,
    pub active_volume_drivers_max: u32,
    pub promotion_rule: String,
    pub exit_rule: String,
    pub return_rule: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SelectiveContextPolicy {
    pub recent_chapter_limit: u32,
    pub evidence_axes: Vec<String>,
    pub context_manifest_required: bool,
    pub source_evidence_required: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct LongFormArchitecture {
    pub macro_parts: Vec<MacroPartSeed>,
    pub volumes: Vec<VolumeBlueprintSeed>,
    pub narrative_arcs: Vec<NarrativeArcSeed>,
    pub climax_chain: Vec<ClimaxSeed>,
    pub fixed_ending: FixedEndingSeed,
    pub character_charm_arcs: Vec<CharacterCharmArcSeed>,
    pub progression_ladders: Vec<ProgressionLadderSeed>,
    pub rolling_outline_policy: RollingOutlinePolicy,
    pub cast_evolution_policy: CastEvolutionPolicy,
    pub repetition_dimensions: Vec<String>,
    pub selective_context_policy: SelectiveContextPolicy,
    pub macro_canon_policy: MacroCanonPolicy,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BookStructureSeed {
    pub first_volume_title: String,
    pub first_unit_title: String,
    pub first_chapter_title: String,
    pub rolling_outline_chapters: u32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub minimum_total_characters: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub long_form: Option<LongFormArchitecture>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BookSetupArtifact {
    pub schema: String,
    pub project_id: String,
    pub book_id: String,
    pub book_plan: BookPlan,
    pub character_bibles: Vec<CharacterBible>,
    pub relationship_bibles: Vec<RelationshipBible>,
    pub world_seeds: Vec<WorldSeed>,
    pub structure: BookStructureSeed,
    pub source_evidence_refs: Vec<BookSetupSourceEvidence>,
    #[serde(default)]
    pub fingerprint: String,
}

/// Private pre-prose context for character and scene simulation. The BookPlan and
/// structure seed stay in the frozen planning chain; surface writers never receive
/// the psychological or relationship decision models directly.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BookSetupSimulationProjection {
    pub schema: String,
    pub setup_fingerprint: String,
    pub character_decision_models: Vec<CharacterBible>,
    pub relationship_decision_models: Vec<RelationshipBible>,
    pub pressure_bearing_world_seeds: Vec<WorldSeed>,
    pub private_pre_prose_context: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BookSetupProposalReceipt {
    pub setup_id: String,
    pub expected_setup_version: u64,
    pub expected_book_plan_version: u64,
    pub setup_fingerprint: String,
    pub request_fingerprint: String,
    pub replayed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BookSetupApprovalReceipt {
    pub setup_id: String,
    pub version: u64,
    pub setup_fingerprint: String,
    pub book_plan_id: String,
    pub book_plan_fingerprint: String,
    pub approval_fingerprint: String,
    pub replayed: bool,
}

impl BookSetupArtifact {
    pub fn seal(&mut self) -> CoreResult<()> {
        self.schema = BOOK_SETUP_SCHEMA.into();
        self.book_id = "BOOK".into();
        self.fingerprint.clear();
        self.validate_shape()?;
        self.fingerprint = setup_fingerprint(self)?;
        Ok(())
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_shape()?;
        let expected = setup_fingerprint(self)?;
        if self.fingerprint != expected {
            return Err(CoreError::AuthorityConflict(
                "book setup fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    pub fn simulation_projection(&self) -> CoreResult<BookSetupSimulationProjection> {
        self.validate()?;
        Ok(BookSetupSimulationProjection {
            schema: "quillframe_book_setup_simulation_projection_v1".into(),
            setup_fingerprint: self.fingerprint.clone(),
            character_decision_models: self.character_bibles.clone(),
            relationship_decision_models: self.relationship_bibles.clone(),
            pressure_bearing_world_seeds: self.world_seeds.clone(),
            private_pre_prose_context: true,
        })
    }

    fn validate_shape(&self) -> CoreResult<()> {
        if self.schema != BOOK_SETUP_SCHEMA || self.book_id != "BOOK" {
            return Err(CoreError::InvalidPlan(
                "book setup schema and book identity must be exact".into(),
            ));
        }
        require_text(&self.project_id, "project_id")?;
        if self.source_evidence_refs.is_empty() {
            return Err(CoreError::InvalidPlan(
                "book setup requires fingerprint-bound source evidence".into(),
            ));
        }
        let mut source_ids = BTreeSet::new();
        for source in &self.source_evidence_refs {
            for (field, value) in [
                ("source evidence id", &source.source_id),
                ("source evidence kind", &source.source_kind),
                ("source evidence uri", &source.source_uri),
                ("source evidence revision", &source.source_revision),
                ("source evidence role", &source.role),
            ] {
                require_text(value, field)?;
            }
            if !source_ids.insert(source.source_id.as_str()) {
                return Err(CoreError::InvalidPlan(
                    "book setup source evidence ids must be unique".into(),
                ));
            }
            require_fingerprint(&source.content_fingerprint, "source evidence content")?;
        }
        PlanBody::Book(self.book_plan.clone()).validate()?;
        if self.structure.rolling_outline_chapters == 0
            || self.structure.rolling_outline_chapters > 30
            || self.structure.minimum_total_characters == Some(0)
        {
            return Err(CoreError::InvalidPlan(
                "book setup requires a 1-30 chapter rolling horizon and a positive optional minimum scale"
                    .into(),
            ));
        }
        if self
            .structure
            .minimum_total_characters
            .is_some_and(|minimum| minimum >= 5_000_000)
        {
            if self.book_plan.fixed_ending_outcomes.is_empty() {
                return Err(CoreError::InvalidPlan(
                    "book setup at or above five million characters requires concrete fixed ending outcomes"
                        .into(),
                ));
            }
            require_text_list(
                &self.book_plan.fixed_ending_outcomes,
                "book fixed ending outcomes",
            )?;
            let architecture = self.structure.long_form.as_ref().ok_or_else(|| {
                CoreError::InvalidPlan(
                    "book setup at or above five million characters requires a typed long-form architecture"
                        .into(),
                )
            })?;
            validate_long_form_architecture(
                architecture,
                self.structure.rolling_outline_chapters,
                self.structure.minimum_total_characters.unwrap_or_default(),
            )?;
            if self.character_bibles.len()
                < architecture.cast_evolution_policy.initial_core_target_min as usize
            {
                return Err(CoreError::InvalidPlan(
                    "long-form setup must instantiate its declared minimum initial core cast"
                        .into(),
                ));
            }
        } else if let Some(architecture) = &self.structure.long_form {
            validate_long_form_architecture(
                architecture,
                self.structure.rolling_outline_chapters,
                self.structure.minimum_total_characters.unwrap_or(1),
            )?;
        }
        for (field, value) in [
            ("first_volume_title", &self.structure.first_volume_title),
            ("first_unit_title", &self.structure.first_unit_title),
            ("first_chapter_title", &self.structure.first_chapter_title),
        ] {
            require_text(value, field)?;
        }

        if self.character_bibles.is_empty() {
            return Err(CoreError::InvalidPlan(
                "book setup requires at least one character bible".into(),
            ));
        }
        let arc_ids = self
            .book_plan
            .character_arcs
            .iter()
            .map(|character| character.character_id.as_str())
            .collect::<BTreeSet<_>>();
        let mut character_ids = BTreeSet::new();
        for character in &self.character_bibles {
            for (field, value) in [
                ("character_id", &character.character_id),
                ("display_name", &character.display_name),
                ("story_function", &character.story_function),
                ("external_want", &character.external_want),
                ("private_need", &character.private_need),
                ("fear_or_shame", &character.fear_or_shame),
                ("false_belief", &character.false_belief),
                ("public_mask", &character.public_mask),
                ("default_strategy", &character.default_strategy),
                ("pressure_leak", &character.pressure_leak),
                ("defense_or_humor", &character.defense_or_humor),
                ("voice.baseline", &character.voice.baseline),
                ("voice.with_intimates", &character.voice.with_intimates),
                ("voice.with_authority", &character.voice.with_authority),
                ("voice.under_pressure", &character.voice.under_pressure),
            ] {
                require_text(value, field)?;
            }
            require_text_list(&character.values, "character values")?;
            require_text_list(&character.knowledge_boundaries, "knowledge boundaries")?;
            require_text_list(&character.non_negotiables, "character non-negotiables")?;
            require_text_list(&character.voice.avoids_saying, "voice avoids_saying")?;
            if !character_ids.insert(character.character_id.as_str()) {
                return Err(CoreError::InvalidPlan(
                    "book setup character ids must be unique".into(),
                ));
            }
        }
        if character_ids != arc_ids {
            return Err(CoreError::InvalidPlan(
                "character bibles must exactly cover the book-plan character arcs".into(),
            ));
        }
        if let Some(architecture) = &self.structure.long_form {
            validate_long_form_authority_bindings(architecture, &character_ids)?;
        }

        let arc_relationships = self
            .book_plan
            .relationship_arcs
            .iter()
            .map(|relationship| {
                (
                    relationship.relationship_id.as_str(),
                    relationship
                        .participant_ids
                        .iter()
                        .map(String::as_str)
                        .collect::<BTreeSet<_>>(),
                )
            })
            .collect::<BTreeMap<_, _>>();
        let mut relationship_ids = BTreeSet::new();
        for relationship in &self.relationship_bibles {
            for (field, value) in [
                ("relationship_id", &relationship.relationship_id),
                ("shared_history", &relationship.shared_history),
                ("current_surface", &relationship.current_surface),
                ("hidden_debt", &relationship.hidden_debt),
                ("power_balance", &relationship.power_balance),
                ("forbidden_topic", &relationship.forbidden_topic),
                ("default_pattern", &relationship.default_pattern),
            ] {
                require_text(value, field)?;
            }
            let participants = relationship
                .participant_ids
                .iter()
                .map(String::as_str)
                .collect::<BTreeSet<_>>();
            if relationship.participant_ids.len() != 2
                || participants.len() != 2
                || participants.iter().any(|id| !character_ids.contains(id))
                || relationship.participant_tactics.len() != 2
                || relationship.participant_tactics.iter().any(|(id, tactic)| {
                    !participants.contains(id.as_str()) || tactic.trim().is_empty()
                })
                || !relationship_ids.insert(relationship.relationship_id.as_str())
                || arc_relationships.get(relationship.relationship_id.as_str())
                    != Some(&participants)
            {
                return Err(CoreError::InvalidPlan(
                    "relationship bibles require a unique book-plan relationship and tactics for both known participants"
                        .into(),
                ));
            }
        }
        if relationship_ids != arc_relationships.keys().copied().collect::<BTreeSet<_>>() {
            return Err(CoreError::InvalidPlan(
                "relationship bibles must exactly cover the book-plan relationship arcs".into(),
            ));
        }

        if self.world_seeds.is_empty() {
            return Err(CoreError::InvalidPlan(
                "book setup requires at least one pressure-bearing world seed".into(),
            ));
        }
        let mut world_ids = BTreeSet::new();
        for seed in &self.world_seeds {
            for (field, value) in [
                ("world seed id", &seed.seed_id),
                ("world seed topic", &seed.topic),
                ("world seed rule", &seed.rule),
                ("world seed narrative pressure", &seed.narrative_pressure),
            ] {
                require_text(value, field)?;
            }
            if !world_ids.insert(seed.seed_id.as_str()) {
                return Err(CoreError::InvalidPlan(
                    "world seed ids must be unique".into(),
                ));
            }
            if !seed.unknowns.is_empty() {
                require_text_list(&seed.unknowns, "world seed unknowns")?;
            }
        }
        Ok(())
    }
}

fn validate_long_form_architecture(
    architecture: &LongFormArchitecture,
    rolling_horizon: u32,
    minimum_total_characters: u64,
) -> CoreResult<()> {
    if architecture.macro_parts.len() < 2 || architecture.volumes.len() < 2 {
        return Err(CoreError::InvalidPlan(
            "long-form architecture requires multiple macro parts and operating volumes".into(),
        ));
    }
    let mut part_ids = BTreeSet::new();
    let mut part_ordinals = BTreeMap::new();
    for (index, part) in architecture.macro_parts.iter().enumerate() {
        for (field, value) in [
            ("macro part id", &part.part_id),
            ("macro part title", &part.title),
            ("macro part story engine", &part.story_engine),
            ("macro part protagonist role", &part.protagonist_role),
            ("macro part entry state", &part.entry_state),
            ("macro part terminal state", &part.terminal_state),
            ("macro part terminal climax", &part.terminal_climax_id),
        ] {
            require_text(value, field)?;
        }
        if part.ordinal != index as u32 + 1
            || part.minimum_capacity_characters == 0
            || !part_ids.insert(part.part_id.as_str())
        {
            return Err(CoreError::InvalidPlan(
                "macro parts require contiguous ordinals, unique ids and positive capacity".into(),
            ));
        }
        part_ordinals.insert(part.part_id.as_str(), part.ordinal);
    }

    let mut volume_ids = BTreeSet::new();
    let mut volume_ordinals = BTreeMap::new();
    let mut volume_capacity_by_part = BTreeMap::<&str, u64>::new();
    let mut last_part_ordinal = 0_u32;
    let mut total_volume_capacity = 0_u64;
    for (index, volume) in architecture.volumes.iter().enumerate() {
        for (field, value) in [
            ("volume id", &volume.volume_id),
            ("volume title", &volume.title),
            ("volume time scope", &volume.time_scope),
            ("volume dramatic question", &volume.dramatic_question),
            ("volume entry state", &volume.entry_state),
            ("volume main plot", &volume.main_plot),
            ("volume climax id", &volume.climax_id),
            (
                "volume irreversible exit state",
                &volume.irreversible_exit_state,
            ),
            ("volume next handoff", &volume.next_volume_handoff),
        ] {
            require_text(value, field)?;
        }
        let part_ordinal = part_ordinals
            .get(volume.macro_part_id.as_str())
            .copied()
            .ok_or_else(|| {
                CoreError::InvalidPlan("every volume must belong to a known macro part".into())
            })?;
        if volume.ordinal != index as u32 + 1
            || volume.minimum_capacity_characters == 0
            || !volume_ids.insert(volume.volume_id.as_str())
            || part_ordinal < last_part_ordinal
        {
            return Err(CoreError::InvalidPlan(
                "volumes require contiguous ordinals, unique ids, positive capacity and contiguous macro-part coverage"
                    .into(),
            ));
        }
        last_part_ordinal = part_ordinal;
        require_text_list(&volume.active_arc_ids, "volume active arcs")?;
        if volume.major_turns.len() < 5 {
            return Err(CoreError::InvalidPlan(
                "every volume requires a concrete opening, reversal, crisis, climax and aftermath"
                    .into(),
            ));
        }
        let mut turn_ids = BTreeSet::new();
        let mut phases = BTreeSet::new();
        for turn in &volume.major_turns {
            for (field, value) in [
                ("volume turn id", &turn.turn_id),
                ("volume turn phase", &turn.phase),
                ("volume turn event", &turn.event),
                ("volume turn consequence", &turn.consequence),
            ] {
                require_text(value, field)?;
            }
            if !turn_ids.insert(turn.turn_id.as_str())
                || !matches!(
                    turn.phase.as_str(),
                    "opening" | "escalation" | "reversal" | "crisis" | "climax" | "aftermath"
                )
            {
                return Err(CoreError::InvalidPlan(
                    "volume turns require unique ids and known dramatic phases".into(),
                ));
            }
            phases.insert(turn.phase.as_str());
            require_text_list(&turn.advanced_arc_ids, "volume turn advanced arcs")?;
        }
        if ["opening", "reversal", "crisis", "climax", "aftermath"]
            .iter()
            .any(|phase| !phases.contains(phase))
        {
            return Err(CoreError::InvalidPlan(
                "every volume must contain the required dramatic turn phases".into(),
            ));
        }
        volume_ordinals.insert(volume.volume_id.as_str(), volume.ordinal);
        let part_capacity = volume_capacity_by_part
            .entry(volume.macro_part_id.as_str())
            .or_default();
        *part_capacity = part_capacity
            .checked_add(volume.minimum_capacity_characters)
            .ok_or_else(|| CoreError::InvalidPlan("long-form capacity overflow".into()))?;
        total_volume_capacity = total_volume_capacity
            .checked_add(volume.minimum_capacity_characters)
            .ok_or_else(|| CoreError::InvalidPlan("long-form capacity overflow".into()))?;
    }
    if total_volume_capacity < minimum_total_characters
        || architecture.macro_parts.iter().any(|part| {
            volume_capacity_by_part.get(part.part_id.as_str()).copied()
                != Some(part.minimum_capacity_characters)
        })
    {
        return Err(CoreError::InvalidPlan(
            "explicit volume capacity must cover the declared scale and exactly roll up to every macro part"
                .into(),
        ));
    }

    let mut arc_ids = BTreeSet::new();
    for arc in &architecture.narrative_arcs {
        for (field, value) in [
            ("narrative arc id", &arc.arc_id),
            ("narrative arc title", &arc.title),
            ("narrative arc initial state", &arc.initial_state),
            ("narrative arc terminal state", &arc.terminal_state),
        ] {
            require_text(value, field)?;
        }
        if !arc_ids.insert(arc.arc_id.as_str()) || arc.milestones.is_empty() {
            return Err(CoreError::InvalidPlan(
                "narrative arcs require unique ids and fixed volume milestones".into(),
            ));
        }
        let mut previous_volume = 0_u32;
        let mut milestone_volumes = BTreeSet::new();
        for milestone in &arc.milestones {
            require_text(&milestone.change, "narrative arc milestone change")?;
            require_text(
                &milestone.consequence,
                "narrative arc milestone consequence",
            )?;
            let ordinal = volume_ordinals
                .get(milestone.volume_id.as_str())
                .copied()
                .ok_or_else(|| {
                    CoreError::InvalidPlan(
                        "narrative arc milestones must reference known volumes".into(),
                    )
                })?;
            if ordinal <= previous_volume || !milestone_volumes.insert(milestone.volume_id.as_str())
            {
                return Err(CoreError::InvalidPlan(
                    "narrative arc milestones must follow strict volume order".into(),
                ));
            }
            previous_volume = ordinal;
        }
    }
    if architecture.narrative_arcs.len() < 3
        || !architecture
            .narrative_arcs
            .iter()
            .any(|arc| matches!(arc.kind, NarrativeArcKind::MainPlot))
        || !architecture.narrative_arcs.iter().any(|arc| {
            matches!(
                arc.kind,
                NarrativeArcKind::Relationship | NarrativeArcKind::Romance
            )
        })
    {
        return Err(CoreError::InvalidPlan(
            "long-form setup requires multiple fixed arcs including a main plot and a relationship arc"
                .into(),
        ));
    }
    for volume in &architecture.volumes {
        if volume
            .active_arc_ids
            .iter()
            .any(|id| !arc_ids.contains(id.as_str()))
            || volume.major_turns.iter().any(|turn| {
                turn.advanced_arc_ids
                    .iter()
                    .any(|id| !arc_ids.contains(id.as_str()))
            })
        {
            return Err(CoreError::InvalidPlan(
                "volume plans and turns may advance only known narrative arcs".into(),
            ));
        }
    }

    let mut climax_ids = BTreeSet::new();
    let mut climax_volume_ids = BTreeSet::new();
    for climax in &architecture.climax_chain {
        for (field, value) in [
            ("climax id", &climax.climax_id),
            ("climax decisive action", &climax.decisive_choice_or_action),
            ("climax consequence", &climax.irreversible_consequence),
            (
                "climax resulting equilibrium",
                &climax.resulting_equilibrium,
            ),
        ] {
            require_text(value, field)?;
        }
        if climax.escalation_tier == 0
            || !volume_ids.contains(climax.volume_id.as_str())
            || !climax_ids.insert(climax.climax_id.as_str())
            || !climax_volume_ids.insert(climax.volume_id.as_str())
        {
            return Err(CoreError::InvalidPlan(
                "the climax chain requires one unique typed climax for every known volume".into(),
            ));
        }
        require_text_list(&climax.converging_arc_ids, "climax converging arcs")?;
        if climax
            .converging_arc_ids
            .iter()
            .any(|id| !arc_ids.contains(id.as_str()))
        {
            return Err(CoreError::InvalidPlan(
                "climaxes may converge only known narrative arcs".into(),
            ));
        }
    }
    if climax_volume_ids != volume_ids
        || architecture.volumes.iter().any(|volume| {
            !climax_ids.contains(volume.climax_id.as_str())
                || !architecture.climax_chain.iter().any(|climax| {
                    climax.climax_id == volume.climax_id && climax.volume_id == volume.volume_id
                })
        })
        || architecture.macro_parts.iter().any(|part| {
            !climax_ids.contains(part.terminal_climax_id.as_str())
                || !architecture.volumes.iter().any(|volume| {
                    volume.macro_part_id == part.part_id
                        && volume.climax_id == part.terminal_climax_id
                })
        })
    {
        return Err(CoreError::InvalidPlan(
            "volume and macro-part terminal climaxes must bind exactly into the full climax chain"
                .into(),
        ));
    }

    let ending = &architecture.fixed_ending;
    for (field, value) in [
        ("ending central answer", &ending.central_question_answer),
        (
            "ending protagonist choice",
            &ending.protagonist_final_choice,
        ),
        ("ending protagonist state", &ending.protagonist_final_state),
        ("ending world state", &ending.world_final_state),
        ("ending cost", &ending.final_cost),
        ("ending image", &ending.final_image),
        ("ending final climax", &ending.final_climax_id),
    ] {
        require_text(value, field)?;
    }
    let resolved = ending
        .resolved_arc_ids
        .iter()
        .map(String::as_str)
        .collect::<BTreeSet<_>>();
    let open = ending
        .intentionally_open_arc_ids
        .iter()
        .map(String::as_str)
        .collect::<BTreeSet<_>>();
    if resolved.len() != ending.resolved_arc_ids.len()
        || open.len() != ending.intentionally_open_arc_ids.len()
        || !resolved.is_disjoint(&open)
        || resolved.union(&open).copied().collect::<BTreeSet<_>>() != arc_ids
        || ending.final_climax_id
            != architecture
                .volumes
                .last()
                .map(|volume| volume.climax_id.as_str())
                .unwrap_or_default()
    {
        return Err(CoreError::InvalidPlan(
            "the fixed ending must bind the final climax and account for every narrative arc"
                .into(),
        ));
    }

    let mut charm_character_ids = BTreeSet::new();
    for charm in &architecture.character_charm_arcs {
        for (field, value) in [
            ("charm character id", &charm.character_id),
            ("charm core appeal", &charm.core_appeal),
            ("charm central contradiction", &charm.central_contradiction),
            ("charm vulnerability", &charm.vulnerability),
            (
                "charm terminal transformation",
                &charm.terminal_transformation,
            ),
        ] {
            require_text(value, field)?;
        }
        require_text_list(&charm.signature_modes, "character charm signature modes")?;
        if !charm_character_ids.insert(charm.character_id.as_str()) || charm.beats.len() < 3 {
            return Err(CoreError::InvalidPlan(
                "character charm arcs require unique characters and at least three fixed beats"
                    .into(),
            ));
        }
        let mut functions = BTreeSet::new();
        for beat in &charm.beats {
            for (field, value) in [
                ("charm beat function", &beat.function),
                ("charm beat visible behavior", &beat.visible_behavior),
                ("charm beat consequence", &beat.cost_or_consequence),
            ] {
                require_text(value, field)?;
            }
            if !volume_ids.contains(beat.volume_id.as_str()) {
                return Err(CoreError::InvalidPlan(
                    "character charm beats must reference known volumes".into(),
                ));
            }
            functions.insert(beat.function.as_str());
        }
        if ["showcase", "vulnerability", "payoff"]
            .iter()
            .any(|function| !functions.contains(function))
        {
            return Err(CoreError::InvalidPlan(
                "character charm arcs must show appeal, vulnerability and payoff".into(),
            ));
        }
    }

    let policy = &architecture.macro_canon_policy;
    if policy.mutable_scope != "chapter_execution_only"
        || !policy.revision_requires_author_approval
        || !policy.revision_requires_new_setup_fingerprint
    {
        return Err(CoreError::InvalidPlan(
            "book and volume canon must be fixed; only chapter execution may roll without a new author-approved setup fingerprint"
                .into(),
        ));
    }

    let mut ladder_ids = BTreeSet::new();
    for ladder in &architecture.progression_ladders {
        require_text(&ladder.ladder_id, "progression ladder id")?;
        require_text(&ladder.name, "progression ladder name")?;
        require_text_list(&ladder.stages, "progression ladder stages")?;
        require_text_list(&ladder.allowed_movements, "progression ladder movements")?;
        if ladder.stages.len() < 2 || !ladder_ids.insert(ladder.ladder_id.as_str()) {
            return Err(CoreError::InvalidPlan(
                "progression ladders require unique ids and at least two stages".into(),
            ));
        }
    }
    if architecture.progression_ladders.len() < 2 {
        return Err(CoreError::InvalidPlan(
            "long-form architecture requires multiple independent progression ladders".into(),
        ));
    }

    let rolling = &architecture.rolling_outline_policy;
    if rolling.committed_chapters == 0
        || rolling.planned_chapters == 0
        || rolling.directional_chapters == 0
        || rolling
            .committed_chapters
            .checked_add(rolling.planned_chapters)
            .and_then(|value| value.checked_add(rolling.directional_chapters))
            != Some(rolling_horizon)
        || rolling.refresh_after_accepted_chapters == 0
        || rolling.refresh_after_accepted_chapters >= rolling_horizon
    {
        return Err(CoreError::InvalidPlan(
            "rolling outline zones must be non-empty, cover the horizon and refresh before exhaustion"
                .into(),
        ));
    }

    let cast = &architecture.cast_evolution_policy;
    if cast.initial_core_target_min == 0
        || cast.initial_core_target_min > cast.initial_core_target_max
        || cast.active_volume_drivers_min == 0
        || cast.active_volume_drivers_min > cast.active_volume_drivers_max
    {
        return Err(CoreError::InvalidPlan(
            "cast evolution ranges must be positive and ordered".into(),
        ));
    }
    for (field, value) in [
        ("cast promotion rule", &cast.promotion_rule),
        ("cast exit rule", &cast.exit_rule),
        ("cast return rule", &cast.return_rule),
    ] {
        require_text(value, field)?;
    }

    if architecture.repetition_dimensions.len() < 8 {
        return Err(CoreError::InvalidPlan(
            "long-form repetition ledger requires at least eight semantic dimensions".into(),
        ));
    }
    require_text_list(&architecture.repetition_dimensions, "repetition dimensions")?;
    if architecture
        .repetition_dimensions
        .iter()
        .collect::<BTreeSet<_>>()
        .len()
        != architecture.repetition_dimensions.len()
    {
        return Err(CoreError::InvalidPlan(
            "long-form repetition dimensions must be unique".into(),
        ));
    }

    let context = &architecture.selective_context_policy;
    if context.recent_chapter_limit == 0
        || context.recent_chapter_limit > rolling_horizon
        || !context.context_manifest_required
        || !context.source_evidence_required
    {
        return Err(CoreError::InvalidPlan(
            "long-form context must be selective, manifest-bound and source-evidenced".into(),
        ));
    }
    require_text_list(&context.evidence_axes, "selective context evidence axes")?;
    Ok(())
}

fn validate_long_form_authority_bindings(
    architecture: &LongFormArchitecture,
    character_ids: &BTreeSet<&str>,
) -> CoreResult<()> {
    for arc in &architecture.narrative_arcs {
        if arc
            .participant_ids
            .iter()
            .any(|id| !character_ids.contains(id.as_str()))
        {
            return Err(CoreError::InvalidPlan(
                "narrative arc participants must reference setup character bibles".into(),
            ));
        }
    }
    let charm_ids = architecture
        .character_charm_arcs
        .iter()
        .map(|arc| arc.character_id.as_str())
        .collect::<BTreeSet<_>>();
    if &charm_ids != character_ids {
        return Err(CoreError::InvalidPlan(
            "character charm arcs must exactly cover the setup core cast".into(),
        ));
    }
    Ok(())
}

fn setup_fingerprint(value: &BookSetupArtifact) -> CoreResult<String> {
    let mut canonical = value.clone();
    canonical.fingerprint.clear();
    serde_json::to_vec(&canonical)
        .map(sha256_fingerprint)
        .map_err(|error| CoreError::Serialization(error.to_string()))
}

fn require_text(value: &str, field: &str) -> CoreResult<()> {
    if value.trim().is_empty() || value != value.trim() {
        return Err(CoreError::InvalidPlan(format!(
            "book setup {field} must be non-empty and trimmed"
        )));
    }
    Ok(())
}

fn require_text_list(values: &[String], field: &str) -> CoreResult<()> {
    if values.is_empty()
        || values
            .iter()
            .any(|value| value.trim().is_empty() || value != value.trim())
    {
        return Err(CoreError::InvalidPlan(format!(
            "book setup {field} must contain trimmed text"
        )));
    }
    Ok(())
}

fn require_fingerprint(value: &str, field: &str) -> CoreResult<()> {
    if value.len() != 71
        || !value.starts_with("sha256:")
        || !value[7..]
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(CoreError::InvalidPlan(format!(
            "book setup {field} fingerprint must be canonical sha256"
        )));
    }
    Ok(())
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::{CharacterArcPlan, StoryFoundation};

    fn long_form_architecture() -> LongFormArchitecture {
        LongFormArchitecture {
            macro_parts: vec![
                MacroPartSeed {
                    part_id: "PART-01".into(),
                    ordinal: 1,
                    title: "逃亡".into(),
                    story_engine: "生存与互信".into(),
                    protagonist_role: "亲自行动者".into(),
                    entry_state: "主角只信自己".into(),
                    terminal_state: "主角建立第一个互信小组".into(),
                    terminal_climax_id: "CLIMAX-01".into(),
                    minimum_capacity_characters: 2_500_000,
                },
                MacroPartSeed {
                    part_id: "PART-02".into(),
                    ordinal: 2,
                    title: "改写规则".into(),
                    story_engine: "组织与制度对抗".into(),
                    protagonist_role: "组织者".into(),
                    entry_state: "互信小组遭到制度封锁".into(),
                    terminal_state: "公开契约并建立可审计的新规则".into(),
                    terminal_climax_id: "CLIMAX-02".into(),
                    minimum_capacity_characters: 2_500_000,
                },
            ],
            volumes: vec![
                VolumeBlueprintSeed {
                    volume_id: "VOL-01".into(),
                    ordinal: 1,
                    macro_part_id: "PART-01".into(),
                    title: "逃出封锁".into(),
                    time_scope: "第一阶段".into(),
                    dramatic_question: "主角能否带证人活着离开".into(),
                    entry_state: "主角独自逃亡".into(),
                    main_plot: "主角与证人从互相利用走到共同破局".into(),
                    major_turns: fixture_turns("VOL-01", "ARC-MAIN"),
                    active_arc_ids: vec!["ARC-MAIN".into(), "ARC-TRUST".into()],
                    climax_id: "CLIMAX-01".into(),
                    irreversible_exit_state: "主角公开选择保护证人并失去独自脱身机会".into(),
                    next_volume_handoff: "共同体必须面对制造封锁的制度".into(),
                    minimum_capacity_characters: 2_500_000,
                },
                VolumeBlueprintSeed {
                    volume_id: "VOL-02".into(),
                    ordinal: 2,
                    macro_part_id: "PART-02".into(),
                    title: "改写契约".into(),
                    time_scope: "第二阶段".into(),
                    dramatic_question: "共同体能否公开真相并改变规则".into(),
                    entry_state: "小组遭到制度追杀".into(),
                    main_plot: "主角组织证据与盟友完成公开制度对决".into(),
                    major_turns: fixture_turns("VOL-02", "ARC-MAIN"),
                    active_arc_ids: vec![
                        "ARC-MAIN".into(),
                        "ARC-TRUST".into(),
                        "ARC-IDENTITY".into(),
                    ],
                    climax_id: "CLIMAX-02".into(),
                    irreversible_exit_state: "旧契约被公开废除，主角接受新规则同样约束自己".into(),
                    next_volume_handoff: "全书终局".into(),
                    minimum_capacity_characters: 2_500_000,
                },
            ],
            narrative_arcs: vec![
                NarrativeArcSeed {
                    arc_id: "ARC-MAIN".into(),
                    kind: NarrativeArcKind::MainPlot,
                    title: "逃亡到改写规则".into(),
                    participant_ids: vec!["CHAR-LEAD".into()],
                    initial_state: "主角被旧契约追捕".into(),
                    terminal_state: "主角公开废除旧契约并接受新约束".into(),
                    milestones: vec![
                        ArcMilestoneSeed {
                            volume_id: "VOL-01".into(),
                            change: "从独自逃亡到建立小组".into(),
                            consequence: "失去独自脱身机会".into(),
                        },
                        ArcMilestoneSeed {
                            volume_id: "VOL-02".into(),
                            change: "从躲避规则到公开改写规则".into(),
                            consequence: "新规则也约束主角".into(),
                        },
                    ],
                },
                NarrativeArcSeed {
                    arc_id: "ARC-TRUST".into(),
                    kind: NarrativeArcKind::Relationship,
                    title: "信任与共同承担".into(),
                    participant_ids: vec!["CHAR-LEAD".into()],
                    initial_state: "主角拒绝依靠他人".into(),
                    terminal_state: "主角愿意公开分权并共同承担".into(),
                    milestones: vec![
                        ArcMilestoneSeed {
                            volume_id: "VOL-01".into(),
                            change: "主角返身救人".into(),
                            consequence: "双方形成有限互信".into(),
                        },
                        ArcMilestoneSeed {
                            volume_id: "VOL-02".into(),
                            change: "主角交出决定性证据的共同保管权".into(),
                            consequence: "关系不再依赖单方控制".into(),
                        },
                    ],
                },
                NarrativeArcSeed {
                    arc_id: "ARC-IDENTITY".into(),
                    kind: NarrativeArcKind::Character,
                    title: "身份与选择权".into(),
                    participant_ids: vec!["CHAR-LEAD".into()],
                    initial_state: "身份由旧契约定义".into(),
                    terminal_state: "身份由公开选择与责任定义".into(),
                    milestones: vec![ArcMilestoneSeed {
                        volume_id: "VOL-02".into(),
                        change: "主角公开真实身份".into(),
                        consequence: "夺回选择权同时承担法律后果".into(),
                    }],
                },
            ],
            climax_chain: vec![
                ClimaxSeed {
                    climax_id: "CLIMAX-01".into(),
                    volume_id: "VOL-01".into(),
                    escalation_tier: 1,
                    converging_arc_ids: vec!["ARC-MAIN".into(), "ARC-TRUST".into()],
                    decisive_choice_or_action: "主角放弃独自出口并返身救证人".into(),
                    irreversible_consequence: "追捕者确认两人结盟".into(),
                    resulting_equilibrium: "互信小组成形并进入制度战".into(),
                },
                ClimaxSeed {
                    climax_id: "CLIMAX-02".into(),
                    volume_id: "VOL-02".into(),
                    escalation_tier: 2,
                    converging_arc_ids: vec![
                        "ARC-MAIN".into(),
                        "ARC-TRUST".into(),
                        "ARC-IDENTITY".into(),
                    ],
                    decisive_choice_or_action: "主角公开身份、契约证据与共同治理方案".into(),
                    irreversible_consequence: "主角失去秘密后手并接受公开审判".into(),
                    resulting_equilibrium: "旧契约废止，新规则可审计且同样约束主角".into(),
                },
            ],
            fixed_ending: FixedEndingSeed {
                central_question_answer: "选择权只有与公开责任和共同约束绑定时才成立".into(),
                protagonist_final_choice: "公开身份和证据，放弃独占控制".into(),
                protagonist_final_state: "成为受共同规则约束的制度设计者".into(),
                world_final_state: "旧契约废止，新规则进入公开执行".into(),
                final_cost: "主角失去秘密身份、独占证据和单方决定权".into(),
                final_image: "主角在公开会议上与昔日证人并排签署新契约".into(),
                final_climax_id: "CLIMAX-02".into(),
                resolved_arc_ids: vec![
                    "ARC-MAIN".into(),
                    "ARC-TRUST".into(),
                    "ARC-IDENTITY".into(),
                ],
                intentionally_open_arc_ids: Vec::new(),
            },
            character_charm_arcs: vec![CharacterCharmArcSeed {
                character_id: "CHAR-LEAD".into(),
                core_appeal: "能拆解困局并亲自承担".into(),
                central_contradiction: "善于解决问题却害怕依靠他人".into(),
                signature_modes: vec!["把混乱变成可执行选择".into(), "用冷笑话掩饰担心".into()],
                vulnerability: "再次判断错人会失去重要关系".into(),
                terminal_transformation: "从独占控制到公开分权".into(),
                beats: vec![
                    CharacterCharmBeatSeed {
                        volume_id: "VOL-01".into(),
                        function: "showcase".into(),
                        visible_behavior: "在封锁中拆出可执行逃生链".into(),
                        cost_or_consequence: "暴露自己的能力".into(),
                    },
                    CharacterCharmBeatSeed {
                        volume_id: "VOL-01".into(),
                        function: "vulnerability".into(),
                        visible_behavior: "因不敢信任险些失去证人".into(),
                        cost_or_consequence: "独行方案失败".into(),
                    },
                    CharacterCharmBeatSeed {
                        volume_id: "VOL-02".into(),
                        function: "payoff".into(),
                        visible_behavior: "主动交出共同保管权并公开承担".into(),
                        cost_or_consequence: "失去最后的秘密后手".into(),
                    },
                ],
            }],
            progression_ladders: vec![
                ProgressionLadderSeed {
                    ladder_id: "LADDER-POWER".into(),
                    name: "行动权限".into(),
                    stages: vec!["个人".into(), "组织".into()],
                    allowed_movements: vec!["获得".into(), "失去".into()],
                },
                ProgressionLadderSeed {
                    ladder_id: "LADDER-TRUST".into(),
                    name: "关系信任".into(),
                    stages: vec!["试探".into(), "共担".into()],
                    allowed_movements: vec!["维持".into(), "重新定价".into()],
                },
            ],
            rolling_outline_policy: RollingOutlinePolicy {
                committed_chapters: 3,
                planned_chapters: 4,
                directional_chapters: 3,
                refresh_after_accepted_chapters: 7,
            },
            cast_evolution_policy: CastEvolutionPolicy {
                initial_core_target_min: 1,
                initial_core_target_max: 9,
                active_volume_drivers_min: 4,
                active_volume_drivers_max: 12,
                promotion_rule: "能独立改变后文才升级为长期角色".into(),
                exit_rule: "退场必须留下可见去向".into(),
                return_rule: "回归必须带来离屏变化".into(),
            },
            repetition_dimensions: vec![
                "问题领域".into(),
                "对抗类型".into(),
                "主角角色".into(),
                "解决策略".into(),
                "核心收益".into(),
                "情绪温度".into(),
                "关系变化".into(),
                "场景空间".into(),
            ],
            selective_context_policy: SelectiveContextPolicy {
                recent_chapter_limit: 4,
                evidence_axes: vec!["实体".into(), "时间".into(), "因果".into(), "语义".into()],
                context_manifest_required: true,
                source_evidence_required: true,
            },
            macro_canon_policy: MacroCanonPolicy {
                mutable_scope: "chapter_execution_only".into(),
                revision_requires_author_approval: true,
                revision_requires_new_setup_fingerprint: true,
            },
        }
    }

    fn fixture_turns(volume_id: &str, arc_id: &str) -> Vec<VolumeTurnSeed> {
        ["opening", "reversal", "crisis", "climax", "aftermath"]
            .into_iter()
            .enumerate()
            .map(|(index, phase)| VolumeTurnSeed {
                turn_id: format!("{volume_id}-TURN-{}", index + 1),
                phase: phase.into(),
                event: format!("{phase} event"),
                consequence: format!("{phase} consequence"),
                advanced_arc_ids: vec![arc_id.into()],
            })
            .collect()
    }

    pub(crate) fn artifact() -> BookSetupArtifact {
        BookSetupArtifact {
            schema: BOOK_SETUP_SCHEMA.into(),
            project_id: "BOOK".into(),
            book_id: "BOOK".into(),
            book_plan: BookPlan {
                foundation: StoryFoundation {
                    target_readers: "长篇悬疑读者".into(),
                    genre_promise: "人物选择持续改变谜局".into(),
                    core_emotion: "互不信任中的被迫合作".into(),
                    progression_fantasy: "从逃亡者变成规则改写者".into(),
                    payoff_cadence: "每个单元偿还一个选择债".into(),
                    premise: "被追捕者必须保护唯一证人".into(),
                    intended_end_state: "主角夺回身份与选择权".into(),
                    differentiators: vec!["关系试探推动破案".into()],
                    non_negotiables: vec!["主角保有因果权".into()],
                },
                character_arcs: vec![CharacterArcPlan {
                    character_id: "CHAR-LEAD".into(),
                    display_name: "林昼".into(),
                    narrative_role: "主动破局者".into(),
                    external_want: "带证人离开封锁区".into(),
                    internal_need: "接受信任必然带来风险".into(),
                    pressure: "追捕和旧背叛".into(),
                    agency: "关键转向由他选择".into(),
                    initial_state: "只信自己".into(),
                    intended_change: "学会共同承担".into(),
                    turning_points: vec!["返身救人".into()],
                }],
                relationship_arcs: Vec::new(),
                reader_promise: "主角靠选择而不是好运破局".into(),
                protagonist_agency: "主动判断并承担结果".into(),
                central_conflict: "保护证人与自保冲突".into(),
                progression: vec!["逃亡者到破局者".into()],
                endgame_reserve: vec!["契约真相".into()],
                fixed_ending_outcomes: vec![
                    "主角公开身份并废止旧契约".into(),
                    "新规则同样约束主角".into(),
                ],
                anti_exhaustion_limits: vec!["不提前揭示终局".into()],
            },
            character_bibles: vec![CharacterBible {
                character_id: "CHAR-LEAD".into(),
                display_name: "林昼".into(),
                story_function: "主动破局者".into(),
                external_want: "带证人离开封锁区".into(),
                private_need: "承认自己需要同伴".into(),
                fear_or_shame: "害怕再次判断错人".into(),
                false_belief: "独自行动就不会失去谁".into(),
                values: vec!["选择权".into()],
                public_mask: "把担心说成流程问题".into(),
                default_strategy: "先给小承诺测试对方".into(),
                pressure_leak: "越害怕越反复检查出口".into(),
                defense_or_humor: "用实用主义冷笑话维持体面".into(),
                voice: CharacterVoiceProfile {
                    baseline: "短句，先谈眼前麻烦".into(),
                    with_intimates: "用旧梗打岔".into(),
                    with_authority: "礼貌追问执行细节".into(),
                    under_pressure: "省略主语并直接下命令".into(),
                    avoids_saying: vec!["我需要你".into()],
                },
                knowledge_boundaries: vec!["不知道契约持有人".into()],
                non_negotiables: vec!["不拿同伴作诱饵".into()],
            }],
            relationship_bibles: Vec::new(),
            world_seeds: vec![WorldSeed {
                seed_id: "WORLD-CONTRACT".into(),
                topic: "身份契约".into(),
                rule: "公开签署的身份契约会同步约束签署者".into(),
                narrative_pressure: "主角不能只让对手承担新规则的代价".into(),
                unknowns: vec!["旧契约的最终持有人尚未确认".into()],
            }],
            structure: BookStructureSeed {
                first_volume_title: "封锁线".into(),
                first_unit_title: "雨城".into(),
                first_chapter_title: "雨巷死者".into(),
                rolling_outline_chapters: 10,
                minimum_total_characters: Some(5_000_000),
                long_form: Some(long_form_architecture()),
            },
            source_evidence_refs: vec![BookSetupSourceEvidence {
                source_id: "SOURCE-BRIEF".into(),
                source_kind: "author_brief".into(),
                source_uri: "project:briefs/opening.md".into(),
                source_revision: "commit:0123456789abcdef".into(),
                content_fingerprint:
                    "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef".into(),
                role: "Primary setup evidence".into(),
            }],
            fingerprint: String::new(),
        }
    }

    #[test]
    fn setup_is_a_fingerprint_bound_character_decision_contract() {
        let mut value = artifact();
        value.seal().unwrap();
        value.validate().unwrap();

        value.character_bibles[0].fear_or_shame = "".into();
        assert!(value.validate().is_err());
    }

    #[test]
    fn setup_has_a_minimum_scale_but_no_maximum_length_field() {
        let mut value = artifact();
        value.structure.minimum_total_characters = Some(5_000_000);
        value.seal().unwrap();
        let json = serde_json::to_value(value).unwrap();
        assert_eq!(
            json.pointer("/structure/minimum_total_characters"),
            Some(&serde_json::json!(5_000_000))
        );
        assert!(json
            .pointer("/structure/maximum_total_characters")
            .is_none());
    }

    #[test]
    fn five_million_character_setup_requires_a_capacity_architecture() {
        let mut value = artifact();
        value.structure.long_form = None;
        assert!(value.seal().is_err());

        let mut value = artifact();
        value.structure.long_form.as_mut().unwrap().macro_parts[0].minimum_capacity_characters = 1;
        assert!(value.seal().is_err());
    }

    #[test]
    fn setup_requires_a_pressure_bearing_world_seed() {
        let mut value = artifact();
        value.world_seeds.clear();
        assert!(value.seal().is_err());
    }

    #[test]
    fn ultralong_setup_requires_concrete_volume_spines_and_a_fixed_ending() {
        let mut value = artifact();
        value.structure.long_form.as_mut().unwrap().volumes.clear();
        assert!(value.seal().is_err());

        let mut value = artifact();
        value
            .structure
            .long_form
            .as_mut()
            .unwrap()
            .fixed_ending
            .protagonist_final_choice
            .clear();
        assert!(value.seal().is_err());
    }

    #[test]
    fn ultralong_macro_canon_changes_require_new_author_approval() {
        let mut value = artifact();
        value
            .structure
            .long_form
            .as_mut()
            .unwrap()
            .macro_canon_policy
            .revision_requires_author_approval = false;
        assert!(value.seal().is_err());
    }

    #[test]
    fn simulation_projection_exposes_decision_models_without_structure_or_book_plan() {
        let mut value = artifact();
        value.seal().unwrap();
        let projection = serde_json::to_value(value.simulation_projection().unwrap()).unwrap();
        assert_eq!(
            projection
                .pointer("/character_decision_models/0/display_name")
                .and_then(serde_json::Value::as_str),
            Some("林昼")
        );
        assert_eq!(
            projection
                .get("private_pre_prose_context")
                .and_then(serde_json::Value::as_bool),
            Some(true)
        );
        assert!(projection.get("book_plan").is_none());
        assert!(projection.get("structure").is_none());
        assert!(projection.get("source_evidence_refs").is_none());
    }

    #[test]
    fn setup_fingerprint_binds_exact_source_evidence() {
        let mut value = artifact();
        value.seal().unwrap();
        let original = value.fingerprint.clone();

        value.source_evidence_refs[0].source_revision = "commit:changed".into();
        assert!(value.validate().is_err());
        value.seal().unwrap();
        assert_ne!(value.fingerprint, original);
    }
}
