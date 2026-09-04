use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use quillframe_native::read_guarded_file;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::{fingerprint::sha256_fingerprint, BookSetupSourceEvidence, CoreError, CoreResult};

const FUNDAMENTALS_ZH_CN: &str = include_str!("../../../surface/FUNDAMENTALS.zh-CN.md");
const FUNDAMENTALS_EN: &str = include_str!("../../../surface/FUNDAMENTALS.en.md");
const WRITER_GUIDANCE_ZH_CN: &str = include_str!("../../../surface/craft/cards/core.zh-CN.md");
const WRITER_GUIDANCE_EN: &str = include_str!("../../../surface/craft/cards/core.en.md");
const QUALITY_CONTRACTS: &str =
    include_str!("../../../harness/semantic_workers/contracts/quality.json");
const MAX_GUIDANCE_SOURCES: usize = 8;
const MAX_SOURCE_BYTES: usize = 64 * 1024;
const MAX_TOTAL_SOURCE_BYTES: usize = 160 * 1024;

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProjectGuidanceInput {
    pub source_id: String,
    pub content: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FrozenGuidanceSource {
    pub source_id: String,
    pub source_kind: String,
    pub source_uri: String,
    pub source_revision: String,
    pub role: String,
    pub content: String,
    pub content_fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionGuidanceSnapshot {
    pub schema: String,
    pub language: String,
    pub writer_guidance: String,
    pub writer_guidance_fingerprint: String,
    pub surface_fundamentals: String,
    pub surface_fundamentals_fingerprint: String,
    pub surface_rule_ids: Vec<String>,
    pub surface_audit_rubric: Value,
    pub surface_audit_rubric_fingerprint: String,
    pub project_sources: Vec<FrozenGuidanceSource>,
    pub fingerprint: String,
}

impl ProductionGuidanceSnapshot {
    pub fn freeze(
        language: &str,
        inputs: Vec<ProjectGuidanceInput>,
        approved_sources: &[BookSetupSourceEvidence],
    ) -> CoreResult<Self> {
        let (writer_guidance, surface_fundamentals) = if language.starts_with("zh") {
            (WRITER_GUIDANCE_ZH_CN, FUNDAMENTALS_ZH_CN)
        } else {
            (WRITER_GUIDANCE_EN, FUNDAMENTALS_EN)
        };
        let approved = approved_sources
            .iter()
            .map(|source| (source.source_id.as_str(), source))
            .collect::<BTreeMap<_, _>>();
        if inputs.len() > MAX_GUIDANCE_SOURCES {
            return Err(CoreError::ContextBoundary(
                "production guidance has too many project sources".into(),
            ));
        }
        let mut seen = BTreeSet::new();
        let mut total_bytes = 0usize;
        let mut project_sources = Vec::with_capacity(inputs.len());
        for input in inputs {
            if input.source_id.trim().is_empty() || input.content.trim().is_empty() {
                return Err(CoreError::InvalidProject(
                    "project guidance source id and content are required".into(),
                ));
            }
            if !seen.insert(input.source_id.clone()) {
                return Err(CoreError::InvalidProject(
                    "project guidance source ids must be unique".into(),
                ));
            }
            let source = approved.get(input.source_id.as_str()).ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "project guidance is not bound to the approved Book Setup".into(),
                )
            })?;
            if !writer_guidance_eligible(source) {
                return Err(CoreError::AuthorityConflict(
                    "approved source is not designated as prose, voice, style, or calibration guidance"
                        .into(),
                ));
            }
            let source_bytes = input.content.len();
            if source_bytes > MAX_SOURCE_BYTES {
                return Err(CoreError::ContextBoundary(
                    "project guidance source exceeds 64 KiB".into(),
                ));
            }
            total_bytes = total_bytes.checked_add(source_bytes).ok_or_else(|| {
                CoreError::ContextBoundary("project guidance byte budget overflowed".into())
            })?;
            if total_bytes > MAX_TOTAL_SOURCE_BYTES {
                return Err(CoreError::ContextBoundary(
                    "project guidance sources exceed 160 KiB".into(),
                ));
            }
            let content_fingerprint = sha256_fingerprint(input.content.as_bytes());
            if content_fingerprint != source.content_fingerprint {
                return Err(CoreError::AuthorityConflict(format!(
                    "project guidance source {} differs from its approved fingerprint",
                    input.source_id
                )));
            }
            project_sources.push(FrozenGuidanceSource {
                source_id: source.source_id.clone(),
                source_kind: source.source_kind.clone(),
                source_uri: source.source_uri.clone(),
                source_revision: source.source_revision.clone(),
                role: source.role.clone(),
                content: input.content,
                content_fingerprint,
            });
        }
        let contract_registry = serde_json::from_str::<Value>(QUALITY_CONTRACTS)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let semantic_rule_contract = contract_registry
            .pointer("/contracts/quality.semantic_rule_audit")
            .ok_or_else(|| {
                CoreError::InvalidProject(
                    "quality contract registry has no semantic rule audit".into(),
                )
            })?;
        let surface_audit_rubric = serde_json::json!({
            "contract_id":"quality.semantic_rule_audit",
            "registry_version":contract_registry.get("version"),
            "kind":semantic_rule_contract.get("kind"),
            "purpose":semantic_rule_contract.get("purpose"),
            "rubric":semantic_rule_contract.get("rubric"),
            "permissions":semantic_rule_contract.get("permissions")
        });
        let surface_audit_rubric_fingerprint = sha256_fingerprint(
            &serde_json::to_vec(&surface_audit_rubric)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let mut value = Self {
            schema: "quillframe_production_guidance_snapshot_v1".into(),
            language: language.into(),
            writer_guidance: writer_guidance.into(),
            writer_guidance_fingerprint: sha256_fingerprint(writer_guidance.as_bytes()),
            surface_fundamentals: surface_fundamentals.into(),
            surface_fundamentals_fingerprint: sha256_fingerprint(surface_fundamentals.as_bytes()),
            surface_rule_ids: surface_rule_ids(surface_fundamentals)?,
            surface_audit_rubric,
            surface_audit_rubric_fingerprint,
            project_sources,
            fingerprint: String::new(),
        };
        value.validate_fields()?;
        value.fingerprint = value.expected_fingerprint()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        self.validate_fields()?;
        if self.fingerprint != self.expected_fingerprint()? {
            return Err(CoreError::AuthorityConflict(
                "production guidance snapshot fingerprint changed".into(),
            ));
        }
        Ok(())
    }

    pub fn writer_projection(&self) -> serde_json::Value {
        serde_json::json!({
            "schema":"quillframe_writer_guidance_projection_v1",
            "guidance_snapshot_fingerprint":self.fingerprint,
            "framework":{"content":self.writer_guidance,"fingerprint":self.writer_guidance_fingerprint},
            "project_sources":self.project_source_projection()
        })
    }

    pub fn audit_project_projection(&self) -> Value {
        Value::Array(self.project_source_projection())
    }

    fn project_source_projection(&self) -> Vec<Value> {
        self.project_sources
            .iter()
            .enumerate()
            .map(|(index, source)| {
                serde_json::json!({
                    "guidance_slot":index + 1,"content":source.content,
                    "content_fingerprint":source.content_fingerprint
                })
            })
            .collect()
    }

    fn validate_fields(&self) -> CoreResult<()> {
        if self.schema != "quillframe_production_guidance_snapshot_v1"
            || self.language.trim().is_empty()
            || self.writer_guidance.trim().is_empty()
            || self.surface_fundamentals.trim().is_empty()
            || self.surface_rule_ids != expected_rule_ids()
            || self.project_sources.len() > MAX_GUIDANCE_SOURCES
        {
            return Err(CoreError::InvalidProject(
                "production guidance snapshot is incomplete".into(),
            ));
        }
        if sha256_fingerprint(self.writer_guidance.as_bytes()) != self.writer_guidance_fingerprint
            || sha256_fingerprint(self.surface_fundamentals.as_bytes())
                != self.surface_fundamentals_fingerprint
            || sha256_fingerprint(
                &serde_json::to_vec(&self.surface_audit_rubric)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?,
            ) != self.surface_audit_rubric_fingerprint
            || self
                .surface_audit_rubric
                .pointer("/permissions/canon_write")
                .and_then(Value::as_bool)
                != Some(false)
            || self
                .surface_audit_rubric
                .pointer("/permissions/framework_behavior_write")
                .and_then(Value::as_bool)
                != Some(false)
        {
            return Err(CoreError::AuthorityConflict(
                "production guidance framework content changed".into(),
            ));
        }
        let mut seen = BTreeSet::new();
        let mut total_bytes = 0usize;
        for source in &self.project_sources {
            if !seen.insert(source.source_id.as_str())
                || [
                    &source.source_id,
                    &source.source_kind,
                    &source.source_uri,
                    &source.source_revision,
                    &source.role,
                    &source.content,
                ]
                .into_iter()
                .any(|value| value.trim().is_empty())
                || sha256_fingerprint(source.content.as_bytes()) != source.content_fingerprint
                || source.content.len() > MAX_SOURCE_BYTES
            {
                return Err(CoreError::InvalidProject(
                    "frozen project guidance source is invalid".into(),
                ));
            }
            total_bytes = total_bytes
                .checked_add(source.content.len())
                .ok_or_else(|| {
                    CoreError::ContextBoundary("project guidance byte budget overflowed".into())
                })?;
        }
        if total_bytes > MAX_TOTAL_SOURCE_BYTES {
            return Err(CoreError::ContextBoundary(
                "project guidance sources exceed 160 KiB".into(),
            ));
        }
        Ok(())
    }

    fn expected_fingerprint(&self) -> CoreResult<String> {
        let mut projection = self.clone();
        projection.fingerprint.clear();
        serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }
}

pub fn materialize_approved_guidance_inputs(
    approved_sources: &[BookSetupSourceEvidence],
    project_root: &Path,
) -> CoreResult<Vec<ProjectGuidanceInput>> {
    let eligible = approved_sources
        .iter()
        .filter(|source| writer_guidance_eligible(source))
        .collect::<Vec<_>>();
    if eligible.len() > MAX_GUIDANCE_SOURCES {
        return Err(CoreError::ContextBoundary(
            "approved production guidance has too many sources".into(),
        ));
    }
    let mut inputs = Vec::with_capacity(eligible.len());
    let mut total_bytes = 0usize;
    for source in eligible {
        let path = if let Some(relative) = source.source_uri.strip_prefix("project:") {
            let relative = Path::new(relative.trim_start_matches(['/', '\\']));
            if relative.as_os_str().is_empty() || relative.is_absolute() {
                return Err(CoreError::AuthorityConflict(format!(
                    "approved production guidance source {} has an invalid project URI",
                    source.source_id
                )));
            }
            project_root.join(relative)
        } else {
            let absolute = Path::new(&source.source_uri);
            if !absolute.is_absolute() {
                return Err(CoreError::AuthorityConflict(format!(
                    "approved production guidance source {} is not a native or project path",
                    source.source_id
                )));
            }
            absolute.to_path_buf()
        };
        let (bytes, _) = read_guarded_file(&path, MAX_SOURCE_BYTES as u64)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        total_bytes = total_bytes.checked_add(bytes.len()).ok_or_else(|| {
            CoreError::ContextBoundary("project guidance byte budget overflowed".into())
        })?;
        if total_bytes > MAX_TOTAL_SOURCE_BYTES {
            return Err(CoreError::ContextBoundary(
                "project guidance sources exceed 160 KiB".into(),
            ));
        }
        let content = String::from_utf8(bytes).map_err(|_| {
            CoreError::InvalidProject("project guidance source must be UTF-8".into())
        })?;
        if sha256_fingerprint(content.as_bytes()) != source.content_fingerprint {
            return Err(CoreError::AuthorityConflict(format!(
                "project guidance source {} differs from its approved fingerprint",
                source.source_id
            )));
        }
        inputs.push(ProjectGuidanceInput {
            source_id: source.source_id.clone(),
            content,
        });
    }
    Ok(inputs)
}

pub fn framework_guidance_fingerprint() -> String {
    sha256_fingerprint(
        [
            FUNDAMENTALS_ZH_CN,
            FUNDAMENTALS_EN,
            WRITER_GUIDANCE_ZH_CN,
            WRITER_GUIDANCE_EN,
            QUALITY_CONTRACTS,
        ]
        .join("\n")
        .as_bytes(),
    )
}

fn surface_rule_ids(content: &str) -> CoreResult<Vec<String>> {
    let mut found = BTreeSet::new();
    for line in content.lines() {
        let Some(rest) = line.trim().strip_prefix("### HF-") else {
            continue;
        };
        let digits = rest.chars().take(2).collect::<String>();
        if digits.len() == 2 && digits.bytes().all(|byte| byte.is_ascii_digit()) {
            found.insert(format!("HF-{digits}"));
        }
    }
    let values = found.into_iter().collect::<Vec<_>>();
    if values != expected_rule_ids() {
        return Err(CoreError::InvalidProject(
            "Surface Fundamentals must define exactly HF-01 through HF-30".into(),
        ));
    }
    Ok(values)
}

fn writer_guidance_eligible(source: &BookSetupSourceEvidence) -> bool {
    let role = source.role.to_lowercase();
    [
        "prose",
        "voice",
        "style",
        "calibration",
        "行文",
        "文风",
        "校准",
    ]
    .iter()
    .any(|marker| role.contains(marker))
}

pub fn expected_rule_ids() -> Vec<String> {
    (1..=30).map(|index| format!("HF-{index:02}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approved(content: &str) -> BookSetupSourceEvidence {
        BookSetupSourceEvidence {
            source_id: "PROFILE".into(),
            source_kind: "project_profile".into(),
            source_uri: "project:profiles/prose.md".into(),
            source_revision: "revision:1".into(),
            content_fingerprint: sha256_fingerprint(content.as_bytes()),
            role: "Project prose profile".into(),
        }
    }

    #[test]
    fn guidance_freezes_framework_rules_and_approved_project_content() {
        let content = "项目正文规则";
        let snapshot = ProductionGuidanceSnapshot::freeze(
            "zh-CN",
            vec![ProjectGuidanceInput {
                source_id: "PROFILE".into(),
                content: content.into(),
            }],
            &[approved(content)],
        )
        .unwrap();
        snapshot.validate().unwrap();
        assert_eq!(snapshot.surface_rule_ids, expected_rule_ids());
        assert!(snapshot.writer_guidance.contains("行动—回应—后果"));
        assert_eq!(
            snapshot
                .surface_audit_rubric
                .get("contract_id")
                .and_then(Value::as_str),
            Some("quality.semantic_rule_audit")
        );
        assert_eq!(snapshot.project_sources[0].content, content);
        let external = snapshot.writer_projection().to_string();
        assert!(!external.contains("PROFILE"));
        assert!(!external.contains("Project prose profile"));
    }

    #[test]
    fn approved_native_project_guidance_materializes_with_exact_bytes() {
        let path = std::env::temp_dir().join(format!(
            "qf-guidance-{}-{}.md",
            std::process::id(),
            uuid::Uuid::new_v4()
        ));
        std::fs::write(&path, "项目行文规则\r\n保留原始换行").unwrap();
        let bytes = std::fs::read(&path).unwrap();
        let source = BookSetupSourceEvidence {
            source_id: "PROFILE".into(),
            source_kind: "authorized_project_projection".into(),
            source_uri: path.to_string_lossy().into_owned(),
            source_revision: "revision:1".into(),
            content_fingerprint: sha256_fingerprint(&bytes),
            role: "Project prose profile".into(),
        };
        let materialized =
            materialize_approved_guidance_inputs(&[source], Path::new("unused-project-root"))
                .unwrap();
        assert_eq!(materialized[0].content.as_bytes(), bytes);
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn guidance_rejects_unapproved_or_changed_project_content() {
        assert!(ProductionGuidanceSnapshot::freeze(
            "zh-CN",
            vec![ProjectGuidanceInput {
                source_id: "OTHER".into(),
                content: "内容".into(),
            }],
            &[approved("内容")],
        )
        .is_err());
        assert!(ProductionGuidanceSnapshot::freeze(
            "zh-CN",
            vec![ProjectGuidanceInput {
                source_id: "PROFILE".into(),
                content: "已改变".into(),
            }],
            &[approved("原内容")],
        )
        .is_err());
        let mut non_guidance = approved("内容");
        non_guidance.role = "Historical plot evidence".into();
        assert!(ProductionGuidanceSnapshot::freeze(
            "zh-CN",
            vec![ProjectGuidanceInput {
                source_id: "PROFILE".into(),
                content: "内容".into(),
            }],
            &[non_guidance],
        )
        .is_err());
    }
}
