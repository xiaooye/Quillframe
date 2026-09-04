use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

const GLOBAL_FICTION_FOUNDATION: &str = "Quillframe prompt foundation: obey only the frozen project material supplied for this call; never invent canon or claim authority; stay inside the named stage; never reveal private chain-of-thought; return only the requested artifact in the requested language and format. Chapter-length policy has a hard minimum only and no prose-length maximum: never reject, compress, or rewrite a manuscript for exceeding a legacy maximum or target band.";

const SURFACE_NATURALNESS: &str = "Chinese web-novel prose guidance: preserve every approved plot function and causal anchor, but realize them through character choices, observable action, consequence, embodied dialogue, spatial continuity, and scene-specific reactions. Let sentence rhythm follow the dramatic beat and retain natural connective tissue. Do not add omniscient explanation, redundant stacks of action/feeling/body description, formulaic symmetry, thematic uplift, or a summary ending. Do not optimize mechanical sentence-length, dialogue-ratio, banned-word, or detector targets. End on live action, dialogue, discovery, or unresolved consequence when the frozen plan calls for chapter pull.";

const PROSE_REVIEW_GUIDANCE: &str = "Natural-prose review guidance: judge the lived reading effect with exact textual evidence. Flag explanatory author commentary, redundant description stacks, disembodied dialogue, broken spatial continuity, formulaic symmetry or uplift, and summary endings only when they damage this manuscript. Preserve useful narrative connective tissue; do not score word bans, sentence-length ratios, dialogue ratios, deliberate errors, or AI-detector proxies.";

const CAUSAL_GUIDANCE: &str = "Causal fiction guidance: model character-specific choice, pressure, observable action, reaction, cost, and changed scene state. Do not write finished prose and do not replace evidence with abstract labels.";

const REPAIR_GUIDANCE: &str = "Repair guidance: preserve the frozen creative intent, causal anchors, character voice, spatial continuity, and useful narrative connective tissue. Fix only evidenced defects; never flatten or dehydrate the story to make it look less machine-written, and never use detector proxies or mechanical ratios as repair targets.";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PromptBlock {
    pub id: String,
    pub channel: String,
    pub content: Value,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PromptAssembly {
    pub schema: String,
    pub stage_key: String,
    pub blocks: Vec<PromptBlock>,
    pub fingerprint: String,
}

impl PromptAssembly {
    pub fn build(stage_key: &str, stage_role: &str, input: Value) -> CoreResult<Self> {
        if stage_key.trim().is_empty() || stage_role.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "prompt stage and role must be non-empty".into(),
            ));
        }
        let mut context = match input {
            Value::Object(value) => value,
            other => Map::from_iter([("input".into(), other)]),
        };
        strip_legacy_length_upper_bounds(&mut context);
        let author_direction = context.remove("instruction");
        let final_contract = context.remove("contract").ok_or_else(|| {
            CoreError::InvalidProject(format!(
                "prompt stage {stage_key} has no final output contract"
            ))
        })?;
        let mut blocks = vec![
            block(
                "global_fiction_foundation",
                "system",
                Value::String(GLOBAL_FICTION_FOUNDATION.into()),
            )?,
            block("stage_role", "system", Value::String(stage_role.into()))?,
        ];
        if let Some(guidance) = stage_guidance(stage_key) {
            blocks.push(block(
                "stage_craft_guidance",
                "system",
                Value::String(guidance.into()),
            )?);
        }
        blocks.push(block(
            "frozen_dynamic_context",
            "user",
            Value::Object(context),
        )?);
        if let Some(direction) = author_direction {
            blocks.push(block("current_author_direction", "user", direction)?);
        }
        blocks.push(block("final_output_contract", "user", final_contract)?);
        let fingerprint = assembly_fingerprint(stage_key, &blocks)?;
        Ok(Self {
            schema: "quillframe_prompt_assembly_v1".into(),
            stage_key: stage_key.into(),
            blocks,
            fingerprint,
        })
    }

    pub fn system_text(&self) -> String {
        self.blocks
            .iter()
            .filter(|block| block.channel == "system")
            .filter_map(|block| block.content.as_str())
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    pub fn user_text(&self) -> CoreResult<String> {
        let blocks = self
            .blocks
            .iter()
            .filter(|block| block.channel == "user")
            .collect::<Vec<_>>();
        serde_json::to_string(&json!({
            "schema":self.schema,
            "stage_key":self.stage_key,
            "blocks":blocks,
            "prompt_assembly_fingerprint":self.fingerprint
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))
    }

    pub fn itemization(&self) -> Value {
        json!({
            "schema":"quillframe_prompt_itemization_v1",
            "stage_key":self.stage_key,
            "assembly_fingerprint":self.fingerprint,
            "blocks":self.blocks.iter().map(|block|json!({
                "id":block.id,"channel":block.channel,"fingerprint":block.fingerprint
            })).collect::<Vec<_>>()
        })
    }
}

fn strip_legacy_length_upper_bounds(context: &mut Map<String, Value>) {
    fn scrub(map: &mut Map<String, Value>) {
        if let Some(Value::Object(constraint_lock)) = map.get_mut("constraint_lock") {
            if let Some(Value::Object(length)) = constraint_lock.get_mut("length") {
                length.remove("max");
            }
        }
        if let Some(Value::Object(scene_budget)) = map.get_mut("scene_length_budget") {
            scene_budget.remove("target_max");
        }
        for child in map.values_mut() {
            visit(child);
        }
    }

    fn visit(value: &mut Value) {
        match value {
            Value::Object(map) => scrub(map),
            Value::Array(values) => {
                for child in values {
                    visit(child);
                }
            }
            _ => {}
        }
    }

    scrub(context);
}

fn stage_guidance(stage_key: &str) -> Option<&'static str> {
    if stage_key.starts_with("surface_scene_") {
        return Some(SURFACE_NATURALNESS);
    }
    match stage_key {
        "surface_realization" | "bounded_repair_surface" => Some(SURFACE_NATURALNESS),
        "candidate_self_audit" | "independent_semantic_gate" => Some(PROSE_REVIEW_GUIDANCE),
        "repair_editor" | "repair_comparison" => Some(REPAIR_GUIDANCE),
        "character_simulation" | "scene_resolution" => Some(CAUSAL_GUIDANCE),
        _ => None,
    }
}

fn block(id: &str, channel: &str, content: Value) -> CoreResult<PromptBlock> {
    let fingerprint = sha256_fingerprint(
        serde_json::to_vec(&json!({"id":id,"channel":channel,"content":content}))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
    );
    Ok(PromptBlock {
        id: id.into(),
        channel: channel.into(),
        content,
        fingerprint,
    })
}

fn assembly_fingerprint(stage_key: &str, blocks: &[PromptBlock]) -> CoreResult<String> {
    serde_json::to_vec(&json!({
        "schema":"quillframe_prompt_assembly_v1",
        "stage_key":stage_key,
        "blocks":blocks
    }))
    .map(sha256_fingerprint)
    .map_err(|error| CoreError::Serialization(error.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prose_guidance_is_stage_scoped_and_contract_is_last() {
        let writer = PromptAssembly::build(
            "surface_realization",
            "Surface Writer",
            json!({"writer_pack":{"id":"pack"},"instruction":"write now","contract":"JSON manuscript"}),
        )
        .unwrap();
        assert!(writer.system_text().contains("embodied dialogue"));
        assert!(writer.system_text().contains("hard minimum only"));
        assert_eq!(writer.blocks.last().unwrap().id, "final_output_contract");
        assert_eq!(
            writer.blocks[writer.blocks.len() - 2].id,
            "current_author_direction"
        );
        assert!(writer.user_text().unwrap().contains("writer_pack"));

        let repair_writer = PromptAssembly::build(
            "bounded_repair_surface",
            "bounded repair Surface Writer",
            json!({"repair_spec":{"id":"repair"},"contract":"JSON patch windows"}),
        )
        .unwrap();
        assert!(repair_writer.system_text().contains("embodied dialogue"));

        let legacy_length = PromptAssembly::build(
            "surface_scene_0001_SC001",
            "Surface Writer",
            json!({
                "chapter_plan":{"contract":{"constraint_lock":{"length":{
                    "min":3200,"max":4200,"unit":"chinese_characters"
                }}}},
                "scene_length_budget":{"target_min":1600,"target_max":2100,"unit":"chinese_characters"},
                "world_fact":{"length":{"min":2,"max":7,"unit":"meters"}},
                "contract":"JSON manuscript"
            }),
        )
        .unwrap();
        let frozen_context = &legacy_length
            .blocks
            .iter()
            .find(|block| block.id == "frozen_dynamic_context")
            .unwrap()
            .content;
        assert_eq!(
            frozen_context.pointer("/scene_length_budget/target_min"),
            Some(&json!(1600))
        );
        assert!(frozen_context
            .pointer("/scene_length_budget/target_max")
            .is_none());
        assert!(frozen_context
            .pointer("/chapter_plan/contract/constraint_lock/length/max")
            .is_none());
        assert_eq!(
            frozen_context.pointer("/world_fact/length/max"),
            Some(&json!(7))
        );

        let analyzer = PromptAssembly::build(
            "corpus_story_entities",
            "Corpus analyst",
            json!({"source":"evidence","contract":"JSON analysis"}),
        )
        .unwrap();
        assert!(!analyzer.system_text().contains("sentence-length"));
        assert_eq!(analyzer.blocks.len(), 4);
    }

    #[test]
    fn assembly_fingerprint_changes_with_dynamic_context() {
        let left = PromptAssembly::build(
            "scene_resolution",
            "resolver",
            json!({"scene":1,"contract":"JSON"}),
        )
        .unwrap();
        let right = PromptAssembly::build(
            "scene_resolution",
            "resolver",
            json!({"scene":2,"contract":"JSON"}),
        )
        .unwrap();
        assert_ne!(left.fingerprint, right.fingerprint);
    }
}
