use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    S1,
    S2,
    S3,
    S4,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FindingCategory {
    Structure,
    Character,
    Prose,
    Consistency,
    Platform,
    Factual,
    Format,
    Causal,
    RuleBoundary,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ReviewMode {
    Full,
    Lean,
    Solo,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ReviewDecision {
    Accept,
    Revise,
    InfrastructureFailed,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReviewFinding {
    pub finding_id: String,
    pub reviewer_role: String,
    pub severity: Severity,
    pub category: FindingCategory,
    pub location: String,
    pub evidence: String,
    pub issue: String,
    pub fix_direction: String,
    pub inherited_from: Option<String>,
}

impl ReviewFinding {
    fn validate(&self) -> CoreResult<()> {
        for (field, value) in [
            ("finding_id", &self.finding_id),
            ("reviewer_role", &self.reviewer_role),
            ("location", &self.location),
            ("evidence", &self.evidence),
            ("issue", &self.issue),
            ("fix_direction", &self.fix_direction),
        ] {
            if value.trim().is_empty() {
                return Err(CoreError::InvalidProject(format!(
                    "review finding {field} is empty"
                )));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReviewReport {
    pub schema: String,
    pub candidate_fingerprint: String,
    pub mode: ReviewMode,
    pub reviewer_sessions: BTreeSet<String>,
    pub independent_context: bool,
    pub deterministic_prechecks: Vec<String>,
    pub findings: Vec<ReviewFinding>,
    pub disagreements: Vec<String>,
    pub decision: ReviewDecision,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReviewReportInput {
    pub candidate_fingerprint: String,
    pub mode: ReviewMode,
    pub reviewer_sessions: BTreeSet<String>,
    pub independent_context: bool,
    pub deterministic_prechecks: Vec<String>,
    pub findings: Vec<ReviewFinding>,
    pub disagreements: Vec<String>,
    pub infrastructure_failed: bool,
}

impl ReviewReport {
    pub fn create(input: ReviewReportInput) -> CoreResult<Self> {
        let ReviewReportInput {
            candidate_fingerprint,
            mode,
            reviewer_sessions,
            independent_context,
            deterministic_prechecks,
            findings,
            disagreements,
            infrastructure_failed,
        } = input;
        for finding in &findings {
            finding.validate()?;
        }
        let mut value = Self {
            schema: "quillframe_review_report_v1".into(),
            candidate_fingerprint,
            mode,
            reviewer_sessions,
            independent_context,
            deterministic_prechecks,
            findings,
            disagreements,
            decision: ReviewDecision::Accept,
            fingerprint: String::new(),
        };
        if !fingerprint(&value.candidate_fingerprint) {
            return Err(CoreError::InvalidProject(
                "review candidate fingerprint is not canonical".into(),
            ));
        }
        value.validate_reviewers()?;
        value.decision = if infrastructure_failed {
            ReviewDecision::InfrastructureFailed
        } else if value.findings.is_empty() {
            ReviewDecision::Accept
        } else {
            ReviewDecision::Revise
        };
        value.fingerprint = value.compute_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self, current_candidate_fingerprint: &str) -> CoreResult<()> {
        if self.candidate_fingerprint != current_candidate_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "review is stale for the current candidate".into(),
            ));
        }
        self.validate_reviewers()?;
        if self.fingerprint != self.compute_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "review report fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    fn validate_reviewers(&self) -> CoreResult<()> {
        let required = match self.mode {
            ReviewMode::Full => 4,
            ReviewMode::Lean => 2,
            ReviewMode::Solo => 1,
        };
        if self.reviewer_sessions.len() < required {
            return Err(CoreError::ContextBoundary(
                "review mode does not have enough distinct reviewer sessions".into(),
            ));
        }
        if self.mode != ReviewMode::Solo && !self.independent_context {
            return Err(CoreError::ContextBoundary(
                "multi-review mode requires genuinely independent contexts".into(),
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

    #[test]
    fn rejection_is_a_revision_decision_and_disagreement_is_preserved() {
        let report = ReviewReport::create(ReviewReportInput {
            candidate_fingerprint: format!("sha256:{}", "a".repeat(64)),
            mode: ReviewMode::Lean,
            reviewer_sessions: BTreeSet::from(["architect".into(), "consistency".into()]),
            independent_context: true,
            deterministic_prechecks: vec!["format-ok".into()],
            findings: vec![ReviewFinding {
                finding_id: "F-001".into(),
                reviewer_role: "architect".into(),
                severity: Severity::S2,
                category: FindingCategory::Causal,
                location: "scene:2".into(),
                evidence: "角色无新信息却改变决定".into(),
                issue: "因果跳跃".into(),
                fix_direction: "补入能改变决定的新证据".into(),
                inherited_from: None,
            }],
            disagreements: vec!["结构审查要求补场，连贯性审查认为可用一句对白解决".into()],
            infrastructure_failed: false,
        })
        .unwrap();
        assert_eq!(report.decision, ReviewDecision::Revise);
        assert_eq!(report.disagreements.len(), 1);
    }
}
