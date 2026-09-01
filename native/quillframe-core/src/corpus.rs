use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AnalyzeStage {
    BoundaryIndex,
    GoldenThree,
    ChapterExtraction,
    AggregateMechanisms,
    StoryEntities,
    Report,
    StyleProfile,
}

impl AnalyzeStage {
    pub fn ordinal(self) -> u8 {
        match self {
            Self::BoundaryIndex => 0,
            Self::GoldenThree => 1,
            Self::ChapterExtraction => 2,
            Self::AggregateMechanisms => 3,
            Self::StoryEntities => 4,
            Self::Report => 5,
            Self::StyleProfile => 6,
        }
    }

    fn next(self) -> Option<Self> {
        match self {
            Self::BoundaryIndex => Some(Self::GoldenThree),
            Self::GoldenThree => Some(Self::ChapterExtraction),
            Self::ChapterExtraction => Some(Self::AggregateMechanisms),
            Self::AggregateMechanisms => Some(Self::StoryEntities),
            Self::StoryEntities => Some(Self::Report),
            Self::Report => Some(Self::StyleProfile),
            Self::StyleProfile => None,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ChapterBoundary {
    pub chapter: u32,
    pub title: String,
    pub start_byte: u64,
    pub end_byte: u64,
    pub source_fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EvidenceAnchor {
    pub work_id: String,
    pub chapter: u32,
    pub start_byte: u64,
    pub end_byte: u64,
    pub excerpt_fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusArtifact {
    pub artifact_id: String,
    pub stage: AnalyzeStage,
    pub kind: String,
    pub content_fingerprint: String,
    pub evidence: Vec<EvidenceAnchor>,
    pub complete: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusMechanism {
    pub mechanism_id: String,
    pub reader_need: String,
    pub emotion_chain: Vec<String>,
    pub dramatic_function: String,
    pub replaceable_slots: Vec<String>,
    pub forbidden_copy_elements: Vec<String>,
    pub rhythm_refs: Vec<String>,
    pub evidence: Vec<EvidenceAnchor>,
}

impl CorpusMechanism {
    fn validate(&self) -> CoreResult<()> {
        require_text(&self.mechanism_id, "mechanism_id")?;
        require_text(&self.reader_need, "reader_need")?;
        require_text(&self.dramatic_function, "dramatic_function")?;
        if self.emotion_chain.len() < 3 || self.replaceable_slots.len() < 3 {
            return Err(CoreError::InvalidProject(
                "corpus mechanism needs an emotion chain and replaceable function slots".into(),
            ));
        }
        if self.forbidden_copy_elements.is_empty() || self.evidence.is_empty() {
            return Err(CoreError::InvalidProject(
                "corpus mechanism must carry copying boundaries and source evidence".into(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusQuality {
    pub confidence: f32,
    pub coverage: f32,
    pub overlap: f32,
    pub chapters_with_information_expansion: u32,
    pub total_chapters: u32,
}

impl CorpusQuality {
    pub fn validate(&self) -> CoreResult<()> {
        if !(0.0..=1.0).contains(&self.confidence)
            || !(0.0..=1.0).contains(&self.coverage)
            || !(0.0..=1.0).contains(&self.overlap)
            || self.total_chapters == 0
            || self.chapters_with_information_expansion > self.total_chapters
        {
            return Err(CoreError::InvalidProject(
                "invalid corpus quality metrics".into(),
            ));
        }
        if self.confidence < 0.85
            || self.coverage < 0.85
            || self.coverage > 0.95
            || self.overlap > 0.35
            || self.chapters_with_information_expansion != self.total_chapters
        {
            return Err(CoreError::InvalidProject(
                "corpus aggregation did not pass the web-novel quality gate".into(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusProgress {
    pub schema: String,
    pub source_id: String,
    pub source_fingerprint: String,
    pub current_stage: AnalyzeStage,
    pub paused_after_golden_three: bool,
    pub completed_stages: BTreeSet<AnalyzeStage>,
    pub failed_work_items: BTreeMap<String, String>,
    pub boundaries: Vec<ChapterBoundary>,
    pub artifacts: BTreeMap<String, CorpusArtifact>,
    pub checkpoint_fingerprint: String,
}

impl CorpusProgress {
    pub fn start(
        source_id: impl Into<String>,
        source_fingerprint: impl Into<String>,
        boundaries: Vec<ChapterBoundary>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_corpus_progress_v1".into(),
            source_id: source_id.into(),
            source_fingerprint: source_fingerprint.into(),
            current_stage: AnalyzeStage::BoundaryIndex,
            paused_after_golden_three: false,
            completed_stages: BTreeSet::new(),
            failed_work_items: BTreeMap::new(),
            boundaries,
            artifacts: BTreeMap::new(),
            checkpoint_fingerprint: String::new(),
        };
        value.validate_boundaries()?;
        value.refresh_checkpoint()?;
        Ok(value)
    }

    pub fn record_artifact(&mut self, artifact: CorpusArtifact) -> CoreResult<()> {
        if artifact.stage != self.current_stage || !artifact.complete {
            return Err(CoreError::AuthorityConflict(
                "artifact must be complete and belong to the active analyze stage".into(),
            ));
        }
        require_fingerprint(&artifact.content_fingerprint)?;
        if artifact.stage != AnalyzeStage::BoundaryIndex && artifact.evidence.is_empty() {
            return Err(CoreError::InvalidProject(
                "analyze artifact lacks source evidence".into(),
            ));
        }
        if self
            .artifacts
            .insert(artifact.artifact_id.clone(), artifact)
            .is_some()
        {
            return Err(CoreError::AuthorityConflict(
                "corpus artifact id already exists".into(),
            ));
        }
        self.refresh_checkpoint()
    }

    pub fn complete_stage(&mut self) -> CoreResult<()> {
        if !self
            .artifacts
            .values()
            .any(|artifact| artifact.stage == self.current_stage && artifact.complete)
        {
            return Err(CoreError::AuthorityConflict(
                "analyze stage has no complete artifact".into(),
            ));
        }
        self.completed_stages.insert(self.current_stage);
        if self.current_stage == AnalyzeStage::GoldenThree {
            self.paused_after_golden_three = true;
        } else if let Some(next) = self.current_stage.next() {
            self.current_stage = next;
        }
        self.refresh_checkpoint()
    }

    pub fn continue_after_preview(&mut self) -> CoreResult<()> {
        if !self.paused_after_golden_three
            || !self.completed_stages.contains(&AnalyzeStage::GoldenThree)
        {
            return Err(CoreError::AuthorityConflict(
                "golden-three preview is not paused".into(),
            ));
        }
        self.paused_after_golden_three = false;
        self.current_stage = AnalyzeStage::ChapterExtraction;
        self.refresh_checkpoint()
    }

    pub fn validate_checkpoint(&self) -> CoreResult<()> {
        let mut copy = self.clone();
        copy.checkpoint_fingerprint.clear();
        let bytes = serde_json::to_vec(&copy)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if self.checkpoint_fingerprint != sha256_fingerprint(bytes) {
            return Err(CoreError::AuthorityConflict(
                "corpus checkpoint fingerprint changed".into(),
            ));
        }
        self.validate_boundaries()
    }

    fn validate_boundaries(&self) -> CoreResult<()> {
        require_fingerprint(&self.source_fingerprint)?;
        if self.boundaries.is_empty() {
            return Err(CoreError::InvalidProject(
                "Stage 0 chapter boundary authority is required".into(),
            ));
        }
        for (index, boundary) in self.boundaries.iter().enumerate() {
            if boundary.chapter as usize != index + 1
                || boundary.title.trim().is_empty()
                || boundary.start_byte >= boundary.end_byte
                || boundary.source_fingerprint != self.source_fingerprint
                || index > 0 && self.boundaries[index - 1].end_byte > boundary.start_byte
            {
                return Err(CoreError::InvalidProject(
                    "chapter boundaries are not one contiguous source authority".into(),
                ));
            }
        }
        Ok(())
    }

    fn refresh_checkpoint(&mut self) -> CoreResult<()> {
        self.checkpoint_fingerprint.clear();
        let bytes = serde_json::to_vec(&self)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        self.checkpoint_fingerprint = sha256_fingerprint(bytes);
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceFreeCorpusPack {
    pub schema: String,
    pub genre: String,
    pub mechanisms: Vec<CorpusMechanism>,
    pub rhythm_summary: String,
    pub style_guidance: Vec<String>,
    pub source_identities_removed: bool,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterCorpusMechanism {
    pub mechanism_id: String,
    pub reader_need: String,
    pub emotion_chain: Vec<String>,
    pub dramatic_function: String,
    pub replaceable_slots: Vec<String>,
    pub forbidden_copy_elements: Vec<String>,
    pub rhythm_refs: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterCorpusProjection {
    pub schema: String,
    pub genre: String,
    pub mechanisms: Vec<WriterCorpusMechanism>,
    pub rhythm_summary: String,
    pub style_guidance: Vec<String>,
    pub source_free_pack_fingerprint: String,
    pub evidence_absent: bool,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterCorpusSelection {
    pub selected_pack_fingerprints: Vec<String>,
}

impl WriterCorpusSelection {
    pub fn validate_against(&self, candidates: &[WriterCorpusProjection]) -> CoreResult<()> {
        if self.selected_pack_fingerprints.len() > 4 {
            return Err(CoreError::ContextBoundary(
                "corpus greenlight may select at most four packs".into(),
            ));
        }
        let universe = candidates
            .iter()
            .map(|candidate| candidate.source_free_pack_fingerprint.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        let selected = self
            .selected_pack_fingerprints
            .iter()
            .map(String::as_str)
            .collect::<std::collections::BTreeSet<_>>();
        if selected.len() != self.selected_pack_fingerprints.len()
            || selected
                .iter()
                .any(|fingerprint| !universe.contains(fingerprint))
        {
            return Err(CoreError::ContextBoundary(
                "corpus greenlight selected duplicate or inactive packs".into(),
            ));
        }
        Ok(())
    }

    pub fn project(
        &self,
        candidates: &[WriterCorpusProjection],
    ) -> CoreResult<Vec<WriterCorpusProjection>> {
        self.validate_against(candidates)?;
        self.selected_pack_fingerprints
            .iter()
            .map(|fingerprint| {
                candidates
                    .iter()
                    .find(|candidate| &candidate.source_free_pack_fingerprint == fingerprint)
                    .cloned()
                    .ok_or_else(|| {
                        CoreError::ContextBoundary("selected corpus pack disappeared".into())
                    })
            })
            .collect()
    }
}

impl SourceFreeCorpusPack {
    pub fn build(
        genre: impl Into<String>,
        mechanisms: Vec<CorpusMechanism>,
        rhythm_summary: impl Into<String>,
        style_guidance: Vec<String>,
    ) -> CoreResult<Self> {
        for mechanism in &mechanisms {
            mechanism.validate()?;
        }
        if mechanisms.is_empty() {
            return Err(CoreError::InvalidProject(
                "source-free corpus pack requires mechanisms".into(),
            ));
        }
        let mut value = Self {
            schema: "quillframe_source_free_corpus_pack_v1".into(),
            genre: genre.into(),
            mechanisms,
            rhythm_summary: rhythm_summary.into(),
            style_guidance,
            source_identities_removed: true,
            fingerprint: String::new(),
        };
        require_text(&value.genre, "genre")?;
        require_text(&value.rhythm_summary, "rhythm_summary")?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        if !self.source_identities_removed || self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::ContextBoundary(
                "corpus pack is not source-free or its fingerprint changed".into(),
            ));
        }
        for mechanism in &self.mechanisms {
            mechanism.validate()?;
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut copy = self.clone();
        copy.fingerprint.clear();
        for mechanism in &mut copy.mechanisms {
            mechanism.evidence.clear();
        }
        let bytes = serde_json::to_vec(&copy)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }

    pub fn writer_projection(&self) -> CoreResult<WriterCorpusProjection> {
        self.validate()?;
        let mechanisms = self
            .mechanisms
            .iter()
            .map(|mechanism| WriterCorpusMechanism {
                mechanism_id: mechanism.mechanism_id.clone(),
                reader_need: mechanism.reader_need.clone(),
                emotion_chain: mechanism.emotion_chain.clone(),
                dramatic_function: mechanism.dramatic_function.clone(),
                replaceable_slots: mechanism.replaceable_slots.clone(),
                forbidden_copy_elements: mechanism.forbidden_copy_elements.clone(),
                rhythm_refs: mechanism.rhythm_refs.clone(),
            })
            .collect();
        let mut projection = WriterCorpusProjection {
            schema: "quillframe_writer_corpus_projection_v1".into(),
            genre: self.genre.clone(),
            mechanisms,
            rhythm_summary: self.rhythm_summary.clone(),
            style_guidance: self.style_guidance.clone(),
            source_free_pack_fingerprint: self.fingerprint.clone(),
            evidence_absent: true,
            fingerprint: String::new(),
        };
        projection.fingerprint = projection.compute_fingerprint()?;
        Ok(projection)
    }
}

impl WriterCorpusProjection {
    pub fn validate(&self) -> CoreResult<()> {
        require_fingerprint(&self.source_free_pack_fingerprint)?;
        if self.schema != "quillframe_writer_corpus_projection_v1"
            || !self.evidence_absent
            || self.genre.trim().is_empty()
            || self.mechanisms.is_empty()
            || self.fingerprint != self.compute_fingerprint()?
        {
            return Err(CoreError::ContextBoundary(
                "Writer corpus projection is incomplete or contains evidence".into(),
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

fn require_text(value: &str, field: &str) -> CoreResult<()> {
    if value.trim().is_empty() {
        return Err(CoreError::InvalidProject(format!(
            "{field} must be non-empty"
        )));
    }
    Ok(())
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
    use super::*;

    fn fp() -> String {
        format!("sha256:{}", "a".repeat(64))
    }

    #[test]
    fn analyze_resume_uses_one_boundary_authority_and_pauses_after_golden_three() {
        let mut progress = CorpusProgress::start(
            "source-1",
            fp(),
            vec![ChapterBoundary {
                chapter: 1,
                title: "第一章".into(),
                start_byte: 0,
                end_byte: 100,
                source_fingerprint: fp(),
            }],
        )
        .unwrap();
        progress
            .record_artifact(CorpusArtifact {
                artifact_id: "boundaries".into(),
                stage: AnalyzeStage::BoundaryIndex,
                kind: "chapter_boundaries".into(),
                content_fingerprint: fp(),
                evidence: vec![],
                complete: true,
            })
            .unwrap();
        progress.complete_stage().unwrap();
        progress
            .record_artifact(CorpusArtifact {
                artifact_id: "golden-three".into(),
                stage: AnalyzeStage::GoldenThree,
                kind: "preview".into(),
                content_fingerprint: fp(),
                evidence: vec![EvidenceAnchor {
                    work_id: "WORK001".into(),
                    chapter: 1,
                    start_byte: 0,
                    end_byte: 50,
                    excerpt_fingerprint: fp(),
                }],
                complete: true,
            })
            .unwrap();
        progress.complete_stage().unwrap();
        assert!(progress.paused_after_golden_three);
        progress.validate_checkpoint().unwrap();
        progress.continue_after_preview().unwrap();
        assert_eq!(progress.current_stage, AnalyzeStage::ChapterExtraction);
    }

    #[test]
    fn source_free_pack_hash_excludes_evidence_and_never_exposes_source_identity() {
        let pack = SourceFreeCorpusPack::build(
            "玄幻",
            vec![CorpusMechanism {
                mechanism_id: "EM-001".into(),
                reader_need: "替代性胜利".into(),
                emotion_chain: vec!["受压".into(), "加压".into(), "释放".into()],
                dramatic_function: "被轻视者用结果公开反证".into(),
                replaceable_slots: vec!["误判者".into(), "见证者".into(), "证据".into()],
                forbidden_copy_elements: vec!["专名".into(), "台词".into()],
                rhythm_refs: vec!["RH-001".into()],
                evidence: vec![EvidenceAnchor {
                    work_id: "WORK001".into(),
                    chapter: 8,
                    start_byte: 800,
                    end_byte: 900,
                    excerpt_fingerprint: fp(),
                }],
            }],
            "三章小循环，十五章大循环",
            vec!["对白与动作交织".into()],
        )
        .unwrap();
        pack.validate().unwrap();
        let json = serde_json::to_string(&pack).unwrap();
        assert!(!json.contains("source-1"));
    }
}
