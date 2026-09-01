use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

const DERIVED_CONTEXT_MAX_BYTES: usize = 12 * 1024;
const CHAPTER_RECORD_TARGET_BYTES: usize = 1536;
const CHAPTER_RECORD_MAX_BYTES: usize = 3072;
const CHARACTER_SNAPSHOT_MAX_BYTES: usize = 8192;

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ChapterTrackingRecord {
    pub chapter_id: String,
    pub reading_order: u32,
    pub net_change: String,
    pub open_expectations: Vec<String>,
    pub paid_expectations: Vec<String>,
    pub relationship_changes: Vec<String>,
    pub state_changes: Vec<String>,
    pub next_pull: String,
    pub source_candidate_fingerprint: String,
}

impl ChapterTrackingRecord {
    pub fn encoded_size(&self) -> CoreResult<usize> {
        serde_json::to_vec(self)
            .map(|bytes| bytes.len())
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }

    pub fn validate(&self) -> CoreResult<()> {
        if self.chapter_id.trim().is_empty()
            || self.reading_order == 0
            || self.net_change.trim().is_empty()
            || self.next_pull.trim().is_empty()
            || !fingerprint(&self.source_candidate_fingerprint)
        {
            return Err(CoreError::InvalidProject(
                "chapter tracking record is incomplete".into(),
            ));
        }
        if self.encoded_size()? > CHAPTER_RECORD_MAX_BYTES {
            return Err(CoreError::ContextBoundary(format!(
                "chapter tracking record exceeds {CHAPTER_RECORD_MAX_BYTES} bytes"
            )));
        }
        Ok(())
    }

    pub fn exceeds_target(&self) -> CoreResult<bool> {
        Ok(self.encoded_size()? > CHAPTER_RECORD_TARGET_BYTES)
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TrackingState {
    pub schema: String,
    pub project_id: String,
    pub version: u64,
    pub chapters: BTreeMap<String, ChapterTrackingRecord>,
    pub character_snapshots: BTreeMap<String, String>,
    pub invalidated_chapters: BTreeSet<String>,
    pub fingerprint: String,
}

impl TrackingState {
    pub fn empty(project_id: impl Into<String>) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_tracking_state_v1".into(),
            project_id: project_id.into(),
            version: 0,
            chapters: BTreeMap::new(),
            character_snapshots: BTreeMap::new(),
            invalidated_chapters: BTreeSet::new(),
            fingerprint: String::new(),
        };
        if value.project_id.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "tracking project id is empty".into(),
            ));
        }
        value.refresh_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        for record in self.chapters.values() {
            record.validate()?;
        }
        for snapshot in self.character_snapshots.values() {
            if snapshot.len() > CHARACTER_SNAPSHOT_MAX_BYTES {
                return Err(CoreError::ContextBoundary(
                    "character snapshot exceeds 8192 bytes".into(),
                ));
            }
        }
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "tracking state fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn refresh_fingerprint(&mut self) -> CoreResult<()> {
        self.fingerprint = self.compute_fingerprint()?;
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

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TrackingLedger {
    current: TrackingState,
}

impl TrackingLedger {
    pub fn new(state: TrackingState) -> CoreResult<Self> {
        state.validate()?;
        Ok(Self { current: state })
    }

    pub fn current(&self) -> &TrackingState {
        &self.current
    }

    pub fn transact(
        &mut self,
        expected_version: u64,
        expected_fingerprint: &str,
        mutate: impl FnOnce(&mut TrackingState) -> CoreResult<()>,
    ) -> CoreResult<&TrackingState> {
        if self.current.version != expected_version
            || self.current.fingerprint != expected_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "tracking state compare-and-swap conflict".into(),
            ));
        }
        let mut next = self.current.clone();
        mutate(&mut next)?;
        next.version += 1;
        next.refresh_fingerprint()?;
        next.validate()?;
        self.current = next;
        Ok(&self.current)
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DerivedTrackingContext {
    pub chapter_id: String,
    pub net_change: String,
    pub open_expectations: String,
    pub paid_expectations: String,
    pub relationship_changes: String,
    pub state_changes: String,
    pub next_pull: String,
}

impl DerivedTrackingContext {
    pub fn from_record(record: &ChapterTrackingRecord) -> CoreResult<Self> {
        record.validate()?;
        let value = Self {
            chapter_id: record.chapter_id.clone(),
            net_change: record.net_change.clone(),
            open_expectations: record.open_expectations.join("；"),
            paid_expectations: record.paid_expectations.join("；"),
            relationship_changes: record.relationship_changes.join("；"),
            state_changes: record.state_changes.join("；"),
            next_pull: record.next_pull.clone(),
        };
        if serde_json::to_vec(&value)
            .map_err(|error| CoreError::Serialization(error.to_string()))?
            .len()
            > DERIVED_CONTEXT_MAX_BYTES
        {
            return Err(CoreError::ContextBoundary(
                "derived tracking context exceeds 12 KiB".into(),
            ));
        }
        Ok(value)
    }
}

fn fingerprint(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..]
            .chars()
            .all(|character| character.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record() -> ChapterTrackingRecord {
        ChapterTrackingRecord {
            chapter_id: "CH001".into(),
            reading_order: 1,
            net_change: "主角救出同伴但暴露身份".into(),
            open_expectations: vec!["能否甩掉追兵".into()],
            paid_expectations: vec!["找到失踪同伴".into()],
            relationship_changes: vec!["同伴从怀疑转为信任".into()],
            state_changes: vec!["身份已暴露".into()],
            next_pull: "追兵封锁下一出口".into(),
            source_candidate_fingerprint: format!("sha256:{}", "a".repeat(64)),
        }
    }

    #[test]
    fn tracking_is_transactional_authority_not_markdown_reverse_parsing() {
        let state = TrackingState::empty("BOOK").unwrap();
        let version = state.version;
        let fingerprint = state.fingerprint.clone();
        let mut ledger = TrackingLedger::new(state).unwrap();
        ledger
            .transact(version, &fingerprint, |next| {
                next.chapters.insert("CH001".into(), record());
                Ok(())
            })
            .unwrap();
        assert_eq!(ledger.current().version, 1);
        assert!(ledger.transact(version, &fingerprint, |_| Ok(())).is_err());
        DerivedTrackingContext::from_record(&record()).unwrap();
    }
}
