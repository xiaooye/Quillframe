use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{CoreError, CoreResult, FindingCategory, ReviewFinding, SceneWritingBrief, Severity};

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
pub struct SurfaceRealization {
    pub manuscript: String,
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
            || self.scenes.iter().any(|scene| {
                scene.scene_id.trim().is_empty()
                    || scene.action_sequence.is_empty()
                    || scene
                        .action_sequence
                        .iter()
                        .any(|action| action.trim().is_empty())
                    || scene.turn.trim().is_empty()
                    || scene.exit_state.trim().is_empty()
            })
        {
            return Err(invalid("scene resolution is incomplete"));
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

impl SurfaceRealization {
    pub fn validate(&self) -> CoreResult<()> {
        if self.manuscript.trim().is_empty() {
            return Err(invalid("surface realization has no manuscript"));
        }
        Ok(())
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

fn invalid(message: &str) -> CoreError {
    CoreError::InvalidProject(message.into())
}
