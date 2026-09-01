use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ContextStage {
    Planning,
    Character,
    Scene,
    Writer,
    BlindReader,
    Continuity,
    IndependentReview,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ContextTier {
    RecentManuscript,
    SettledLedger,
    ArchiveEvidence,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ContextEntry {
    pub reference: String,
    pub tier: ContextTier,
    pub fingerprint: String,
    pub summary: String,
    pub byte_size: usize,
    pub source_chapter_id: Option<String>,
    pub source_head_fingerprint: Option<String>,
    pub allowed_stages: BTreeSet<ContextStage>,
    pub contains_manuscript_body: bool,
    pub contains_private_state: bool,
    pub contains_corpus_identity: bool,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ContextQueryPlan {
    pub queries: Vec<String>,
    pub required_references: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ContextSelectionProposal {
    pub selected_references: Vec<String>,
}

#[derive(Clone, Debug, Default)]
pub struct ContextManifest {
    entries: Vec<ContextEntry>,
    seen: BTreeSet<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ContextFreeze {
    pub schema: String,
    pub stage: ContextStage,
    pub entries: Vec<ContextEntry>,
    pub total_bytes: usize,
    pub fingerprint: String,
}

impl ContextManifest {
    pub fn select(&mut self, entry: ContextEntry) -> CoreResult<()> {
        if entry.reference.trim().is_empty()
            || entry.summary.trim().is_empty()
            || entry.byte_size != entry.summary.len()
            || !canonical_fingerprint(&entry.fingerprint)
            || entry.source_chapter_id.is_some() != entry.source_head_fingerprint.is_some()
            || entry
                .source_head_fingerprint
                .as_deref()
                .is_some_and(|fingerprint| !canonical_fingerprint(fingerprint))
        {
            return Err(CoreError::ContextBoundary(
                "context entry is not canonical".into(),
            ));
        }
        if !self.seen.insert(entry.reference.clone()) {
            return Err(CoreError::ContextBoundary(
                "context reference was selected twice".into(),
            ));
        }
        self.entries.push(entry);
        Ok(())
    }

    pub fn freeze(
        &self,
        stage: ContextStage,
        max_items: usize,
        max_bytes: usize,
    ) -> CoreResult<ContextFreeze> {
        if max_items == 0 || max_bytes == 0 {
            return Err(CoreError::ContextBoundary(
                "context budget must be positive".into(),
            ));
        }
        let mut entries = Vec::new();
        let mut total_bytes = 0usize;
        for entry in &self.entries {
            if !entry.allowed_stages.contains(&stage) {
                continue;
            }
            if matches!(
                stage,
                ContextStage::BlindReader | ContextStage::IndependentReview
            ) && (entry.contains_private_state || entry.contains_corpus_identity)
            {
                return Err(CoreError::ContextBoundary(
                    "blind stage received private or treatment identity".into(),
                ));
            }
            if stage == ContextStage::Writer && entry.contains_private_state {
                return Err(CoreError::ContextBoundary(
                    "Writer received private character state".into(),
                ));
            }
            if entries.len() == max_items || total_bytes + entry.byte_size > max_bytes {
                break;
            }
            total_bytes += entry.byte_size;
            entries.push(entry.clone());
        }
        let bytes = serde_json::to_vec(&(stage, &entries, total_bytes))
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(ContextFreeze {
            schema: "quillframe_context_freeze_v1".into(),
            stage,
            entries,
            total_bytes,
            fingerprint: sha256_fingerprint(bytes),
        })
    }

    pub fn freeze_selected(
        &self,
        stage: ContextStage,
        selected_references: &[String],
        max_items: usize,
        max_bytes: usize,
    ) -> CoreResult<ContextFreeze> {
        if selected_references.is_empty() {
            return Err(CoreError::ContextBoundary(
                "semantic context selection is empty".into(),
            ));
        }
        let mut selected = BTreeSet::new();
        let mut manifest = ContextManifest::default();
        for reference in selected_references {
            if !selected.insert(reference) {
                return Err(CoreError::ContextBoundary(
                    "semantic context selected a reference twice".into(),
                ));
            }
            let entry = self
                .entries
                .iter()
                .find(|entry| &entry.reference == reference)
                .ok_or_else(|| {
                    CoreError::ContextBoundary(format!(
                        "semantic context selected unknown reference {reference}"
                    ))
                })?;
            manifest.select(entry.clone())?;
        }
        manifest.freeze(stage, max_items, max_bytes)
    }

    pub fn entries(&self) -> &[ContextEntry] {
        &self.entries
    }
}

impl ContextQueryPlan {
    pub fn validate(&self) -> CoreResult<()> {
        if self.queries.is_empty()
            || self.queries.len() > 6
            || self
                .queries
                .iter()
                .any(|query| query.trim().is_empty() || query.chars().count() > 80)
            || self.required_references.len() > 16
            || self
                .required_references
                .iter()
                .any(|reference| reference.trim().is_empty())
        {
            return Err(CoreError::ContextBoundary(
                "context query plan exceeds its bounded contract".into(),
            ));
        }
        let query_count = self.queries.iter().collect::<BTreeSet<_>>().len();
        let reference_count = self
            .required_references
            .iter()
            .collect::<BTreeSet<_>>()
            .len();
        if query_count != self.queries.len() || reference_count != self.required_references.len() {
            return Err(CoreError::ContextBoundary(
                "context query plan contains duplicate selectors".into(),
            ));
        }
        Ok(())
    }
}

impl ContextSelectionProposal {
    pub fn validate_against(&self, candidates: &[ContextEntry]) -> CoreResult<()> {
        if self.selected_references.is_empty() || self.selected_references.len() > 24 {
            return Err(CoreError::ContextBoundary(
                "context greenlight must select one to twenty-four references".into(),
            ));
        }
        let universe = candidates
            .iter()
            .map(|entry| entry.reference.as_str())
            .collect::<BTreeSet<_>>();
        let selected = self
            .selected_references
            .iter()
            .map(String::as_str)
            .collect::<BTreeSet<_>>();
        if selected.len() != self.selected_references.len()
            || selected
                .iter()
                .any(|reference| !universe.contains(reference))
        {
            return Err(CoreError::ContextBoundary(
                "context greenlight selected duplicate or unknown references".into(),
            ));
        }
        Ok(())
    }
}

fn canonical_fingerprint(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(reference: &str, summary: &str, stages: &[ContextStage]) -> ContextEntry {
        ContextEntry {
            reference: reference.into(),
            tier: ContextTier::SettledLedger,
            fingerprint: format!("sha256:{}", "a".repeat(64)),
            summary: summary.into(),
            byte_size: summary.len(),
            source_chapter_id: None,
            source_head_fingerprint: None,
            allowed_stages: stages.iter().copied().collect(),
            contains_manuscript_body: false,
            contains_private_state: false,
            contains_corpus_identity: false,
        }
    }

    #[test]
    fn freeze_is_bounded_instead_of_loading_a_whole_book() {
        let mut manifest = ContextManifest::default();
        for index in 0..10_000 {
            manifest
                .select(entry(
                    &format!("chapter-summary:{index}"),
                    "有界章节状态摘要",
                    &[ContextStage::Planning],
                ))
                .unwrap();
        }
        let frozen = manifest
            .freeze(ContextStage::Planning, 32, 4 * 1024)
            .unwrap();
        assert_eq!(frozen.entries.len(), 32);
        assert!(frozen.total_bytes <= 4 * 1024);
    }

    #[test]
    fn blind_reader_never_receives_corpus_identity() {
        let mut value = entry(
            "corpus:mechanism",
            "source-free mechanism",
            &[ContextStage::BlindReader],
        );
        value.contains_corpus_identity = true;
        let mut manifest = ContextManifest::default();
        manifest.select(value).unwrap();
        assert!(manifest.freeze(ContextStage::BlindReader, 4, 1024).is_err());
    }
}
