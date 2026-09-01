use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RevisionRequest {
    pub schema: String,
    pub request_id: Uuid,
    pub candidate_id: String,
    pub candidate_fingerprint: String,
    pub requested_by: String,
    pub reason: String,
    pub idempotency_key: String,
    pub created_at: String,
    pub fingerprint: String,
}

impl RevisionRequest {
    pub fn create(
        candidate_id: impl Into<String>,
        candidate_fingerprint: impl Into<String>,
        requested_by: impl Into<String>,
        reason: impl Into<String>,
        idempotency_key: impl Into<String>,
        created_at: impl Into<String>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_revision_request_v1".into(),
            request_id: Uuid::new_v4(),
            candidate_id: candidate_id.into(),
            candidate_fingerprint: candidate_fingerprint.into(),
            requested_by: requested_by.into(),
            reason: reason.into(),
            idempotency_key: idempotency_key.into(),
            created_at: created_at.into(),
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        exact(
            &self.fingerprint,
            &self.compute_fingerprint()?,
            "revision request",
        )
    }

    fn validate_fields(&self) -> CoreResult<()> {
        required([
            &self.candidate_id,
            &self.requested_by,
            &self.reason,
            &self.idempotency_key,
            &self.created_at,
        ])?;
        require_fingerprint(&self.candidate_fingerprint)
    }

    fn compute_fingerprint(&self) -> CoreResult<String> {
        fingerprint_of(self)
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AcceptanceDecision {
    pub schema: String,
    pub acceptance_id: Uuid,
    pub candidate_id: String,
    pub candidate_fingerprint: String,
    pub review_report_fingerprint: String,
    pub authorized_by: String,
    pub idempotency_key: String,
    pub created_at: String,
    pub fingerprint: String,
}

impl AcceptanceDecision {
    pub fn create(
        candidate_id: impl Into<String>,
        candidate_fingerprint: impl Into<String>,
        review_report_fingerprint: impl Into<String>,
        authorized_by: impl Into<String>,
        idempotency_key: impl Into<String>,
        created_at: impl Into<String>,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_acceptance_decision_v1".into(),
            acceptance_id: Uuid::new_v4(),
            candidate_id: candidate_id.into(),
            candidate_fingerprint: candidate_fingerprint.into(),
            review_report_fingerprint: review_report_fingerprint.into(),
            authorized_by: authorized_by.into(),
            idempotency_key: idempotency_key.into(),
            created_at: created_at.into(),
            fingerprint: String::new(),
        };
        required([
            &value.candidate_id,
            &value.authorized_by,
            &value.idempotency_key,
            &value.created_at,
        ])?;
        require_fingerprint(&value.candidate_fingerprint)?;
        require_fingerprint(&value.review_report_fingerprint)?;
        value.fingerprint = fingerprint_of(&value)?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        required([
            &self.candidate_id,
            &self.authorized_by,
            &self.idempotency_key,
            &self.created_at,
        ])?;
        require_fingerprint(&self.candidate_fingerprint)?;
        require_fingerprint(&self.review_report_fingerprint)?;
        exact(&self.fingerprint, &fingerprint_of(self)?, "acceptance")
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SettlementPreflight {
    pub schema: String,
    pub preflight_id: Uuid,
    pub acceptance_id: String,
    pub candidate_id: String,
    pub candidate_fingerprint: String,
    pub revision_id: String,
    pub target_ref: String,
    pub before_fingerprint: String,
    pub created_at: String,
    pub fingerprint: String,
}

impl SettlementPreflight {
    pub(crate) fn seal(&mut self) -> CoreResult<()> {
        self.fingerprint = fingerprint_of(self)?;
        Ok(())
    }

    pub fn validate(&self) -> CoreResult<()> {
        required([
            &self.acceptance_id,
            &self.candidate_id,
            &self.revision_id,
            &self.target_ref,
            &self.created_at,
        ])?;
        require_fingerprint(&self.candidate_fingerprint)?;
        require_fingerprint(&self.before_fingerprint)?;
        exact(
            &self.fingerprint,
            &fingerprint_of(self)?,
            "settlement preflight",
        )
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SettlementAuthorization {
    pub schema: String,
    pub settlement_id: Uuid,
    pub acceptance_id: String,
    pub target_ref: String,
    pub preflight_fingerprint: String,
    pub expected_before_fingerprint: String,
    pub authorized_by: String,
    pub idempotency_key: String,
    pub created_at: String,
    pub fingerprint: String,
}

impl SettlementAuthorization {
    pub fn create(
        preflight: &SettlementPreflight,
        authorized_by: impl Into<String>,
        idempotency_key: impl Into<String>,
        created_at: impl Into<String>,
    ) -> CoreResult<Self> {
        preflight.validate()?;
        let mut value = Self {
            schema: "quillframe_settlement_authorization_v1".into(),
            settlement_id: Uuid::new_v4(),
            acceptance_id: preflight.acceptance_id.clone(),
            target_ref: preflight.target_ref.clone(),
            preflight_fingerprint: preflight.fingerprint.clone(),
            expected_before_fingerprint: preflight.before_fingerprint.clone(),
            authorized_by: authorized_by.into(),
            idempotency_key: idempotency_key.into(),
            created_at: created_at.into(),
            fingerprint: String::new(),
        };
        required([
            &value.acceptance_id,
            &value.target_ref,
            &value.authorized_by,
            &value.idempotency_key,
            &value.created_at,
        ])?;
        value.fingerprint = fingerprint_of(&value)?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        required([
            &self.acceptance_id,
            &self.target_ref,
            &self.authorized_by,
            &self.idempotency_key,
            &self.created_at,
        ])?;
        require_fingerprint(&self.preflight_fingerprint)?;
        require_fingerprint(&self.expected_before_fingerprint)?;
        exact(
            &self.fingerprint,
            &fingerprint_of(self)?,
            "settlement authorization",
        )
    }
}

fn fingerprint_of<T>(value: &T) -> CoreResult<String>
where
    T: Serialize + Clone + FingerprintProjection,
{
    let mut copy = value.clone();
    copy.clear_fingerprint();
    serde_json::to_vec(&copy)
        .map(sha256_fingerprint)
        .map_err(|error| CoreError::Serialization(error.to_string()))
}

trait FingerprintProjection {
    fn clear_fingerprint(&mut self);
}

macro_rules! projection {
    ($type:ty) => {
        impl FingerprintProjection for $type {
            fn clear_fingerprint(&mut self) {
                self.fingerprint.clear();
            }
        }
    };
}
projection!(RevisionRequest);
projection!(AcceptanceDecision);
projection!(SettlementAuthorization);

impl FingerprintProjection for SettlementPreflight {
    fn clear_fingerprint(&mut self) {
        self.fingerprint.clear();
        // A preflight is a read-only view. Its authority fingerprint is derived from
        // the accepted candidate, target and current Canon state, not query metadata.
        self.preflight_id = Uuid::nil();
        self.created_at.clear();
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

fn required<'a>(values: impl IntoIterator<Item = &'a String>) -> CoreResult<()> {
    if values.into_iter().any(|value| value.trim().is_empty()) {
        return Err(CoreError::AuthorityConflict(
            "author decision fields must be non-empty".into(),
        ));
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
        return Err(CoreError::AuthorityConflict(
            "decision fingerprint binding is not canonical".into(),
        ));
    }
    Ok(())
}
