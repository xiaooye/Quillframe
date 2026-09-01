use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult, ModelRequest, ModelResult};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "SCREAMING-KEBAB-CASE")]
pub enum ProductionTaskMode {
    Draft,
    Revise,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BoundRuleMaterial {
    pub id: String,
    pub authority: String,
    pub statement: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepairBinding {
    pub source_run_id: String,
    pub source_checkpoint_id: String,
    pub expected_candidate_fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionIntent {
    pub instruction: String,
    pub reader_grip: String,
    pub author_profile: String,
    pub rule_material: Vec<BoundRuleMaterial>,
    pub selected_preference_ids: Vec<String>,
    pub repair_source: Option<RepairBinding>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionRequest {
    pub schema: String,
    pub run_id: String,
    pub task_mode: ProductionTaskMode,
    pub target_ref: String,
    pub intent: ProductionIntent,
    pub writer_pack_fingerprint: String,
    pub framework_build_fingerprint: String,
    pub route_policy: String,
    pub model_call_budget: Option<u32>,
    pub fingerprint: String,
}

impl ProductionRequest {
    #[allow(clippy::too_many_arguments)]
    pub fn freeze(
        run_id: impl Into<String>,
        task_mode: ProductionTaskMode,
        target_ref: impl Into<String>,
        intent: ProductionIntent,
        writer_pack_fingerprint: impl Into<String>,
        framework_build_fingerprint: impl Into<String>,
        route_policy: impl Into<String>,
        model_call_budget: Option<u32>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_production_request_v1".into(),
            run_id: run_id.into(),
            task_mode,
            target_ref: target_ref.into(),
            intent,
            writer_pack_fingerprint: writer_pack_fingerprint.into(),
            framework_build_fingerprint: framework_build_fingerprint.into(),
            route_policy: route_policy.into(),
            model_call_budget,
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = fingerprint(&value)?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        exact(&self.fingerprint, &fingerprint(self)?, "production request")
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_production_request_v1"
            || [&self.run_id, &self.target_ref, &self.route_policy]
                .iter()
                .any(|value| value.trim().is_empty())
        {
            return Err(CoreError::InvalidProject(
                "production request is incomplete".into(),
            ));
        }
        if self.intent.instruction.trim().is_empty()
            || !matches!(
                self.intent.reader_grip.as_str(),
                "low" | "medium" | "high" | "very_high"
            )
            || self.intent.author_profile.trim().is_empty()
            || self.intent.rule_material.iter().any(|rule| {
                rule.id.trim().is_empty()
                    || rule.authority.trim().is_empty()
                    || rule.statement.trim().is_empty()
            })
            || self
                .intent
                .selected_preference_ids
                .iter()
                .any(|value| value.trim().is_empty())
        {
            return Err(CoreError::InvalidProject(
                "production intent is incomplete".into(),
            ));
        }
        match (self.task_mode, &self.intent.repair_source) {
            (ProductionTaskMode::Draft, None) => {}
            (ProductionTaskMode::Revise, Some(binding))
                if !binding.source_run_id.trim().is_empty()
                    && !binding.source_checkpoint_id.trim().is_empty()
                    && require_fingerprint(&binding.expected_candidate_fingerprint).is_ok() => {}
            _ => {
                return Err(CoreError::InvalidProject(
                    "DRAFT cannot bind repair evidence and REVISE requires it".into(),
                ))
            }
        }
        require_fingerprint(&self.writer_pack_fingerprint)?;
        require_fingerprint(&self.framework_build_fingerprint)?;
        if self.model_call_budget == Some(0) {
            return Err(CoreError::InvalidProject(
                "model call budget cannot be zero".into(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StageJob {
    pub schema: String,
    pub stage_key: String,
    pub runtime_role: String,
    pub model_request: ModelRequest,
    pub input_fingerprint: String,
    pub fingerprint: String,
}

impl StageJob {
    pub fn freeze(
        stage_key: impl Into<String>,
        runtime_role: impl Into<String>,
        model_request: ModelRequest,
        input_fingerprint: impl Into<String>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_stage_job_v1".into(),
            stage_key: stage_key.into(),
            runtime_role: runtime_role.into(),
            model_request,
            input_fingerprint: input_fingerprint.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = fingerprint(&value)?;
        Ok(value)
    }
    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        exact(&self.fingerprint, &fingerprint(self)?, "stage job")
    }
    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_stage_job_v1"
            || self.stage_key.trim().is_empty()
            || self.runtime_role.trim().is_empty()
        {
            return Err(CoreError::InvalidProject("stage job is incomplete".into()));
        }
        require_fingerprint(&self.input_fingerprint)
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StageCallState {
    Dispatched,
    Confirmed,
    Unconfirmed,
    Cancelled,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StageCall {
    pub call_id: String,
    pub run_id: String,
    pub job: StageJob,
    pub owner_token: String,
    pub state: StageCallState,
    pub deadline_at_ms: u64,
    pub result: Option<ModelResult>,
    pub error_code: Option<String>,
}

fn fingerprint<T: Serialize + Clone + ClearFingerprint>(value: &T) -> CoreResult<String> {
    let mut copy = value.clone();
    copy.clear();
    serde_json::to_vec(&copy)
        .map(sha256_fingerprint)
        .map_err(|error| CoreError::Serialization(error.to_string()))
}
trait ClearFingerprint {
    fn clear(&mut self);
}
impl ClearFingerprint for ProductionRequest {
    fn clear(&mut self) {
        self.fingerprint.clear();
    }
}
impl ClearFingerprint for StageJob {
    fn clear(&mut self) {
        self.fingerprint.clear();
    }
}
fn exact(actual: &str, expected: &str, label: &str) -> CoreResult<()> {
    if actual != expected {
        return Err(CoreError::AuthorityConflict(format!(
            "{label} fingerprint changed"
        )));
    }
    Ok(())
}
fn require_fingerprint(value: &str) -> CoreResult<()> {
    if value.len() != 71
        || !value.starts_with("sha256:")
        || !value[7..].bytes().all(|byte| byte.is_ascii_hexdigit())
    {
        return Err(CoreError::AuthorityConflict(
            "runtime fingerprint is not canonical".into(),
        ));
    }
    Ok(())
}
