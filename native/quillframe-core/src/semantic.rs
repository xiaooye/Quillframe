use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::{
    fingerprint::sha256_fingerprint, CoreError, CoreResult, FindingCategory, ReviewFinding,
    SceneWritingBrief, Severity,
};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterAction {
    pub scene_id: String,
    pub character: String,
    pub action: String,
    pub motive_pressure: String,
    pub observable_consequence: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterSimulation {
    pub actions: Vec<CharacterAction>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ResolvedScene {
    pub scene_id: String,
    pub action_sequence: Vec<String>,
    pub turn: String,
    pub exit_state: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SceneResolution {
    pub scenes: Vec<ResolvedScene>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DirectorNote {
    pub schema: String,
    pub chapter_id: String,
    pub scene: ResolvedScene,
    pub source_receipts: BTreeMap<String, String>,
    pub private_reasoning_exposed: bool,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SurfaceRealization {
    pub manuscript: String,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SurfaceRuleStatus {
    Pass,
    Fail,
    NotApplicable,
    InsufficientEvidence,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SurfaceRuleAssessment {
    pub rule_id: String,
    pub status: SurfaceRuleStatus,
    pub evidence_excerpt: Option<String>,
    pub report: String,
    pub repair_scope: Option<String>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SurfaceAuditDecision {
    Accept,
    Revise,
    InsufficientEvidence,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SurfaceHardRuleAudit {
    pub candidate_fingerprint: String,
    pub guidance_snapshot_fingerprint: String,
    pub rule_set_fingerprint: String,
    pub decision: SurfaceAuditDecision,
    pub assessments: Vec<SurfaceRuleAssessment>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NarrativeEntityKind {
    Character,
    World,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NarrativeEntityDelta {
    pub entity_kind: NarrativeEntityKind,
    pub entity_id: String,
    pub display_name: String,
    pub state: Value,
    pub evidence_excerpt: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RelationshipStateDelta {
    pub relationship_id: String,
    pub participant_a: String,
    pub participant_b: String,
    pub relationship_type: String,
    pub state: Value,
    pub evidence_excerpt: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterKnowledgeDelta {
    pub knowledge_id: String,
    pub character_id: String,
    pub fact: Value,
    pub confidence: String,
    pub evidence_excerpt: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TimelineEventDelta {
    pub event_id: String,
    pub title: String,
    pub description: String,
    pub evidence_excerpt: String,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ExpectationDeltaAction {
    Open,
    Advance,
    Payoff,
    Defer,
    Abandon,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReaderExpectationDelta {
    pub expectation_id: String,
    pub kind: String,
    pub action: ExpectationDeltaAction,
    pub description: String,
    pub evidence_excerpt: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ChapterTrackingProposal {
    pub net_change: String,
    pub open_expectations: Vec<String>,
    pub paid_expectations: Vec<String>,
    pub relationship_changes: Vec<String>,
    pub state_changes: Vec<String>,
    pub next_pull: String,
    pub character_snapshot_updates: BTreeMap<String, String>,
    pub entity_deltas: Vec<NarrativeEntityDelta>,
    pub relationship_deltas: Vec<RelationshipStateDelta>,
    pub knowledge_deltas: Vec<CharacterKnowledgeDelta>,
    pub timeline_deltas: Vec<TimelineEventDelta>,
    pub expectation_deltas: Vec<ReaderExpectationDelta>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RepairGenerationMode {
    LocalOrBoundedRepair,
    FreshRealization,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepairTarget {
    pub location: String,
    pub source_excerpt: String,
    pub fix: String,
    pub preserve: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepairSpec {
    pub repair_owner: String,
    pub generation_mode: RepairGenerationMode,
    pub objective_envelope: String,
    pub targets: Vec<RepairTarget>,
    pub invalidation_boundary: Vec<String>,
    pub comparison_required: bool,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RepairComparisonOutcome {
    SuccessfulRepair,
    TargetNotFixed,
    ObjectiveRegression,
    Inconclusive,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepairComparison {
    pub target_outcome: String,
    pub objective_preservation: String,
    pub winner: String,
    pub outcome_class: RepairComparisonOutcome,
    pub introduced_regressions: Vec<String>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticGateDecision {
    Accept,
    Revise,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticFinding {
    pub finding_id: String,
    pub severity: Severity,
    pub category: FindingCategory,
    pub location: String,
    pub evidence: String,
    pub issue: String,
    pub fix_direction: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticGate {
    pub decision: SemanticGateDecision,
    pub findings: Vec<SemanticFinding>,
}

impl CharacterSimulation {
    pub fn validate(&self) -> CoreResult<()> {
        if self.actions.is_empty()
            || self.actions.iter().any(|action| {
                [
                    &action.scene_id,
                    &action.character,
                    &action.action,
                    &action.motive_pressure,
                    &action.observable_consequence,
                ]
                .into_iter()
                .any(|value| value.trim().is_empty())
            })
        {
            return Err(invalid("character simulation is incomplete"));
        }
        Ok(())
    }

    pub fn validate_against(&self, briefs: &[SceneWritingBrief]) -> CoreResult<()> {
        self.validate()?;
        let expected = briefs
            .iter()
            .map(|brief| brief.scene_id.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        let actual = self
            .actions
            .iter()
            .map(|action| action.scene_id.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        if actual != expected {
            return Err(invalid(
                "character simulation must cover every planned scene and no unplanned scene",
            ));
        }
        Ok(())
    }
}

impl SceneResolution {
    pub fn validate(&self) -> CoreResult<()> {
        if self.scenes.is_empty()
            || self.scenes.len() > 64
            || self.scenes.iter().any(|scene| {
                !valid_director_text(&scene.scene_id, 256)
                    || scene.action_sequence.is_empty()
                    || scene.action_sequence.len() > 32
                    || scene
                        .action_sequence
                        .iter()
                        .any(|action| !valid_director_text(action, 2_048))
                    || !valid_director_text(&scene.turn, 2_048)
                    || !valid_director_text(&scene.exit_state, 2_048)
            })
        {
            return Err(invalid("scene resolution is incomplete or unsafe"));
        }
        Ok(())
    }

    pub fn validate_against(&self, briefs: &[SceneWritingBrief]) -> CoreResult<()> {
        self.validate()?;
        let actual = self
            .scenes
            .iter()
            .map(|scene| scene.scene_id.as_str())
            .collect::<Vec<_>>();
        let expected = briefs
            .iter()
            .map(|brief| brief.scene_id.as_str())
            .collect::<Vec<_>>();
        if actual != expected {
            return Err(invalid(
                "scene resolution must exactly preserve planned scene count and order",
            ));
        }
        Ok(())
    }
}

impl DirectorNote {
    pub fn freeze(
        chapter_id: impl Into<String>,
        scene: ResolvedScene,
        source_receipts: BTreeMap<String, String>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_director_note_v1".into(),
            chapter_id: chapter_id.into(),
            scene,
            source_receipts,
            private_reasoning_exposed: false,
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.expected_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        if self.fingerprint != self.expected_fingerprint()? {
            return Err(invalid("director note fingerprint changed"));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        let resolution = SceneResolution {
            scenes: vec![self.scene.clone()],
        };
        resolution.validate()?;
        if self.schema != "quillframe_director_note_v1"
            || !valid_director_text(&self.chapter_id, 256)
            || self.private_reasoning_exposed
            || self.source_receipts.len() != 2
            || !self.source_receipts.contains_key("character_simulation")
            || !self.source_receipts.contains_key("scene_resolution")
            || self.source_receipts.values().any(|value| {
                value.len() != 71
                    || !value.starts_with("sha256:")
                    || !value[7..].bytes().all(|byte| byte.is_ascii_hexdigit())
            })
        {
            return Err(invalid(
                "director note is incomplete or exposes private reasoning",
            ));
        }
        Ok(())
    }

    fn expected_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }
}

impl SurfaceRealization {
    pub fn validate(&self) -> CoreResult<()> {
        if self.manuscript.trim().is_empty() {
            return Err(invalid("surface realization has no manuscript"));
        }
        Ok(())
    }
}

pub(crate) fn parse_surface_realization_value(
    mut value: Value,
    expected_chapter_id: &str,
    expected_scene_id: &str,
) -> CoreResult<SurfaceRealization> {
    if let Some(object) = value.as_object_mut() {
        if let Some(redundant) = object.remove("raw_content") {
            let empty_provider_field = redundant.is_null() || redundant.as_str() == Some("");
            if !empty_provider_field && object.get("manuscript") != Some(&redundant) {
                return Err(invalid(
                    "surface response raw_content alias differs from manuscript",
                ));
            }
        }
        if let Some(answer) = object.remove("answer") {
            let empty_provider_field = answer.is_null() || answer.as_str() == Some("");
            let exact_alias = object.get("manuscript") == Some(&answer);
            let bounded_status_note = object
                .get("manuscript")
                .and_then(Value::as_str)
                .zip(answer.as_str())
                .is_some_and(|(manuscript, note)| {
                    manuscript.len() >= 512
                        && !note.contains(['\n', '\r'])
                        && note.len() <= 256
                        && note.len().saturating_mul(8) < manuscript.len()
                });
            if !empty_provider_field && !exact_alias && !bounded_status_note {
                return Err(invalid(
                    "surface response answer differs from manuscript and is not a bounded status note",
                ));
            }
        }
        for (field, expected) in [
            ("chapter_id", expected_chapter_id),
            ("scene_id", expected_scene_id),
        ] {
            if let Some(identity) = object.remove(field) {
                if identity.as_str() != Some(expected) {
                    return Err(CoreError::InvalidProject(format!(
                        "surface response {field} differs from the frozen scene"
                    )));
                }
            }
        }
        let metadata = object
            .iter()
            .filter(|(key, _)| key.as_str() != "manuscript")
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect::<Map<_, _>>();
        if !metadata.is_empty() {
            if metadata.len() > 8
                || !metadata.values().all(bounded_surface_metadata)
                || serde_json::to_vec(&metadata)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?
                    .len()
                    > 2_048
            {
                return Err(invalid("surface response metadata is not bounded"));
            }
            object.retain(|key, _| key == "manuscript");
        }
    }
    serde_json::from_value(value).map_err(|error| {
        CoreError::InvalidProject(format!(
            "surface stage returned invalid typed JSON: {error}"
        ))
    })
}

fn bounded_surface_metadata(value: &Value) -> bool {
    match value {
        Value::Null | Value::Bool(_) | Value::Number(_) => true,
        Value::String(value) => value.len() <= 512,
        Value::Array(values) => values.len() <= 16 && values.iter().all(bounded_surface_metadata),
        Value::Object(values) => {
            values.len() <= 16
                && values.keys().all(|key| key.len() <= 64)
                && values.values().all(bounded_surface_metadata)
        }
    }
}

impl SurfaceHardRuleAudit {
    pub fn validate_against(
        &self,
        manuscript: &str,
        candidate_fingerprint: &str,
        guidance_snapshot_fingerprint: &str,
        rule_set_fingerprint: &str,
    ) -> CoreResult<()> {
        if sha256_fingerprint(manuscript.as_bytes()) != candidate_fingerprint
            || self.candidate_fingerprint != candidate_fingerprint
            || self.guidance_snapshot_fingerprint != guidance_snapshot_fingerprint
            || self.rule_set_fingerprint != rule_set_fingerprint
            || !canonical_fingerprint(&self.candidate_fingerprint)
            || !canonical_fingerprint(&self.guidance_snapshot_fingerprint)
            || !canonical_fingerprint(&self.rule_set_fingerprint)
        {
            return Err(CoreError::AuthorityConflict(
                "surface audit identity differs from its frozen candidate or rules".into(),
            ));
        }
        let expected = crate::guidance::expected_rule_ids();
        let actual = self
            .assessments
            .iter()
            .map(|assessment| assessment.rule_id.clone())
            .collect::<Vec<_>>();
        if actual != expected || actual.iter().collect::<BTreeSet<_>>().len() != expected.len() {
            return Err(invalid(
                "surface audit must cover HF-01 through HF-30 exactly once and in order",
            ));
        }
        for assessment in &self.assessments {
            if assessment.report.trim().is_empty() {
                return Err(invalid("surface audit assessment report is empty"));
            }
            match assessment.status {
                SurfaceRuleStatus::Pass => {
                    if assessment
                        .evidence_excerpt
                        .as_deref()
                        .is_some_and(|evidence| {
                            evidence.trim().is_empty() || !manuscript.contains(evidence)
                        })
                    {
                        return Err(invalid(
                            "surface audit pass evidence is not exact candidate text",
                        ));
                    }
                }
                SurfaceRuleStatus::Fail => {
                    let evidence = assessment
                        .evidence_excerpt
                        .as_deref()
                        .filter(|value| !value.trim().is_empty())
                        .ok_or_else(|| invalid("surface audit failure requires exact evidence"))?;
                    if !manuscript.contains(evidence) {
                        return Err(invalid(
                            "surface audit failure evidence is absent from the exact candidate",
                        ));
                    }
                }
                SurfaceRuleStatus::NotApplicable | SurfaceRuleStatus::InsufficientEvidence => {
                    if assessment.evidence_excerpt.is_some() {
                        return Err(invalid(
                            "not-applicable or insufficient surface assessment cannot claim evidence",
                        ));
                    }
                }
            }
            if assessment.status == SurfaceRuleStatus::Fail {
                if !assessment
                    .repair_scope
                    .as_deref()
                    .is_some_and(|scope| matches!(scope, "local" | "block" | "scene" | "chapter"))
                {
                    return Err(invalid(
                        "failed surface assessment requires a bounded repair scope",
                    ));
                }
            } else if assessment.repair_scope.is_some() {
                return Err(invalid(
                    "only failed surface assessments may select a repair scope",
                ));
            }
        }
        let has_fail = self
            .assessments
            .iter()
            .any(|assessment| assessment.status == SurfaceRuleStatus::Fail);
        let has_insufficient = self
            .assessments
            .iter()
            .any(|assessment| assessment.status == SurfaceRuleStatus::InsufficientEvidence);
        let expected_decision = if has_fail {
            SurfaceAuditDecision::Revise
        } else if has_insufficient {
            SurfaceAuditDecision::InsufficientEvidence
        } else {
            SurfaceAuditDecision::Accept
        };
        if self.decision != expected_decision {
            return Err(invalid(
                "surface audit decision disagrees with its rule assessments",
            ));
        }
        Ok(())
    }

    pub fn normalize_pass_evidence(&mut self, manuscript: &str) {
        for assessment in &mut self.assessments {
            if assessment.status == SurfaceRuleStatus::Pass
                && assessment
                    .evidence_excerpt
                    .as_deref()
                    .is_some_and(|evidence| {
                        evidence.trim().is_empty() || !manuscript.contains(evidence)
                    })
            {
                assessment.evidence_excerpt = None;
            }
        }
    }

    pub fn passed(&self) -> bool {
        self.decision == SurfaceAuditDecision::Accept
    }
}

impl ChapterTrackingProposal {
    pub fn validate(&self) -> CoreResult<()> {
        let list_values = [
            &self.open_expectations,
            &self.paid_expectations,
            &self.relationship_changes,
            &self.state_changes,
        ];
        if self.net_change.trim().is_empty()
            || self.next_pull.trim().is_empty()
            || list_values.into_iter().any(|values| {
                values.len() > 16 || values.iter().any(|value| value.trim().is_empty())
            })
            || self.character_snapshot_updates.len() > 32
            || self
                .character_snapshot_updates
                .iter()
                .any(|(character, snapshot)| {
                    character.trim().is_empty()
                        || snapshot.trim().is_empty()
                        || snapshot.len() > 2048
                })
            || self.entity_deltas.len() > 32
            || self.relationship_deltas.len() > 32
            || self.knowledge_deltas.len() > 64
            || self.timeline_deltas.len() > 32
            || self.expectation_deltas.len() > 32
        {
            return Err(invalid(
                "chapter tracking proposal is incomplete or unbounded",
            ));
        }
        let mut identities = std::collections::BTreeSet::new();
        for delta in &self.entity_deltas {
            require_delta_fields(
                [
                    &delta.entity_id,
                    &delta.display_name,
                    &delta.evidence_excerpt,
                ],
                &delta.state,
            )?;
            if !identities.insert(("entity", delta.entity_id.as_str())) {
                return Err(invalid("narrative entity delta id is duplicated"));
            }
        }
        for delta in &self.relationship_deltas {
            require_delta_fields(
                [
                    &delta.relationship_id,
                    &delta.participant_a,
                    &delta.participant_b,
                    &delta.relationship_type,
                    &delta.evidence_excerpt,
                ],
                &delta.state,
            )?;
            if delta.participant_a == delta.participant_b
                || !identities.insert(("relationship", delta.relationship_id.as_str()))
            {
                return Err(invalid("relationship delta identity is invalid"));
            }
        }
        for delta in &self.knowledge_deltas {
            require_delta_fields(
                [
                    &delta.knowledge_id,
                    &delta.character_id,
                    &delta.confidence,
                    &delta.evidence_excerpt,
                ],
                &delta.fact,
            )?;
            if !identities.insert(("knowledge", delta.knowledge_id.as_str())) {
                return Err(invalid("knowledge delta id is duplicated"));
            }
        }
        for delta in &self.timeline_deltas {
            if [
                &delta.event_id,
                &delta.title,
                &delta.description,
                &delta.evidence_excerpt,
            ]
            .into_iter()
            .any(|value| value.trim().is_empty())
                || !identities.insert(("timeline", delta.event_id.as_str()))
            {
                return Err(invalid("timeline delta is incomplete or duplicated"));
            }
        }
        for delta in &self.expectation_deltas {
            if [
                &delta.expectation_id,
                &delta.kind,
                &delta.description,
                &delta.evidence_excerpt,
            ]
            .into_iter()
            .any(|value| value.trim().is_empty())
                || !matches!(
                    delta.kind.as_str(),
                    "question" | "promise" | "setup" | "relationship" | "goal" | "mystery"
                )
                || !identities.insert(("expectation", delta.expectation_id.as_str()))
            {
                return Err(invalid("reader expectation delta is invalid or duplicated"));
            }
        }
        if serde_json::to_vec(self)
            .map_err(|error| CoreError::Serialization(error.to_string()))?
            .len()
            > 12 * 1024
        {
            return Err(CoreError::ContextBoundary(
                "chapter tracking proposal exceeds 12 KiB".into(),
            ));
        }
        Ok(())
    }
}

fn require_delta_fields<const N: usize>(fields: [&String; N], value: &Value) -> CoreResult<()> {
    if fields.into_iter().any(|field| field.trim().is_empty()) || !value.is_object() {
        return Err(invalid(
            "narrative state delta fields and structured value are required",
        ));
    }
    Ok(())
}

impl RepairSpec {
    pub fn validate(&self) -> CoreResult<()> {
        if self.repair_owner != "prose_writer"
            || self.objective_envelope.trim().is_empty()
            || self.targets.is_empty()
            || !self.comparison_required
            || self.targets.iter().any(|target| {
                target.location.trim().is_empty()
                    || target.fix.trim().is_empty()
                    || target.source_excerpt.is_empty()
                    || target.preserve.is_empty()
                    || target.preserve.iter().any(|item| item.trim().is_empty())
            })
        {
            return Err(invalid(
                "repair specification is incomplete or routed outside the prose writer",
            ));
        }
        Ok(())
    }

    pub fn validate_against_source(&self, source: &str) -> CoreResult<()> {
        self.validate()?;
        if self.generation_mode == RepairGenerationMode::FreshRealization {
            if self
                .targets
                .iter()
                .any(|target| target.source_excerpt != "fresh-realization-whole-candidate")
            {
                return Err(invalid(
                    "fresh realization cannot carry incumbent prose windows",
                ));
            }
            return Ok(());
        }
        let mut cursor = 0usize;
        for target in &self.targets {
            let relative = source[cursor..]
                .find(&target.source_excerpt)
                .ok_or_else(|| invalid("repair target excerpt is absent or out of order"))?;
            cursor = cursor
                .checked_add(relative)
                .and_then(|value| value.checked_add(target.source_excerpt.len()))
                .ok_or_else(|| invalid("repair target range overflowed"))?;
        }
        Ok(())
    }

    pub fn verify_bounded_output(&self, source: &str, output: &str) -> CoreResult<()> {
        self.validate_against_source(source)?;
        if self.generation_mode != RepairGenerationMode::LocalOrBoundedRepair {
            return Ok(());
        }
        let mut invariants = Vec::new();
        let mut source_cursor = 0usize;
        for target in &self.targets {
            let relative = source[source_cursor..]
                .find(&target.source_excerpt)
                .ok_or_else(|| invalid("repair target excerpt is absent"))?;
            let start = source_cursor + relative;
            invariants.push(&source[source_cursor..start]);
            source_cursor = start + target.source_excerpt.len();
        }
        invariants.push(&source[source_cursor..]);
        if !output.starts_with(invariants[0]) || !output.ends_with(invariants.last().unwrap()) {
            return Err(invalid("bounded repair changed protected prefix or suffix"));
        }
        let mut output_cursor = invariants[0].len();
        for invariant in invariants
            .iter()
            .skip(1)
            .take(invariants.len().saturating_sub(2))
        {
            let relative = output[output_cursor..]
                .find(invariant)
                .ok_or_else(|| invalid("bounded repair changed protected material"))?;
            output_cursor += relative + invariant.len();
        }
        Ok(())
    }
}

impl RepairComparison {
    pub fn validate(&self) -> CoreResult<()> {
        if self.target_outcome.trim().is_empty()
            || self.objective_preservation.trim().is_empty()
            || self.winner.trim().is_empty()
        {
            return Err(invalid("repair comparison is incomplete"));
        }
        Ok(())
    }

    pub fn passed(&self) -> bool {
        self.outcome_class == RepairComparisonOutcome::SuccessfulRepair
            && self.target_outcome == "improved"
            && self.objective_preservation == "preserved"
            && self.winner == "challenger"
            && self.introduced_regressions.is_empty()
    }
}

impl SemanticGate {
    pub fn validate(&self) -> CoreResult<()> {
        if self.decision == SemanticGateDecision::Accept && !self.findings.is_empty()
            || self.decision == SemanticGateDecision::Revise && self.findings.is_empty()
            || self.findings.iter().any(|finding| {
                [
                    &finding.finding_id,
                    &finding.location,
                    &finding.evidence,
                    &finding.issue,
                    &finding.fix_direction,
                ]
                .into_iter()
                .any(|value| value.trim().is_empty())
            })
        {
            return Err(invalid("semantic gate decision and findings disagree"));
        }
        Ok(())
    }

    pub fn review_findings(&self, reviewer_role: &str) -> Vec<ReviewFinding> {
        self.findings
            .iter()
            .map(|finding| ReviewFinding {
                finding_id: finding.finding_id.clone(),
                reviewer_role: reviewer_role.into(),
                severity: finding.severity,
                category: finding.category,
                location: finding.location.clone(),
                evidence: finding.evidence.clone(),
                issue: finding.issue.clone(),
                fix_direction: finding.fix_direction.clone(),
                inherited_from: None,
            })
            .collect()
    }
}

fn valid_director_text(value: &str, maximum_bytes: usize) -> bool {
    let trimmed = value.trim();
    if trimmed.is_empty() || value.len() > maximum_bytes {
        return false;
    }
    let lower = value.to_ascii_lowercase();
    !["<think", "</think", "<analysis", "</analysis"]
        .iter()
        .any(|marker| lower.contains(marker))
}

fn canonical_fingerprint(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..].bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn invalid(message: &str) -> CoreError {
    CoreError::InvalidProject(message.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repair_spec(mode: RepairGenerationMode, excerpts: &[&str]) -> RepairSpec {
        RepairSpec {
            repair_owner: "prose_writer".into(),
            generation_mode: mode,
            objective_envelope: "repair the requested prose defect".into(),
            targets: excerpts
                .iter()
                .enumerate()
                .map(|(index, excerpt)| RepairTarget {
                    location: format!("target-{index}"),
                    source_excerpt: (*excerpt).into(),
                    fix: "improve the prose".into(),
                    preserve: vec!["story facts".into()],
                })
                .collect(),
            invalidation_boundary: vec!["story facts".into()],
            comparison_required: true,
        }
    }

    #[test]
    fn director_note_binds_structured_scene_and_private_receipts() {
        let scene = ResolvedScene {
            scene_id: "SC001".into(),
            action_sequence: vec!["陈承先查空衣架，再问最后经手的人".into()],
            turn: "父亲指出他漏算了熟客临时改号".into(),
            exit_state: "父子合并线索，锁定四十二号去向".into(),
        };
        let receipts = BTreeMap::from([
            (
                "character_simulation".into(),
                format!("sha256:{}", "1".repeat(64)),
            ),
            (
                "scene_resolution".into(),
                format!("sha256:{}", "2".repeat(64)),
            ),
        ]);

        let note = DirectorNote::freeze("CH002", scene, receipts).unwrap();

        note.validate().unwrap();
        assert!(!note.private_reasoning_exposed);
        assert!(note.fingerprint.starts_with("sha256:"));
    }

    #[test]
    fn director_artifacts_reject_private_reasoning_wrappers() {
        let resolution = SceneResolution {
            scenes: vec![ResolvedScene {
                scene_id: "SC001".into(),
                action_sequence: vec!["<think>hidden deliberation</think>".into()],
                turn: "turn".into(),
                exit_state: "exit".into(),
            }],
        };

        assert!(resolution.validate().is_err());
    }

    fn surface_audit(
        status: SurfaceRuleStatus,
        decision: SurfaceAuditDecision,
    ) -> SurfaceHardRuleAudit {
        SurfaceHardRuleAudit {
            candidate_fingerprint: sha256_fingerprint("正文证据".as_bytes()),
            guidance_snapshot_fingerprint: format!("sha256:{}", "b".repeat(64)),
            rule_set_fingerprint: format!("sha256:{}", "c".repeat(64)),
            decision,
            assessments: crate::guidance::expected_rule_ids()
                .into_iter()
                .map(|rule_id| SurfaceRuleAssessment {
                    rule_id,
                    status,
                    evidence_excerpt: matches!(
                        status,
                        SurfaceRuleStatus::Pass | SurfaceRuleStatus::Fail
                    )
                    .then(|| "证据".into()),
                    report: "已检查完整候选中的该机制".into(),
                    repair_scope: (status == SurfaceRuleStatus::Fail).then(|| "scene".into()),
                })
                .collect(),
        }
    }

    #[test]
    fn surface_audit_requires_complete_evidence_bound_coverage() {
        let candidate = sha256_fingerprint("正文证据".as_bytes());
        let guidance = format!("sha256:{}", "b".repeat(64));
        let rules = format!("sha256:{}", "c".repeat(64));
        surface_audit(SurfaceRuleStatus::Pass, SurfaceAuditDecision::Accept)
            .validate_against("正文证据", &candidate, &guidance, &rules)
            .unwrap();
        let mut normalized = surface_audit(SurfaceRuleStatus::Pass, SurfaceAuditDecision::Accept);
        normalized.assessments[0].evidence_excerpt = Some("缩写但不精确".into());
        normalized.normalize_pass_evidence("正文证据");
        assert_eq!(normalized.assessments[0].evidence_excerpt, None);
        normalized
            .validate_against("正文证据", &candidate, &guidance, &rules)
            .unwrap();

        let mut missing = surface_audit(SurfaceRuleStatus::Pass, SurfaceAuditDecision::Accept);
        missing.assessments.pop();
        assert!(missing
            .validate_against("正文证据", &candidate, &guidance, &rules)
            .is_err());

        let wrong_decision = surface_audit(SurfaceRuleStatus::Fail, SurfaceAuditDecision::Accept);
        assert!(wrong_decision
            .validate_against("正文证据", &candidate, &guidance, &rules)
            .is_err());
    }

    #[test]
    fn persisted_surface_envelope_reuses_live_normalization() {
        let surface = parse_surface_realization_value(
            serde_json::json!({
                "manuscript":"正文",
                "answer":"正文",
                "raw_content":"正文",
                "chapter_id":"CH001",
                "scene_id":"SC001",
                "chin_context":{"language":"zh-CN"}
            }),
            "CH001",
            "SC001",
        )
        .unwrap();
        assert_eq!(surface.manuscript, "正文");
        assert_eq!(
            parse_surface_realization_value(
                serde_json::json!({"manuscript":"正文","answer":""}),
                "CH001",
                "SC001",
            )
            .unwrap()
            .manuscript,
            "正文"
        );
        let long_manuscript = "场景正文".repeat(160);
        assert_eq!(
            parse_surface_realization_value(
                serde_json::json!({"manuscript":long_manuscript,"answer":"SC001 prose completed."}),
                "CH001",
                "SC001",
            )
            .unwrap()
            .manuscript,
            long_manuscript
        );
        assert!(parse_surface_realization_value(
            serde_json::json!({"manuscript":"正文","answer":"另一稿"}),
            "CH001",
            "SC001",
        )
        .is_err());
        assert!(parse_surface_realization_value(
            serde_json::json!({"manuscript":"正文","scene_id":"OTHER"}),
            "CH001",
            "SC001",
        )
        .is_err());
    }

    #[test]
    fn fresh_realization_accepts_non_prose_targets_in_diagnostic_order() {
        let spec = repair_spec(
            RepairGenerationMode::FreshRealization,
            &[
                "fresh-realization-whole-candidate",
                "fresh-realization-whole-candidate",
            ],
        );

        spec.validate_against_source("incumbent prose is not required")
            .unwrap();
    }

    #[test]
    fn fresh_realization_requires_non_prose_target_sentinels() {
        let mut spec = repair_spec(
            RepairGenerationMode::FreshRealization,
            &["present excerpt", "missing excerpt"],
        );
        assert!(spec
            .validate_against_source("present excerpt only")
            .is_err());
        for target in &mut spec.targets {
            target.source_excerpt = "fresh-realization-whole-candidate".into();
        }
        spec.validate_against_source("incumbent prose stays outside the fresh Writer")
            .unwrap();
    }

    #[test]
    fn bounded_repair_still_requires_source_order() {
        let spec = repair_spec(
            RepairGenerationMode::LocalOrBoundedRepair,
            &["later excerpt", "earlier excerpt"],
        );

        assert!(spec
            .validate_against_source("earlier excerpt then later excerpt")
            .is_err());
    }
}
