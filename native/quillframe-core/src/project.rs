use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

pub const PROJECT_SCHEMA: &str = "quillframe_project_v1_0";
pub const PROJECT_CONTEXT_SCHEMA: &str = "quillframe_project_context_v1_0";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProjectManifest {
    pub schema: String,
    pub id: String,
    pub title: String,
    pub language: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProjectContext {
    pub context_schema: String,
    pub scope: String,
    pub project_root: PathBuf,
    pub data_root: PathBuf,
    pub manifest: ProjectManifest,
    pub manifest_fingerprint: String,
    pub manifest_raw_fingerprint: String,
}

impl ProjectManifest {
    pub fn new(
        id: impl Into<String>,
        title: impl Into<String>,
        language: impl Into<String>,
    ) -> CoreResult<Self> {
        let value = Self {
            schema: PROJECT_SCHEMA.to_owned(),
            id: id.into(),
            title: title.into(),
            language: language.into(),
        };
        value.validate()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        if self.schema != PROJECT_SCHEMA {
            return Err(CoreError::InvalidProject(format!(
                "schema must be exactly {PROJECT_SCHEMA}"
            )));
        }
        if !valid_project_id(&self.id) {
            return Err(CoreError::InvalidProject(
                "project id is not canonical".into(),
            ));
        }
        if self.title.trim().is_empty() || self.title != self.title.trim() {
            return Err(CoreError::InvalidProject(
                "title must be non-empty and trimmed".into(),
            ));
        }
        if self.language.trim().is_empty() || self.language != self.language.trim() {
            return Err(CoreError::InvalidProject(
                "language must be non-empty and trimmed".into(),
            ));
        }
        Ok(())
    }

    pub fn from_toml_bytes(bytes: &[u8]) -> CoreResult<Self> {
        let source = std::str::from_utf8(bytes)
            .map_err(|_| CoreError::InvalidProject("manifest must be UTF-8".into()))?;
        let value: Self = toml::from_str(source)
            .map_err(|error| CoreError::InvalidProject(format!("invalid manifest: {error}")))?;
        value.validate()?;
        Ok(value)
    }

    pub fn to_toml_bytes(&self) -> CoreResult<Vec<u8>> {
        self.validate()?;
        toml::to_string(self)
            .map(String::into_bytes)
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }

    pub fn canonical_fingerprint(&self) -> CoreResult<String> {
        self.validate()?;
        let fields = BTreeMap::from([
            ("id", self.id.as_str()),
            ("language", self.language.as_str()),
            ("schema", self.schema.as_str()),
            ("title", self.title.as_str()),
        ]);
        let bytes = serde_json::to_vec(&fields)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(sha256_fingerprint(bytes))
    }

    pub fn resolve(root: &Path, manifest_bytes: &[u8]) -> CoreResult<ProjectContext> {
        if !root.is_absolute()
            || root.components().any(|part| {
                matches!(
                    part,
                    std::path::Component::CurDir | std::path::Component::ParentDir
                )
            })
        {
            return Err(CoreError::InvalidProject(
                "project root must be an absolute canonical path".into(),
            ));
        }
        let manifest = Self::from_toml_bytes(manifest_bytes)?;
        let manifest_fingerprint = manifest.canonical_fingerprint()?;
        let data_root = root.join(".quillframe").join("data");
        if !data_root.starts_with(root) {
            return Err(CoreError::InvalidProject(
                "project data root escapes the project root".into(),
            ));
        }
        Ok(ProjectContext {
            context_schema: PROJECT_CONTEXT_SCHEMA.into(),
            scope: "novel".into(),
            project_root: root.to_path_buf(),
            data_root,
            manifest,
            manifest_fingerprint,
            manifest_raw_fingerprint: sha256_fingerprint(manifest_bytes),
        })
    }
}

fn valid_project_id(value: &str) -> bool {
    if value.is_empty() || value.len() > 64 {
        return false;
    }
    let mut chars = value.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    first.is_ascii_alphanumeric()
        && chars.all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_manifest_is_exactly_four_keys() {
        let value = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let object = serde_json::to_value(value).unwrap();
        assert_eq!(object.as_object().unwrap().len(), 4);
    }

    #[test]
    fn project_id_matches_native_contract() {
        assert!(ProjectManifest::new("book-01", "Book", "en-US").is_ok());
        assert!(ProjectManifest::new("bad/id", "Book", "en-US").is_err());
        assert!(ProjectManifest::new("", "Book", "en-US").is_err());
    }

    #[test]
    fn toml_contract_rejects_extra_or_legacy_keys() {
        let valid = ProjectManifest::new("BOOK", "长篇", "zh-CN")
            .unwrap()
            .to_toml_bytes()
            .unwrap();
        assert_eq!(ProjectManifest::from_toml_bytes(&valid).unwrap().id, "BOOK");
        let mut extra = String::from_utf8(valid).unwrap();
        extra.push_str("chapter_scope = \"CH001\"\n");
        assert!(ProjectManifest::from_toml_bytes(extra.as_bytes()).is_err());
    }

    #[test]
    fn resolved_context_binds_canonical_and_raw_manifest_fingerprints() {
        let root = std::env::current_dir().unwrap().join("novel");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let compact = manifest.to_toml_bytes().unwrap();
        let mut spaced = compact.clone();
        spaced.extend_from_slice(b"\n");
        let first = ProjectManifest::resolve(&root, &compact).unwrap();
        let second = ProjectManifest::resolve(&root, &spaced).unwrap();
        assert_eq!(first.scope, "novel");
        assert_eq!(first.data_root, root.join(".quillframe").join("data"));
        assert_eq!(first.manifest_fingerprint, second.manifest_fingerprint);
        assert_ne!(
            first.manifest_raw_fingerprint,
            second.manifest_raw_fingerprint
        );
    }
}
