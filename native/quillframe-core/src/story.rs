use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};

use crate::{CoreError, CoreResult};

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StoryKind {
    Book,
    Volume,
    Unit,
    Chapter,
    Scene,
}

impl StoryKind {
    pub fn expected_parent(self) -> Option<Self> {
        match self {
            Self::Book => None,
            Self::Volume => Some(Self::Book),
            Self::Unit => Some(Self::Volume),
            Self::Chapter => Some(Self::Unit),
            Self::Scene => Some(Self::Chapter),
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StoryNode {
    pub id: String,
    pub parent_id: Option<String>,
    pub kind: StoryKind,
    pub ordinal: u32,
    pub title: String,
    pub manuscript_id: Option<String>,
}

#[derive(Clone, Debug, Default)]
pub struct StoryGraph {
    nodes: BTreeMap<String, StoryNode>,
    sibling_ordinals: BTreeSet<(Option<String>, StoryKind, u32)>,
    chapter_reading_order: BTreeMap<u32, String>,
}

impl StoryGraph {
    pub fn bootstrap(title: impl Into<String>) -> CoreResult<Self> {
        let title = title.into();
        let mut graph = Self::default();
        graph.insert(StoryNode {
            id: "BOOK".into(),
            parent_id: None,
            kind: StoryKind::Book,
            ordinal: 1,
            title: title.clone(),
            manuscript_id: None,
        })?;
        graph.insert(StoryNode {
            id: "VOL001".into(),
            parent_id: Some("BOOK".into()),
            kind: StoryKind::Volume,
            ordinal: 1,
            title: "第一卷".into(),
            manuscript_id: None,
        })?;
        graph.insert(StoryNode {
            id: "UNIT001".into(),
            parent_id: Some("VOL001".into()),
            kind: StoryKind::Unit,
            ordinal: 1,
            title: "第一单元".into(),
            manuscript_id: None,
        })?;
        graph.insert(StoryNode {
            id: "CH001".into(),
            parent_id: Some("UNIT001".into()),
            kind: StoryKind::Chapter,
            ordinal: 1,
            title,
            manuscript_id: Some("DOC-CH001".into()),
        })?;
        graph.insert(StoryNode {
            id: "SC001".into(),
            parent_id: Some("CH001".into()),
            kind: StoryKind::Scene,
            ordinal: 1,
            title: "第一场".into(),
            manuscript_id: None,
        })?;
        Ok(graph)
    }

    pub fn insert(&mut self, node: StoryNode) -> CoreResult<()> {
        validate_node_id(&node.id)?;
        if self.nodes.contains_key(&node.id) {
            return Err(CoreError::InvalidHierarchy("node id already exists".into()));
        }
        if node.ordinal == 0 || node.title.trim().is_empty() {
            return Err(CoreError::InvalidHierarchy(
                "ordinal must be positive and title must be non-empty".into(),
            ));
        }
        match node.kind.expected_parent() {
            None => {
                if node.parent_id.is_some()
                    || self
                        .nodes
                        .values()
                        .any(|value| value.kind == StoryKind::Book)
                {
                    return Err(CoreError::InvalidHierarchy(
                        "book must be the single root".into(),
                    ));
                }
            }
            Some(expected) => {
                let parent_id = node.parent_id.as_ref().ok_or_else(|| {
                    CoreError::InvalidHierarchy("non-book node requires a parent".into())
                })?;
                let parent = self.nodes.get(parent_id).ok_or_else(|| {
                    CoreError::InvalidHierarchy("parent node does not exist".into())
                })?;
                if parent.kind != expected {
                    return Err(CoreError::InvalidHierarchy(format!(
                        "{:?} requires {:?} parent",
                        node.kind, expected
                    )));
                }
            }
        }
        if node.kind == StoryKind::Chapter {
            if node.manuscript_id.as_deref().is_none_or(str::is_empty) {
                return Err(CoreError::InvalidHierarchy(
                    "chapter requires exactly one manuscript id".into(),
                ));
            }
        } else if node.manuscript_id.is_some() {
            return Err(CoreError::InvalidHierarchy(
                "only chapters may bind manuscript documents".into(),
            ));
        }
        let sibling_key = (node.parent_id.clone(), node.kind, node.ordinal);
        if !self.sibling_ordinals.insert(sibling_key.clone()) {
            return Err(CoreError::InvalidHierarchy(
                "sibling ordinal already exists".into(),
            ));
        }
        if node.kind == StoryKind::Chapter {
            let reading_order = self.chapter_reading_order.len() as u32 + 1;
            self.chapter_reading_order
                .insert(reading_order, node.id.clone());
        }
        self.nodes.insert(node.id.clone(), node);
        Ok(())
    }

    pub fn node(&self, id: &str) -> Option<&StoryNode> {
        self.nodes.get(id)
    }

    pub fn ancestors(&self, id: &str) -> CoreResult<Vec<&StoryNode>> {
        let mut current = self
            .nodes
            .get(id)
            .ok_or_else(|| CoreError::InvalidHierarchy("target node does not exist".into()))?;
        let mut output = Vec::new();
        while let Some(parent_id) = current.parent_id.as_deref() {
            current = self.nodes.get(parent_id).ok_or_else(|| {
                CoreError::InvalidHierarchy("story graph contains a broken parent".into())
            })?;
            output.push(current);
        }
        output.reverse();
        Ok(output)
    }

    pub fn canonical_target(&self, id: &str) -> CoreResult<String> {
        let node = self
            .nodes
            .get(id)
            .ok_or_else(|| CoreError::InvalidHierarchy("target node does not exist".into()))?;
        let prefix = match node.kind {
            StoryKind::Book => "book",
            StoryKind::Volume => "volume",
            StoryKind::Unit => "unit",
            StoryKind::Chapter => "chapter",
            StoryKind::Scene => "scene",
        };
        Ok(format!("{prefix}:{}", node.id))
    }

    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }
}

fn validate_node_id(value: &str) -> CoreResult<()> {
    if value.is_empty()
        || value.len() > 96
        || !value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || matches!(character, '-' | '_'))
    {
        return Err(CoreError::InvalidHierarchy(
            "node id is not canonical".into(),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bootstrap_is_real_five_level_ready_hierarchy() {
        let graph = StoryGraph::bootstrap("第一章").unwrap();
        assert_eq!(graph.len(), 5);
        assert_eq!(
            graph.node("CH001").unwrap().parent_id.as_deref(),
            Some("UNIT001")
        );
        assert_eq!(graph.canonical_target("BOOK").unwrap(), "book:BOOK");
    }

    #[test]
    fn strict_parent_matrix_rejects_chapter_under_book() {
        let mut graph = StoryGraph::bootstrap("第一章").unwrap();
        let result = graph.insert(StoryNode {
            id: "CH002".into(),
            parent_id: Some("BOOK".into()),
            kind: StoryKind::Chapter,
            ordinal: 2,
            title: "第二章".into(),
            manuscript_id: Some("DOC-CH002".into()),
        });
        assert!(result.is_err());
    }

    #[test]
    fn scenes_never_get_manuscript_documents() {
        let mut graph = StoryGraph::bootstrap("第一章").unwrap();
        assert!(graph
            .insert(StoryNode {
                id: "SC001".into(),
                parent_id: Some("CH001".into()),
                kind: StoryKind::Scene,
                ordinal: 1,
                title: "入场".into(),
                manuscript_id: Some("DOC-SC001".into()),
            })
            .is_err());
    }
}
