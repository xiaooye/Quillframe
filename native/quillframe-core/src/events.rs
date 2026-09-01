use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StoryEvent {
    pub schema: String,
    pub event_id: Uuid,
    pub project_id: String,
    pub run_id: Option<String>,
    pub chapter_id: Option<String>,
    pub aggregate_kind: String,
    pub aggregate_id: String,
    pub event_kind: String,
    pub base_revision: u64,
    pub commit_revision: u64,
    pub payload: Value,
    pub payload_fingerprint: String,
    pub created_at: String,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StoryStateSnapshot {
    pub schema: String,
    pub snapshot_id: Uuid,
    pub project_id: String,
    pub through_revision: u64,
    pub through_event_seq: i64,
    pub through_event_fingerprint: String,
    pub event_chain_fingerprint: String,
    pub projection: Value,
    pub projection_fingerprint: String,
    pub reason: String,
    pub created_at: String,
    pub fingerprint: String,
}

impl StoryStateSnapshot {
    #[allow(clippy::too_many_arguments)]
    pub fn create(
        project_id: impl Into<String>,
        through_revision: u64,
        through_event_seq: i64,
        through_event_fingerprint: impl Into<String>,
        event_chain_fingerprint: impl Into<String>,
        projection: Value,
        reason: impl Into<String>,
        created_at: impl Into<String>,
    ) -> CoreResult<Self> {
        let projection_fingerprint = sha256_fingerprint(
            serde_json::to_vec(&projection)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let mut value = Self {
            schema: "quillframe_story_state_snapshot_v1".into(),
            snapshot_id: Uuid::new_v4(),
            project_id: project_id.into(),
            through_revision,
            through_event_seq,
            through_event_fingerprint: through_event_fingerprint.into(),
            event_chain_fingerprint: event_chain_fingerprint.into(),
            projection,
            projection_fingerprint,
            reason: reason.into(),
            created_at: created_at.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        let projection_fingerprint = sha256_fingerprint(
            serde_json::to_vec(&self.projection)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        if projection_fingerprint != self.projection_fingerprint
            || self.compute_fingerprint()? != self.fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "story state snapshot fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_story_state_snapshot_v1"
            || self.project_id.trim().is_empty()
            || self.through_revision == 0
            || self.through_event_seq <= 0
            || self.reason.trim().is_empty()
            || self.created_at.trim().is_empty()
            || !self.projection.is_object()
            || !canonical_fingerprint(&self.through_event_fingerprint)
            || !canonical_fingerprint(&self.event_chain_fingerprint)
            || !canonical_fingerprint(&self.projection_fingerprint)
        {
            return Err(CoreError::AuthorityConflict(
                "story state snapshot is incomplete".into(),
            ));
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }
}

fn canonical_fingerprint(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..].bytes().all(|byte| byte.is_ascii_hexdigit())
}

impl StoryEvent {
    #[allow(clippy::too_many_arguments)]
    pub fn create(
        project_id: impl Into<String>,
        run_id: Option<String>,
        chapter_id: Option<String>,
        aggregate_kind: impl Into<String>,
        aggregate_id: impl Into<String>,
        event_kind: impl Into<String>,
        base_revision: u64,
        payload: Value,
        created_at: impl Into<String>,
    ) -> CoreResult<Self> {
        let payload_bytes = serde_json::to_vec(&payload)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let mut value = Self {
            schema: "quillframe_story_event_v1".into(),
            event_id: Uuid::new_v4(),
            project_id: project_id.into(),
            run_id,
            chapter_id,
            aggregate_kind: aggregate_kind.into(),
            aggregate_id: aggregate_id.into(),
            event_kind: event_kind.into(),
            base_revision,
            commit_revision: base_revision.saturating_add(1),
            payload,
            payload_fingerprint: sha256_fingerprint(payload_bytes),
            created_at: created_at.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        let payload_bytes = serde_json::to_vec(&self.payload)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if self.payload_fingerprint != sha256_fingerprint(payload_bytes)
            || self.fingerprint != self.compute_fingerprint()?
        {
            return Err(CoreError::AuthorityConflict(
                "story event fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_story_event_v1"
            || self.project_id.trim().is_empty()
            || self.aggregate_kind.trim().is_empty()
            || self.aggregate_id.trim().is_empty()
            || self.event_kind.trim().is_empty()
            || self.created_at.trim().is_empty()
            || !self.payload.is_object()
            || self.commit_revision != self.base_revision.saturating_add(1)
        {
            return Err(CoreError::AuthorityConflict(
                "story event identity or revision is invalid".into(),
            ));
        }
        Ok(())
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        let bytes = serde_json::to_vec(&projection)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;

    #[test]
    fn story_event_binds_payload_and_monotonic_revision() {
        let event = StoryEvent::create(
            "BOOK",
            Some("RUN1".into()),
            Some("CH001".into()),
            "chapter",
            "CH001",
            "chapter_settled",
            4,
            json!({"candidate":"sha256:test"}),
            "T5",
        )
        .unwrap();
        assert_eq!(event.commit_revision, 5);
        event.validate().unwrap();
    }
}
