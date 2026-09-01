use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterPreferenceProjection {
    pub schema: String,
    pub hypothesis_id: String,
    pub scope: String,
    pub statement: String,
    pub version: u64,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct WriterPreferenceSelection {
    pub selected_hypothesis_ids: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FeedbackCaptureDecision {
    Capture,
    Skip,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FeedbackInterpretation {
    pub capture_decision: FeedbackCaptureDecision,
    pub scope: Option<String>,
    pub statement: Option<String>,
    pub reason: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PreferenceReviewDecision {
    Validated,
    Contested,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PreferenceReviewResult {
    pub decision: PreferenceReviewDecision,
    pub reason: String,
}

impl FeedbackInterpretation {
    pub fn validate(&self) -> CoreResult<()> {
        if self.reason.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "feedback interpretation reason is required".into(),
            ));
        }
        match self.capture_decision {
            FeedbackCaptureDecision::Capture
                if self.scope.as_deref().is_some_and(valid_scope)
                    && self
                        .statement
                        .as_deref()
                        .is_some_and(|value| !value.trim().is_empty()) =>
            {
                Ok(())
            }
            FeedbackCaptureDecision::Skip if self.scope.is_none() && self.statement.is_none() => {
                Ok(())
            }
            _ => Err(CoreError::InvalidProject(
                "feedback capture/skip fields are inconsistent".into(),
            )),
        }
    }
}

impl PreferenceReviewResult {
    pub fn validate(&self) -> CoreResult<()> {
        if self.reason.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "preference review reason is required".into(),
            ));
        }
        Ok(())
    }
}

fn valid_scope(scope: &str) -> bool {
    matches!(
        scope,
        "one_off" | "project" | "user_taste" | "general_craft"
    )
}

impl WriterPreferenceProjection {
    pub fn freeze(
        hypothesis_id: impl Into<String>,
        scope: impl Into<String>,
        statement: impl Into<String>,
        version: u64,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_writer_preference_projection_v1".into(),
            hypothesis_id: hypothesis_id.into(),
            scope: scope.into(),
            statement: statement.into(),
            version,
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
                "writer preference projection changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_writer_preference_projection_v1"
            || self.hypothesis_id.trim().is_empty()
            || self.statement.trim().is_empty()
            || self.version == 0
            || !matches!(
                self.scope.as_str(),
                "one_off" | "project" | "user_taste" | "general_craft"
            )
        {
            return Err(CoreError::InvalidProject(
                "writer preference projection is incomplete".into(),
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

impl WriterPreferenceSelection {
    pub fn validate_against(
        &self,
        candidates: &[WriterPreferenceProjection],
        explicitly_requested: &[String],
    ) -> CoreResult<()> {
        if self.selected_hypothesis_ids.len() > 12 {
            return Err(CoreError::ContextBoundary(
                "preference greenlight may select at most twelve hypotheses".into(),
            ));
        }
        let universe = candidates
            .iter()
            .map(|candidate| candidate.hypothesis_id.as_str())
            .collect::<BTreeSet<_>>();
        let selected = self
            .selected_hypothesis_ids
            .iter()
            .map(String::as_str)
            .collect::<BTreeSet<_>>();
        let requested = explicitly_requested
            .iter()
            .map(String::as_str)
            .collect::<BTreeSet<_>>();
        if selected.len() != self.selected_hypothesis_ids.len()
            || requested.len() != explicitly_requested.len()
            || selected.iter().any(|id| !universe.contains(id))
            || requested.iter().any(|id| !universe.contains(id))
            || requested.iter().any(|id| !selected.contains(id))
        {
            return Err(CoreError::ContextBoundary(
                "preference greenlight omitted explicit active choices or selected unknown ids"
                    .into(),
            ));
        }
        Ok(())
    }

    pub fn project(
        &self,
        candidates: &[WriterPreferenceProjection],
        explicitly_requested: &[String],
    ) -> CoreResult<Vec<WriterPreferenceProjection>> {
        self.validate_against(candidates, explicitly_requested)?;
        self.selected_hypothesis_ids
            .iter()
            .map(|id| {
                candidates
                    .iter()
                    .find(|candidate| &candidate.hypothesis_id == id)
                    .cloned()
                    .ok_or_else(|| {
                        CoreError::ContextBoundary("selected preference disappeared".into())
                    })
            })
            .collect()
    }
}
