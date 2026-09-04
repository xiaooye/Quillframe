use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::{
    fingerprint::sha256_fingerprint, ChapterTrackingRecord, CoreError, CoreResult,
    HierarchicalPlanLock, ProductionTaskMode, ReviewDecision, ReviewReport, WriterCorpusProjection,
};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SceneWritingBrief {
    pub scene_id: String,
    pub ordinal: u32,
    pub viewpoint: String,
    pub location: String,
    pub entry_state: String,
    pub objective: String,
    pub opposition: String,
    pub turn: String,
    pub choice: String,
    pub consequence: String,
    pub value_shift: String,
    pub information_change: String,
    pub exit_state: String,
    pub emotion_target: String,
    pub reader_effect: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterContinuityEntry {
    pub record: ChapterTrackingRecord,
    pub canon_head_fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterPack {
    pub schema: String,
    pub chapter_id: String,
    pub plan_lock: HierarchicalPlanLock,
    pub active_plan_fingerprint: String,
    pub book_setup_fingerprint: String,
    pub context_freeze_fingerprint: String,
    pub tracking_fingerprint: String,
    pub reader_pressure: String,
    pub scenes: Vec<SceneWritingBrief>,
    pub continuity_context: Vec<WriterContinuityEntry>,
    pub corpus_mechanisms: Vec<WriterCorpusProjection>,
    pub private_state_absent: bool,
    pub fingerprint: String,
}

impl WriterPack {
    #[allow(clippy::too_many_arguments)]
    pub fn freeze(
        chapter_id: impl Into<String>,
        plan_lock: HierarchicalPlanLock,
        book_setup_fingerprint: impl Into<String>,
        context_freeze_fingerprint: impl Into<String>,
        tracking_fingerprint: impl Into<String>,
        reader_pressure: impl Into<String>,
        continuity_context: Vec<WriterContinuityEntry>,
        corpus_mechanisms: Vec<WriterCorpusProjection>,
    ) -> CoreResult<Self> {
        if corpus_mechanisms.len() > 4 {
            return Err(CoreError::ContextBoundary(
                "Writer Pack accepts zero to four source-free corpus packs".into(),
            ));
        }
        for pack in &corpus_mechanisms {
            pack.validate()?;
        }
        if continuity_context.len() > 12 {
            return Err(CoreError::ContextBoundary(
                "Writer Pack accepts at most twelve settled continuity entries".into(),
            ));
        }
        plan_lock.validate()?;
        let chapter_id = chapter_id.into();
        let chapter_plan = plan_lock.chapter_plan(&chapter_id)?;
        let scenes = chapter_plan
            .scene_script
            .scenes
            .iter()
            .map(|scene| SceneWritingBrief {
                scene_id: scene.scene_id.clone(),
                ordinal: scene.ordinal,
                viewpoint: scene.viewpoint.clone(),
                location: scene.location.clone(),
                entry_state: scene.entry_state.clone(),
                objective: scene.objective.clone(),
                opposition: scene.opposition.clone(),
                turn: scene.turn.clone(),
                choice: scene.choice.clone(),
                consequence: scene.consequence.clone(),
                value_shift: scene.value_shift.clone(),
                information_change: scene.information_change.clone(),
                exit_state: scene.exit_state.clone(),
                emotion_target: scene.emotion_target.clone(),
                reader_effect: scene.reader_effect.clone(),
            })
            .collect::<Vec<_>>();
        if scenes.is_empty() {
            return Err(CoreError::InvalidPlan(
                "Writer Pack requires ordered scene briefs".into(),
            ));
        }
        for (index, scene) in scenes.iter().enumerate() {
            if scene.ordinal as usize != index + 1
                || [
                    &scene.scene_id,
                    &scene.viewpoint,
                    &scene.location,
                    &scene.entry_state,
                    &scene.objective,
                    &scene.opposition,
                    &scene.turn,
                    &scene.choice,
                    &scene.consequence,
                    &scene.value_shift,
                    &scene.information_change,
                    &scene.exit_state,
                    &scene.emotion_target,
                    &scene.reader_effect,
                ]
                .into_iter()
                .any(|value| value.trim().is_empty())
            {
                return Err(CoreError::InvalidPlan(
                    "Writer Pack scene briefs are incomplete or unordered".into(),
                ));
            }
        }
        let active_plan_fingerprint = plan_lock
            .layers
            .last()
            .map(|layer| layer.proposal_fingerprint.clone())
            .ok_or_else(|| CoreError::InvalidPlan("Writer Pack plan lock is empty".into()))?;
        let mut value = Self {
            schema: "quillframe_writer_pack_v5".into(),
            chapter_id,
            plan_lock,
            active_plan_fingerprint,
            book_setup_fingerprint: book_setup_fingerprint.into(),
            context_freeze_fingerprint: context_freeze_fingerprint.into(),
            tracking_fingerprint: tracking_fingerprint.into(),
            reader_pressure: reader_pressure.into(),
            scenes,
            continuity_context,
            corpus_mechanisms,
            private_state_absent: true,
            fingerprint: String::new(),
        };
        for fingerprint in [
            &value.active_plan_fingerprint,
            &value.book_setup_fingerprint,
            &value.context_freeze_fingerprint,
            &value.tracking_fingerprint,
        ] {
            require_fingerprint(fingerprint)?;
        }
        if value.chapter_id.trim().is_empty() || value.reader_pressure.trim().is_empty() {
            return Err(CoreError::InvalidPlan(
                "Writer Pack lacks chapter identity or Reader Pressure".into(),
            ));
        }
        let mut seen_chapters = std::collections::BTreeSet::new();
        let mut continuity_bytes = 0usize;
        for entry in &value.continuity_context {
            entry.record.validate()?;
            require_fingerprint(&entry.canon_head_fingerprint)?;
            if entry.record.chapter_id == value.chapter_id
                || !seen_chapters.insert(entry.record.chapter_id.clone())
            {
                return Err(CoreError::ContextBoundary(
                    "Writer Pack continuity entries must be unique settled prior chapters".into(),
                ));
            }
            continuity_bytes = continuity_bytes.saturating_add(
                serde_json::to_vec(entry)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?
                    .len(),
            );
        }
        if continuity_bytes > 12 * 1024 {
            return Err(CoreError::ContextBoundary(
                "Writer Pack continuity context exceeds 12 KiB".into(),
            ));
        }
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.plan_lock.validate()?;
        let chapter_layer = self.plan_lock.layers.last().ok_or_else(|| {
            CoreError::ContextBoundary("Writer Pack plan lock has no chapter layer".into())
        })?;
        let chapter_plan = self.plan_lock.chapter_plan(&self.chapter_id)?;
        let planned_scenes = chapter_plan
            .scene_script
            .scenes
            .iter()
            .map(|scene| SceneWritingBrief {
                scene_id: scene.scene_id.clone(),
                ordinal: scene.ordinal,
                viewpoint: scene.viewpoint.clone(),
                location: scene.location.clone(),
                entry_state: scene.entry_state.clone(),
                objective: scene.objective.clone(),
                opposition: scene.opposition.clone(),
                turn: scene.turn.clone(),
                choice: scene.choice.clone(),
                consequence: scene.consequence.clone(),
                value_shift: scene.value_shift.clone(),
                information_change: scene.information_change.clone(),
                exit_state: scene.exit_state.clone(),
                emotion_target: scene.emotion_target.clone(),
                reader_effect: scene.reader_effect.clone(),
            })
            .collect::<Vec<_>>();
        if self.schema != "quillframe_writer_pack_v5"
            || chapter_layer.target.node_id != self.chapter_id
            || chapter_layer.proposal_fingerprint != self.active_plan_fingerprint
            || require_fingerprint(&self.book_setup_fingerprint).is_err()
            || self.scenes != planned_scenes
            || !self.private_state_absent
            || self.fingerprint != self.compute_fingerprint()?
        {
            return Err(CoreError::ContextBoundary(
                "Writer Pack contains private state or changed after freeze".into(),
            ));
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut copy = self.clone();
        copy.fingerprint.clear();
        let bytes = serde_json::to_vec(&copy)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CandidateArtifact {
    pub schema: String,
    pub candidate_id: String,
    pub chapter_id: String,
    pub writer_pack_fingerprint: String,
    pub parent_candidate_fingerprint: Option<String>,
    pub revision: u32,
    pub manuscript: String,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionRelease {
    pub schema: String,
    pub release_id: String,
    pub candidate_id: String,
    pub candidate_fingerprint: String,
    pub task_mode: ProductionTaskMode,
    pub writer_pack_fingerprint: String,
    pub tracking_fingerprint: String,
    pub review_report_fingerprint: String,
    pub stage_receipt_fingerprints: BTreeMap<String, String>,
    pub released_at: String,
    pub fingerprint: String,
}

impl ProductionRelease {
    pub fn create(
        candidate_id: impl Into<String>,
        candidate_fingerprint: impl Into<String>,
        writer_pack_fingerprint: impl Into<String>,
        tracking_fingerprint: impl Into<String>,
        review_report_fingerprint: impl Into<String>,
        stage_receipt_fingerprints: BTreeMap<String, String>,
        released_at: impl Into<String>,
    ) -> CoreResult<Self> {
        Self::create_for_mode(
            candidate_id,
            candidate_fingerprint,
            ProductionTaskMode::Draft,
            writer_pack_fingerprint,
            tracking_fingerprint,
            review_report_fingerprint,
            stage_receipt_fingerprints,
            released_at,
        )
    }

    #[allow(clippy::too_many_arguments)]
    pub fn create_for_mode(
        candidate_id: impl Into<String>,
        candidate_fingerprint: impl Into<String>,
        task_mode: ProductionTaskMode,
        writer_pack_fingerprint: impl Into<String>,
        tracking_fingerprint: impl Into<String>,
        review_report_fingerprint: impl Into<String>,
        stage_receipt_fingerprints: BTreeMap<String, String>,
        released_at: impl Into<String>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_production_release_v2".into(),
            release_id: format!("release-{}", uuid::Uuid::new_v4()),
            candidate_id: candidate_id.into(),
            candidate_fingerprint: candidate_fingerprint.into(),
            task_mode,
            writer_pack_fingerprint: writer_pack_fingerprint.into(),
            tracking_fingerprint: tracking_fingerprint.into(),
            review_report_fingerprint: review_report_fingerprint.into(),
            stage_receipt_fingerprints,
            released_at: released_at.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "production release fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if !matches!(
            self.schema.as_str(),
            "quillframe_production_release_v1" | "quillframe_production_release_v2"
        ) || self.release_id.trim().is_empty()
            || self.candidate_id.trim().is_empty()
            || self.released_at.trim().is_empty()
        {
            return Err(CoreError::AuthorityConflict(
                "production release identity is incomplete".into(),
            ));
        }
        for fingerprint in [
            &self.candidate_fingerprint,
            &self.writer_pack_fingerprint,
            &self.tracking_fingerprint,
            &self.review_report_fingerprint,
        ] {
            require_fingerprint(fingerprint)?;
        }
        for required_stage in [
            "context_query_plan",
            "context_greenlight",
            "context_freeze",
            "corpus_greenlight",
            "preference_greenlight",
            "reader_engagement",
            "character_simulation",
            "scene_resolution",
            "surface_realization",
            "continuity",
            "candidate_self_audit",
            "independent_semantic_gate",
            "settlement_tracking_projection",
            "settlement_tracking_audit",
            "user_visible_gate",
        ] {
            let fingerprint = self
                .stage_receipt_fingerprints
                .get(required_stage)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict(format!(
                        "production release lacks {required_stage} evidence"
                    ))
                })?;
            require_fingerprint(fingerprint)?;
        }
        if self.schema == "quillframe_production_release_v2" {
            let fingerprint = self
                .stage_receipt_fingerprints
                .get("surface_hard_rule_audit")
                .ok_or_else(|| {
                    CoreError::AuthorityConflict(
                        "production release lacks surface_hard_rule_audit evidence".into(),
                    )
                })?;
            require_fingerprint(fingerprint)?;
        }
        let scene_receipts = self
            .stage_receipt_fingerprints
            .iter()
            .filter(|(stage, _)| stage.starts_with("surface_scene_"))
            .collect::<Vec<_>>();
        if scene_receipts.is_empty() {
            return Err(CoreError::AuthorityConflict(
                "production release lacks scene-level surface evidence".into(),
            ));
        }
        for (ordinal, (stage, fingerprint)) in scene_receipts.iter().enumerate() {
            let expected_prefix = format!("surface_scene_{:04}_", ordinal + 1);
            if !stage.starts_with(&expected_prefix) {
                return Err(CoreError::AuthorityConflict(
                    "surface scene receipts are not a contiguous ordered sequence".into(),
                ));
            }
            require_fingerprint(fingerprint)?;
        }
        if self.task_mode == ProductionTaskMode::Revise {
            for required_stage in ["repair_editor", "repair_comparison", "repair_source"] {
                let fingerprint = self
                    .stage_receipt_fingerprints
                    .get(required_stage)
                    .ok_or_else(|| {
                        CoreError::AuthorityConflict(format!(
                            "REVISE release lacks {required_stage} evidence"
                        ))
                    })?;
                require_fingerprint(fingerprint)?;
            }
        }
        if self
            .stage_receipt_fingerprints
            .values()
            .any(|fingerprint| require_fingerprint(fingerprint).is_err())
        {
            return Err(CoreError::AuthorityConflict(
                "production release contains a malformed stage receipt".into(),
            ));
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut copy = self.clone();
        copy.fingerprint.clear();
        serde_json::to_vec(&copy)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }
}

impl CandidateArtifact {
    pub fn draft(
        candidate_id: impl Into<String>,
        writer_pack: &WriterPack,
        manuscript: impl Into<String>,
    ) -> CoreResult<Self> {
        writer_pack.validate()?;
        Self::new(candidate_id, writer_pack, None, 1, manuscript.into())
    }

    pub fn revision(
        candidate_id: impl Into<String>,
        writer_pack: &WriterPack,
        parent_candidate_fingerprint: impl Into<String>,
        revision: u32,
        manuscript: impl Into<String>,
    ) -> CoreResult<Self> {
        writer_pack.validate()?;
        if revision < 2 {
            return Err(CoreError::InvalidProject(
                "revision candidate number must be at least two".into(),
            ));
        }
        Self::new(
            candidate_id,
            writer_pack,
            Some(parent_candidate_fingerprint.into()),
            revision,
            manuscript.into(),
        )
    }

    fn new(
        candidate_id: impl Into<String>,
        writer_pack: &WriterPack,
        parent_candidate_fingerprint: Option<String>,
        revision: u32,
        manuscript: String,
    ) -> CoreResult<Self> {
        if manuscript.trim().is_empty() || revision == 0 {
            return Err(CoreError::InvalidProject(
                "candidate manuscript and revision are required".into(),
            ));
        }
        if let Some(parent) = &parent_candidate_fingerprint {
            require_fingerprint(parent)?;
        }
        let mut value = Self {
            schema: "quillframe_candidate_artifact_v1".into(),
            candidate_id: candidate_id.into(),
            chapter_id: writer_pack.chapter_id.clone(),
            writer_pack_fingerprint: writer_pack.fingerprint.clone(),
            parent_candidate_fingerprint,
            revision,
            manuscript,
            fingerprint: String::new(),
        };
        value.fingerprint = sha256_fingerprint(value.manuscript.as_bytes());
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        if self.schema != "quillframe_candidate_artifact_v1"
            || self.candidate_id.trim().is_empty()
            || self.chapter_id.trim().is_empty()
            || self.revision == 0
            || self.manuscript.trim().is_empty()
        {
            return Err(CoreError::AuthorityConflict(
                "candidate artifact is incomplete".into(),
            ));
        }
        require_fingerprint(&self.writer_pack_fingerprint)?;
        if self.fingerprint != sha256_fingerprint(self.manuscript.as_bytes()) {
            return Err(CoreError::AuthorityConflict(
                "candidate fingerprint changed".into(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProductionState {
    Ready,
    WriterPackFrozen,
    Drafted,
    AwaitingReview,
    RevisionRequired,
    Accepted,
    InfrastructureFailed,
}

#[derive(Clone, Debug)]
pub struct ProductionPipeline {
    pub state: ProductionState,
    writer_pack: Option<WriterPack>,
    candidates: BTreeMap<String, CandidateArtifact>,
    current_candidate_fingerprint: Option<String>,
    open_findings: Vec<String>,
}

impl Default for ProductionPipeline {
    fn default() -> Self {
        Self {
            state: ProductionState::Ready,
            writer_pack: None,
            candidates: BTreeMap::new(),
            current_candidate_fingerprint: None,
            open_findings: Vec::new(),
        }
    }
}

impl ProductionPipeline {
    pub fn freeze_writer_pack(&mut self, pack: WriterPack) -> CoreResult<()> {
        if self.state != ProductionState::Ready {
            return Err(CoreError::AuthorityConflict(
                "Writer Pack may only freeze from ready state".into(),
            ));
        }
        pack.validate()?;
        self.writer_pack = Some(pack);
        self.state = ProductionState::WriterPackFrozen;
        Ok(())
    }

    pub fn record_draft(&mut self, candidate: CandidateArtifact) -> CoreResult<()> {
        if !matches!(
            self.state,
            ProductionState::WriterPackFrozen | ProductionState::RevisionRequired
        ) {
            return Err(CoreError::AuthorityConflict(
                "candidate cannot enter the current production state".into(),
            ));
        }
        candidate.validate()?;
        let pack = self.writer_pack.as_ref().ok_or_else(|| {
            CoreError::AuthorityConflict("production has no frozen Writer Pack".into())
        })?;
        if candidate.writer_pack_fingerprint != pack.fingerprint {
            return Err(CoreError::AuthorityConflict(
                "candidate was generated from a different Writer Pack".into(),
            ));
        }
        if self.state == ProductionState::RevisionRequired
            && candidate.parent_candidate_fingerprint != self.current_candidate_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "revision does not bind the rejected candidate".into(),
            ));
        }
        self.current_candidate_fingerprint = Some(candidate.fingerprint.clone());
        self.candidates
            .insert(candidate.fingerprint.clone(), candidate);
        self.state = ProductionState::Drafted;
        Ok(())
    }

    pub fn begin_review(&mut self) -> CoreResult<&str> {
        if self.state != ProductionState::Drafted {
            return Err(CoreError::AuthorityConflict(
                "review requires a complete draft candidate".into(),
            ));
        }
        self.state = ProductionState::AwaitingReview;
        Ok(self.current_candidate_fingerprint.as_deref().unwrap())
    }

    pub fn apply_review(&mut self, report: ReviewReport) -> CoreResult<()> {
        if self.state != ProductionState::AwaitingReview {
            return Err(CoreError::AuthorityConflict(
                "review result arrived outside review state".into(),
            ));
        }
        let current = self.current_candidate_fingerprint.as_deref().unwrap();
        report.validate(current)?;
        self.open_findings = report
            .findings
            .iter()
            .map(|finding| finding.finding_id.clone())
            .collect();
        self.state = match report.decision {
            ReviewDecision::Accept => ProductionState::Accepted,
            ReviewDecision::Revise => ProductionState::RevisionRequired,
            ReviewDecision::InfrastructureFailed => ProductionState::InfrastructureFailed,
        };
        Ok(())
    }

    pub fn revise(
        &mut self,
        candidate_id: impl Into<String>,
        manuscript: impl Into<String>,
    ) -> CoreResult<CandidateArtifact> {
        if self.state != ProductionState::RevisionRequired {
            return Err(CoreError::AuthorityConflict(
                "revision requires a rejected candidate".into(),
            ));
        }
        let parent = self.current_candidate_fingerprint.clone().unwrap();
        let prior = self.candidates.get(&parent).unwrap();
        let pack = self.writer_pack.as_ref().unwrap();
        CandidateArtifact::new(
            candidate_id,
            pack,
            Some(parent),
            prior.revision + 1,
            manuscript.into(),
        )
    }

    pub fn open_findings(&self) -> &[String] {
        &self.open_findings
    }
}

fn require_fingerprint(value: &str) -> CoreResult<()> {
    if value.len() != 71
        || !value.starts_with("sha256:")
        || !value[7..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
    {
        return Err(CoreError::InvalidProject(
            "fingerprint must be canonical sha256".into(),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;

    use crate::{FindingCategory, ReviewFinding, ReviewMode, ReviewReportInput, Severity};

    use super::*;

    fn fp() -> String {
        format!("sha256:{}", "a".repeat(64))
    }

    fn pack() -> WriterPack {
        WriterPack::freeze(
            "CH001",
            crate::planning::fixture_hierarchical_plan_lock(),
            fp(),
            fp(),
            fp(),
            "读者需要看到主角主动选择并承担代价",
            vec![],
            vec![],
        )
        .unwrap()
    }

    fn release_receipts() -> BTreeMap<String, String> {
        [
            "context_query_plan",
            "context_greenlight",
            "context_freeze",
            "corpus_greenlight",
            "preference_greenlight",
            "reader_engagement",
            "character_simulation",
            "scene_resolution",
            "surface_scene_0001_SC001",
            "surface_realization",
            "continuity",
            "candidate_self_audit",
            "independent_semantic_gate",
            "settlement_tracking_projection",
            "settlement_tracking_audit",
            "user_visible_gate",
        ]
        .into_iter()
        .map(|stage| (stage.into(), fp()))
        .collect()
    }

    #[test]
    fn release_v2_requires_surface_rule_audit_and_v1_remains_readable() {
        let receipts = release_receipts();
        assert!(
            ProductionRelease::create("C1", fp(), fp(), fp(), fp(), receipts.clone(), "T0")
                .is_err()
        );

        let mut complete = receipts.clone();
        complete.insert("surface_hard_rule_audit".into(), fp());
        let current =
            ProductionRelease::create("C1", fp(), fp(), fp(), fp(), complete, "T0").unwrap();
        assert_eq!(current.schema, "quillframe_production_release_v2");

        let mut legacy = current;
        legacy.schema = "quillframe_production_release_v1".into();
        legacy
            .stage_receipt_fingerprints
            .remove("surface_hard_rule_audit");
        legacy.fingerprint = legacy.compute_fingerprint().unwrap();
        legacy.validate().unwrap();
    }

    #[test]
    fn independent_rejection_routes_to_exact_bound_revision() {
        let pack = pack();
        let draft = CandidateArtifact::draft("C1", &pack, "第一版正文").unwrap();
        let draft_fp = draft.fingerprint.clone();
        let mut pipeline = ProductionPipeline::default();
        pipeline.freeze_writer_pack(pack).unwrap();
        pipeline.record_draft(draft).unwrap();
        assert_eq!(pipeline.begin_review().unwrap(), draft_fp);
        let report = ReviewReport::create(ReviewReportInput {
            candidate_fingerprint: draft_fp.clone(),
            mode: ReviewMode::Solo,
            reviewer_sessions: BTreeSet::from(["solo-reviewer".into()]),
            independent_context: true,
            deterministic_prechecks: vec!["format-ok".into()],
            findings: vec![ReviewFinding {
                finding_id: "F1".into(),
                reviewer_role: "solo".into(),
                severity: Severity::S2,
                category: FindingCategory::Causal,
                location: "scene:1".into(),
                evidence: "决定缺少触发".into(),
                issue: "因果跳跃".into(),
                fix_direction: "补触发证据".into(),
                inherited_from: None,
            }],
            disagreements: vec![],
            infrastructure_failed: false,
        })
        .unwrap();
        pipeline.apply_review(report).unwrap();
        assert_eq!(pipeline.state, ProductionState::RevisionRequired);
        let revision = pipeline.revise("C2", "修订正文").unwrap();
        assert_eq!(
            revision.parent_candidate_fingerprint.as_deref(),
            Some(draft_fp.as_str())
        );
        pipeline.record_draft(revision).unwrap();
        assert_eq!(pipeline.state, ProductionState::Drafted);
    }

    #[test]
    fn writer_pack_rejects_scene_content_that_differs_from_frozen_script() {
        let mut pack = pack();
        pack.scenes[0].choice = "same id and ordinal, different creative instruction".into();
        pack.fingerprint = pack.compute_fingerprint().unwrap();
        assert!(pack.validate().is_err());
    }
}
