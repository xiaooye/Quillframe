use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use base64::Engine;
use quillframe_native::{
    guard_directory, publish_staged_noreplace, read_guarded_file, write_stage_new, QfNativeIdentity,
};
use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult, ProjectDatabase};

const MAX_ARTIFACT_BYTES: u64 = 64 * 1024 * 1024;
const MAX_COLLECTION_CHAPTERS: usize = 10_000;
const SINGLE_COMPILER: &str = "quillframe_core_publication_text_v1";
const COLLECTION_COMPILER: &str = "quillframe_core_publication_collection_text_v1";

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum PublicationFormat {
    Md,
    Txt,
}

impl PublicationFormat {
    pub fn parse(value: &str) -> CoreResult<Self> {
        match value {
            "md" => Ok(Self::Md),
            "txt" => Ok(Self::Txt),
            _ => Err(CoreError::InvalidProject(
                "publication format must be md or txt".into(),
            )),
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Self::Md => "md",
            Self::Txt => "txt",
        }
    }

    fn media_type(self) -> &'static str {
        match self {
            Self::Md => "text/markdown; charset=utf-8",
            Self::Txt => "text/plain; charset=utf-8",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PublicationPreview {
    pub source_acceptance_id: String,
    pub source_fingerprint: String,
    pub document_id: String,
    pub content: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PublicationBuild {
    pub project_id: String,
    pub build_id: String,
    pub source_acceptance_ids: Vec<String>,
    pub format: PublicationFormat,
    pub compiler_contract: String,
    pub source_fingerprint: String,
    pub output_ref: String,
    pub identity_fingerprint: String,
    pub artifact_fingerprint: String,
    pub byte_size: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PublicationArtifact {
    pub project_id: String,
    pub build_id: String,
    pub filename: String,
    pub media_type: String,
    pub byte_size: u64,
    pub artifact_fingerprint: String,
    pub content_base64: String,
    pub source_acceptance_ids: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct SourceBinding {
    acceptance_id: String,
    candidate_id: String,
    chapter_id: String,
    content_fingerprint: String,
    document_id: String,
    head_fingerprint: Option<String>,
    reading_order: Option<u64>,
    revision_id: String,
    run_id: Option<String>,
    settlement_id: Option<String>,
}

struct PublicationSource {
    binding: SourceBinding,
    content: String,
}

struct PublicationPlan {
    project_id: String,
    build_id: String,
    source_acceptance_ids: Vec<String>,
    source_ids_json: String,
    source_binding_json: String,
    source_binding_fingerprint: String,
    format: PublicationFormat,
    compiler_contract: &'static str,
    content: Vec<u8>,
    source_fingerprint: String,
    identity_fingerprint: String,
    artifact_fingerprint: String,
    byte_size: u64,
    final_ref: String,
    collection: bool,
}

#[derive(Clone)]
struct AttemptRow {
    stage_ref: String,
    final_ref: String,
    owner_token: String,
    state: String,
    state_version: u64,
    stage_identity_json: Option<String>,
    final_identity_json: Option<String>,
    durability_json: Option<String>,
}

impl ProjectDatabase {
    pub fn preview_publication(&self, acceptance_id: &str) -> CoreResult<PublicationPreview> {
        let source = load_accepted_source(self.connection(), acceptance_id)?;
        Ok(PublicationPreview {
            source_acceptance_id: acceptance_id.to_owned(),
            source_fingerprint: source.binding.content_fingerprint,
            document_id: source.binding.document_id,
            content: source.content,
        })
    }

    pub fn build_publication(
        &mut self,
        project_id: &str,
        acceptance_id: &str,
        format: PublicationFormat,
        created_at: &str,
    ) -> CoreResult<PublicationBuild> {
        let source = load_accepted_source(self.connection(), acceptance_id)?;
        let plan = make_plan(project_id, vec![source], format, false)?;
        build_plan(self, &plan, None, created_at)
    }

    pub fn build_publication_collection(
        &mut self,
        project_id: &str,
        acceptance_ids: &[String],
        format: PublicationFormat,
        idempotency_key: &str,
        user_authorized: bool,
        created_at: &str,
    ) -> CoreResult<PublicationBuild> {
        if !user_authorized {
            return Err(CoreError::AuthorityConflict(
                "publication collection requires explicit author authorization".into(),
            ));
        }
        if idempotency_key.trim().is_empty() || idempotency_key.len() > 256 {
            return Err(CoreError::InvalidProject(
                "publication collection requires a bounded idempotency key".into(),
            ));
        }
        if acceptance_ids.is_empty()
            || acceptance_ids.len() > MAX_COLLECTION_CHAPTERS
            || acceptance_ids.iter().any(|value| value.trim().is_empty())
            || acceptance_ids.iter().collect::<BTreeSet<_>>().len() != acceptance_ids.len()
        {
            return Err(CoreError::InvalidProject(
                "publication collection source list is invalid".into(),
            ));
        }
        let mut sources = Vec::with_capacity(acceptance_ids.len());
        for acceptance_id in acceptance_ids {
            sources.push(load_current_source(self.connection(), acceptance_id)?);
        }
        if sources
            .windows(2)
            .any(|pair| pair[0].binding.reading_order >= pair[1].binding.reading_order)
        {
            return Err(CoreError::AuthorityConflict(
                "publication collection must follow current novel reading order".into(),
            ));
        }
        let plan = make_plan(project_id, sources, format, true)?;
        build_plan(self, &plan, Some(idempotency_key), created_at)
    }

    pub fn publication_artifact(
        &self,
        project_id: &str,
        build_id: &str,
    ) -> CoreResult<PublicationArtifact> {
        let build = load_build(self, project_id, build_id)?;
        let final_path = artifact_path(self, &build.output_ref)?;
        let (bytes, _) =
            read_guarded_file(&final_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
        validate_artifact_bytes(&bytes, &build.artifact_fingerprint, build.byte_size)?;
        let filename = final_path
            .file_name()
            .and_then(|value| value.to_str())
            .ok_or_else(|| CoreError::Storage("publication filename is invalid".into()))?
            .to_owned();
        Ok(PublicationArtifact {
            project_id: project_id.to_owned(),
            build_id: build.build_id,
            filename,
            media_type: build.format.media_type().into(),
            byte_size: build.byte_size,
            artifact_fingerprint: build.artifact_fingerprint,
            content_base64: base64::engine::general_purpose::STANDARD.encode(bytes),
            source_acceptance_ids: build.source_acceptance_ids,
        })
    }
}

fn load_accepted_source(
    connection: &Connection,
    acceptance_id: &str,
) -> CoreResult<PublicationSource> {
    if acceptance_id.trim().is_empty() {
        return Err(CoreError::InvalidProject(
            "acceptance id is required".into(),
        ));
    }
    let row = connection.query_row(
        "SELECT a.candidate_id,a.candidate_fingerprint,c.status,c.document_id,c.revision_id,c.run_id, \
         r.content,r.content_fingerprint,r.authority_class,r.document_id,d.story_node_id,d.document_kind,n.kind \
         FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id \
         JOIN document_revisions r ON r.revision_id=c.revision_id \
         JOIN documents d ON d.document_id=c.document_id JOIN story_nodes n ON n.node_id=d.story_node_id \
         WHERE a.acceptance_id=?1",
        [acceptance_id],
        |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?,
            row.get::<_,String>(3)?,row.get::<_,String>(4)?,row.get::<_,Option<String>>(5)?,
            row.get::<_,String>(6)?,row.get::<_,String>(7)?,row.get::<_,String>(8)?,
            row.get::<_,String>(9)?,row.get::<_,String>(10)?,row.get::<_,String>(11)?,row.get::<_,String>(12)?)),
    ).map_err(storage)?;
    let (
        candidate_id,
        candidate_fp,
        status,
        document_id,
        revision_id,
        run_id,
        content,
        revision_fp,
        authority,
        revision_document,
        chapter_id,
        document_kind,
        node_kind,
    ) = row;
    let actual = sha256_fingerprint(content.as_bytes());
    if status != "accepted"
        || authority != "accepted"
        || candidate_fp != revision_fp
        || revision_fp != actual
        || document_id != revision_document
        || document_kind != "manuscript"
        || node_kind != "chapter"
    {
        return Err(CoreError::AuthorityConflict(
            "publication source is not an intact accepted revision".into(),
        ));
    }
    Ok(PublicationSource {
        binding: SourceBinding {
            acceptance_id: acceptance_id.into(),
            candidate_id,
            chapter_id,
            content_fingerprint: revision_fp,
            document_id,
            head_fingerprint: None,
            reading_order: None,
            revision_id,
            run_id,
            settlement_id: None,
        },
        content,
    })
}

fn load_current_source(
    connection: &Connection,
    acceptance_id: &str,
) -> CoreResult<PublicationSource> {
    let mut source = load_accepted_source(connection, acceptance_id)?;
    let (head_json, head_fingerprint, head_authority):(String,String,String)=connection.query_row(
        "SELECT value_json,content_fingerprint,authority_class FROM canon_state WHERE state_key=?1",
        [format!("chapter:{}",source.binding.chapter_id)],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))
    ).map_err(storage)?;
    if head_authority != "accepted" || sha256_fingerprint(head_json.as_bytes()) != head_fingerprint
    {
        return Err(CoreError::AuthorityConflict(
            "current chapter head is invalid".into(),
        ));
    }
    let head: Value = serde_json::from_str(&head_json)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let matches = head.get("acceptance_id").and_then(Value::as_str) == Some(acceptance_id)
        && head.get("candidate_id").and_then(Value::as_str)
            == Some(source.binding.candidate_id.as_str())
        && head.get("chapter_id").and_then(Value::as_str)
            == Some(source.binding.chapter_id.as_str())
        && head.get("content_fingerprint").and_then(Value::as_str)
            == Some(source.binding.content_fingerprint.as_str())
        && head.get("document_id").and_then(Value::as_str)
            == Some(source.binding.document_id.as_str())
        && head.get("revision_id").and_then(Value::as_str)
            == Some(source.binding.revision_id.as_str());
    let reading_order = head
        .get("reading_order")
        .and_then(Value::as_u64)
        .ok_or_else(|| {
            CoreError::AuthorityConflict("current chapter head has no reading order".into())
        })?;
    if !matches {
        return Err(CoreError::AuthorityConflict(
            "acceptance is not the current settled chapter head".into(),
        ));
    }
    let settlement_id=connection.query_row(
        "SELECT settlement_id FROM settlements WHERE acceptance_id=?1 AND target_ref=?2 \
         AND status='settled' AND after_fingerprint=?3 ORDER BY completed_at DESC,settlement_id DESC LIMIT 1",
        params![acceptance_id,format!("chapter:{}",source.binding.chapter_id),head_fingerprint],|row|row.get::<_,String>(0)
    ).map_err(storage)?;
    if let Some(run_id) = source.binding.run_id.as_deref() {
        let stale:u64=connection.query_row(
            "SELECT COUNT(*) FROM chapter_dependencies d LEFT JOIN canon_state s \
             ON s.state_key='chapter:'||d.source_chapter_id WHERE d.run_id=?1 \
             AND (d.status<>'current' OR s.content_fingerprint IS NULL OR d.source_fingerprint<>s.content_fingerprint)",
            [run_id],|row|row.get(0)
        ).map_err(storage)?;
        if stale != 0 {
            return Err(CoreError::AuthorityConflict(
                "publication source has stale production dependencies".into(),
            ));
        }
    }
    let live_order: u64 = connection
        .query_row(
            "SELECT COUNT(*) FROM story_nodes c2 JOIN story_nodes u2 ON u2.node_id=c2.parent_id \
         JOIN story_nodes v2 ON v2.node_id=u2.parent_id JOIN story_nodes c ON c.node_id=?1 \
         JOIN story_nodes u ON u.node_id=c.parent_id JOIN story_nodes v ON v.node_id=u.parent_id \
         WHERE c2.kind='chapter' AND (v2.ordinal<v.ordinal OR (v2.ordinal=v.ordinal AND \
         (u2.ordinal<u.ordinal OR (u2.ordinal=u.ordinal AND (c2.ordinal<c.ordinal OR \
         (c2.ordinal=c.ordinal AND c2.node_id<=c.node_id))))))",
            [&source.binding.chapter_id],
            |row| row.get(0),
        )
        .map_err(storage)?;
    if live_order != reading_order {
        return Err(CoreError::AuthorityConflict(
            "publication reading order changed after settlement".into(),
        ));
    }
    source.binding.head_fingerprint = Some(head_fingerprint);
    source.binding.reading_order = Some(reading_order);
    source.binding.settlement_id = Some(settlement_id);
    Ok(source)
}

fn make_plan(
    project_id: &str,
    sources: Vec<PublicationSource>,
    format: PublicationFormat,
    collection: bool,
) -> CoreResult<PublicationPlan> {
    let source_acceptance_ids = sources
        .iter()
        .map(|source| source.binding.acceptance_id.clone())
        .collect::<Vec<_>>();
    let source_ids_json = serde_json::to_string(&source_acceptance_ids)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let source_binding_json = if collection {
        serde_json::to_string(
            &sources
                .iter()
                .map(|source| &source.binding)
                .collect::<Vec<_>>(),
        )
    } else {
        serde_json::to_string(&sources[0].binding)
    }
    .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let source_binding_fingerprint = sha256_fingerprint(source_binding_json.as_bytes());
    let content = sources
        .iter()
        .map(|source| source.content.as_str())
        .collect::<Vec<_>>()
        .join(if collection { "\n\n" } else { "" })
        .into_bytes();
    if content.len() as u64 > MAX_ARTIFACT_BYTES {
        return Err(CoreError::InvalidProject(
            "publication artifact exceeds 64 MiB".into(),
        ));
    }
    let compiler_contract = if collection {
        COLLECTION_COMPILER
    } else {
        SINGLE_COMPILER
    };
    let identity_json = serde_json::to_string(
        &json!({"compiler_contract":compiler_contract,"format":format.as_str(),
        "project_id":project_id,"source_acceptance_ids":source_acceptance_ids,
        "source_binding_fingerprint":source_binding_fingerprint}),
    )
    .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let identity_fingerprint = sha256_fingerprint(identity_json.as_bytes());
    let build_id = format!("pub_{}", identity_fingerprint.trim_start_matches("sha256:"));
    let final_ref = format!("exports/{build_id}.{}", format.as_str());
    Ok(PublicationPlan {
        project_id: project_id.into(),
        build_id,
        source_acceptance_ids,
        source_ids_json,
        source_binding_json,
        source_binding_fingerprint: source_binding_fingerprint.clone(),
        format,
        compiler_contract,
        artifact_fingerprint: sha256_fingerprint(&content),
        byte_size: content.len() as u64,
        content,
        source_fingerprint: if collection {
            source_binding_fingerprint.clone()
        } else {
            sources[0].binding.content_fingerprint.clone()
        },
        identity_fingerprint,
        final_ref,
        collection,
    })
}

fn build_plan(
    store: &mut ProjectDatabase,
    plan: &PublicationPlan,
    idempotency_key: Option<&str>,
    created_at: &str,
) -> CoreResult<PublicationBuild> {
    prepare_attempt(store, plan, idempotency_key, created_at)?;
    let attempt = load_attempt(store.connection(), plan)?;
    if attempt.state != "committed" {
        drive_publication_files(store, plan, &attempt, created_at)?;
        finalize_build(store, plan, created_at)?;
    }
    let build = load_build(store, &plan.project_id, &plan.build_id)?;
    let artifact_path = artifact_path(store, &build.output_ref)?;
    let (bytes, _) = read_guarded_file(&artifact_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
    validate_artifact_bytes(&bytes, &build.artifact_fingerprint, build.byte_size)?;
    Ok(build)
}

fn prepare_attempt(
    store: &mut ProjectDatabase,
    plan: &PublicationPlan,
    idempotency_key: Option<&str>,
    created_at: &str,
) -> CoreResult<()> {
    if created_at.trim().is_empty() {
        return Err(CoreError::InvalidProject(
            "publication timestamp is required".into(),
        ));
    }
    let transaction = store
        .connection_mut()
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(storage)?;
    let actual_project: String = transaction
        .query_row("SELECT project_id FROM project_identity", [], |row| {
            row.get(0)
        })
        .map_err(storage)?;
    if actual_project != plan.project_id {
        return Err(CoreError::AuthorityConflict(
            "publication project does not match the opened Project".into(),
        ));
    }
    let table = if plan.collection {
        "publication_collection_attempts"
    } else {
        "publication_build_attempts"
    };
    let exists: bool = transaction
        .query_row(
            &format!("SELECT EXISTS(SELECT 1 FROM {table} WHERE build_id=?1)"),
            [&plan.build_id],
            |row| row.get(0),
        )
        .map_err(storage)?;
    if exists {
        let exact: bool = if plan.collection {
            transaction.query_row(
                "SELECT EXISTS(SELECT 1 FROM publication_collection_attempts WHERE build_id=?1 \
                 AND identity_fingerprint=?2 AND project_id=?3 AND source_acceptance_ids_json=?4 \
                 AND format=?5 AND compiler_contract=?6 AND source_fingerprint=?7 \
                 AND artifact_fingerprint=?8 AND byte_size=?9 AND final_ref=?10 \
                 AND source_binding_json=?11 AND source_binding_fingerprint=?12)",
                params![
                    plan.build_id,
                    plan.identity_fingerprint,
                    plan.project_id,
                    plan.source_ids_json,
                    plan.format.as_str(),
                    plan.compiler_contract,
                    plan.source_fingerprint,
                    plan.artifact_fingerprint,
                    plan.byte_size,
                    plan.final_ref,
                    plan.source_binding_json,
                    plan.source_binding_fingerprint
                ],
                |row| row.get(0),
            )
        } else {
            transaction.query_row(
                "SELECT EXISTS(SELECT 1 FROM publication_build_attempts WHERE build_id=?1 \
                 AND identity_fingerprint=?2 AND project_id=?3 AND source_acceptance_id=?4 \
                 AND format=?5 AND compiler_contract=?6 AND source_fingerprint=?7 \
                 AND artifact_fingerprint=?8 AND byte_size=?9 AND final_ref=?10 \
                 AND source_binding_json=?11 AND source_binding_fingerprint=?12)",
                params![
                    plan.build_id,
                    plan.identity_fingerprint,
                    plan.project_id,
                    plan.source_acceptance_ids[0],
                    plan.format.as_str(),
                    plan.compiler_contract,
                    plan.source_fingerprint,
                    plan.artifact_fingerprint,
                    plan.byte_size,
                    plan.final_ref,
                    plan.source_binding_json,
                    plan.source_binding_fingerprint
                ],
                |row| row.get(0),
            )
        }
        .map_err(storage)?;
        if !exact {
            return Err(CoreError::AuthorityConflict(
                "publication identity conflicts with its durable attempt".into(),
            ));
        }
        if plan.collection {
            let mut statement=transaction.prepare("SELECT acceptance_id FROM publication_collection_members WHERE build_id=?1 ORDER BY ordinal")
                .map_err(storage)?;
            let members = statement
                .query_map([&plan.build_id], |row| row.get::<_, String>(0))
                .map_err(storage)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage)?;
            if members != plan.source_acceptance_ids {
                return Err(CoreError::AuthorityConflict(
                    "publication collection membership changed".into(),
                ));
            }
        }
    } else {
        let token = uuid::Uuid::new_v4().simple().to_string();
        let owner_token = format!("qfpub:{token}");
        let stage_ref = format!("exports/.{}.{}.stage", plan.build_id, token);
        if plan.collection {
            transaction.execute(
                "INSERT INTO publication_collection_attempts(build_id,identity_fingerprint,project_id, \
                 source_acceptance_ids_json,format,compiler_contract,source_fingerprint,artifact_fingerprint, \
                 byte_size,stage_ref,final_ref,owner_token,state,error_code,created_at,updated_at, \
                 source_binding_json,source_binding_fingerprint,state_version) \
                 VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,'staged',NULL,?13,?13,?14,?15,1)",
                params![plan.build_id,plan.identity_fingerprint,plan.project_id,plan.source_ids_json,
                    plan.format.as_str(),plan.compiler_contract,plan.source_fingerprint,
                    plan.artifact_fingerprint,plan.byte_size,stage_ref,plan.final_ref,owner_token,
                    created_at,plan.source_binding_json,plan.source_binding_fingerprint],
            ).map_err(storage)?;
            for (ordinal, acceptance_id) in plan.source_acceptance_ids.iter().enumerate() {
                transaction.execute(
                    "INSERT INTO publication_collection_members(build_id,ordinal,acceptance_id) VALUES(?1,?2,?3)",
                    params![plan.build_id,ordinal,acceptance_id],
                ).map_err(storage)?;
            }
        } else {
            transaction.execute(
                "INSERT INTO publication_build_attempts(build_id,identity_fingerprint,project_id, \
                 source_acceptance_id,format,compiler_contract,source_fingerprint,artifact_fingerprint, \
                 byte_size,stage_ref,final_ref,owner_token,state,error_code,created_at,updated_at, \
                 source_binding_json,source_binding_fingerprint,state_version) \
                 VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,'staged',NULL,?13,?13,?14,?15,1)",
                params![plan.build_id,plan.identity_fingerprint,plan.project_id,plan.source_acceptance_ids[0],
                    plan.format.as_str(),plan.compiler_contract,plan.source_fingerprint,
                    plan.artifact_fingerprint,plan.byte_size,stage_ref,plan.final_ref,owner_token,
                    created_at,plan.source_binding_json,plan.source_binding_fingerprint],
            ).map_err(storage)?;
        }
    }
    let request_fingerprint = sha256_fingerprint(
        serde_json::to_string(
            &json!({"format":plan.format.as_str(),"operation":if plan.collection{
            "publication.collection.build"}else{"publication.build"},"project_id":plan.project_id,
            "source_acceptance_ids":plan.source_acceptance_ids}),
        )
        .map_err(|error| CoreError::Serialization(error.to_string()))?
        .as_bytes(),
    );
    if plan.collection {
        let key = idempotency_key.ok_or_else(|| {
            CoreError::InvalidProject("collection idempotency key is required".into())
        })?;
        let prior=transaction.query_row(
            "SELECT request_fingerprint,build_id FROM publication_collection_requests WHERE idempotency_key=?1",
            [key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?))
        ).optional().map_err(storage)?;
        if let Some((fingerprint, build_id)) = prior {
            if fingerprint != request_fingerprint || build_id != plan.build_id {
                return Err(CoreError::AuthorityConflict(
                    "publication idempotency key binds another request".into(),
                ));
            }
        } else {
            transaction.execute(
                "INSERT INTO publication_collection_requests(idempotency_key,request_fingerprint,build_id,created_at) VALUES(?1,?2,?3,?4)",
                params![key,request_fingerprint,plan.build_id,created_at],
            ).map_err(storage)?;
        }
    } else {
        let key = format!("single:{}", plan.identity_fingerprint);
        let prior=transaction.query_row(
            "SELECT request_fingerprint,build_id FROM publication_build_requests WHERE idempotency_key=?1",
            [&key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?))
        ).optional().map_err(storage)?;
        if let Some((fingerprint, build_id)) = prior {
            if fingerprint != request_fingerprint || build_id != plan.build_id {
                return Err(CoreError::AuthorityConflict(
                    "publication request identity conflicts".into(),
                ));
            }
        } else {
            transaction.execute(
                "INSERT INTO publication_build_requests(idempotency_key,request_fingerprint,build_id,created_at) VALUES(?1,?2,?3,?4)",
                params![key,request_fingerprint,plan.build_id,created_at],
            ).map_err(storage)?;
        }
    }
    transaction.commit().map_err(storage)
}

fn load_attempt(connection: &Connection, plan: &PublicationPlan) -> CoreResult<AttemptRow> {
    let query = if plan.collection {
        "SELECT stage_ref,final_ref,owner_token,state,state_version,stage_identity_json,final_identity_json,durability_json \
         FROM publication_collection_attempts WHERE build_id=?1"
    } else {
        "SELECT stage_ref,final_ref,owner_token,state,state_version,stage_identity_json,final_identity_json,durability_json \
         FROM publication_build_attempts WHERE build_id=?1"
    };
    connection
        .query_row(query, [&plan.build_id], |row| {
            Ok(AttemptRow {
                stage_ref: row.get(0)?,
                final_ref: row.get(1)?,
                owner_token: row.get(2)?,
                state: row.get(3)?,
                state_version: row.get(4)?,
                stage_identity_json: row.get(5)?,
                final_identity_json: row.get(6)?,
                durability_json: row.get(7)?,
            })
        })
        .map_err(storage)
}

fn drive_publication_files(
    store: &mut ProjectDatabase,
    plan: &PublicationPlan,
    initial: &AttemptRow,
    updated_at: &str,
) -> CoreResult<()> {
    if initial.state == "failed" {
        return Err(CoreError::AuthorityConflict(
            "failed publication attempts require an explicit retry".into(),
        ));
    }
    if initial.state == "committed" {
        return Ok(());
    }
    validate_attempt_refs(plan, initial)?;
    let exports = store
        .path()
        .parent()
        .ok_or_else(|| CoreError::Storage("project database has no data root".into()))?
        .join("exports");
    let _exports_guard = guard_directory(&exports, true).map_err(native_error)?;
    let stage_path = artifact_path(store, &initial.stage_ref)?;
    let final_path = artifact_path(store, &initial.final_ref)?;
    if stage_path.exists() && final_path.exists() {
        return Err(CoreError::AuthorityConflict(
            "publication stage and final both exist; ownership is ambiguous".into(),
        ));
    }
    let mut attempt = initial.clone();
    if final_path.exists() {
        let expected = attempt.stage_identity_json.as_deref().ok_or_else(|| {
            CoreError::AuthorityConflict(
                "publication final exists without a recorded staged identity".into(),
            )
        })?;
        let expected = parse_identity(expected)?;
        let (bytes, actual) =
            read_guarded_file(&final_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
        validate_artifact_bytes(&bytes, &plan.artifact_fingerprint, plan.byte_size)?;
        require_identity(expected, actual)?;
        if attempt.state == "staged" {
            update_published(store, plan, &attempt, actual, updated_at)?;
        }
        return Ok(());
    }
    if attempt.state == "published" {
        return Err(CoreError::AuthorityConflict(
            "published artifact is missing".into(),
        ));
    }
    let stage_identity = if stage_path.exists() {
        let (bytes, actual) =
            read_guarded_file(&stage_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
        validate_artifact_bytes(&bytes, &plan.artifact_fingerprint, plan.byte_size)?;
        if let Some(expected) = attempt.stage_identity_json.as_deref() {
            require_identity(parse_identity(expected)?, actual)?;
        }
        actual
    } else {
        if attempt.stage_identity_json.is_some() {
            return Err(CoreError::AuthorityConflict(
                "owned publication stage is missing".into(),
            ));
        }
        let guard = write_stage_new(&stage_path, &plan.content).map_err(native_error)?;
        let identity = guard.revalidate().map_err(native_error)?;
        drop(guard);
        identity
    };
    if attempt.stage_identity_json.is_none() {
        let table = if plan.collection {
            "publication_collection_attempts"
        } else {
            "publication_build_attempts"
        };
        let changed=store.connection_mut().execute(
            &format!("UPDATE {table} SET stage_identity_json=?1,state_version=state_version+1,updated_at=?2 \
             WHERE build_id=?3 AND state='staged' AND state_version=?4 AND stage_identity_json IS NULL"),
            params![identity_json(stage_identity)?,updated_at,plan.build_id,attempt.state_version],
        ).map_err(storage)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "publication stage state changed concurrently".into(),
            ));
        }
        attempt = load_attempt(store.connection(), plan)?;
    }
    let recorded = parse_identity(
        attempt
            .stage_identity_json
            .as_deref()
            .ok_or_else(|| CoreError::Storage("stage identity was not persisted".into()))?,
    )?;
    require_identity(recorded, stage_identity)?;
    let published =
        publish_staged_noreplace(&stage_path, &final_path, recorded).map_err(native_error)?;
    let final_identity = published.revalidate().map_err(native_error)?;
    drop(published);
    let (bytes, reopened) =
        read_guarded_file(&final_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
    validate_artifact_bytes(&bytes, &plan.artifact_fingerprint, plan.byte_size)?;
    require_identity(final_identity, reopened)?;
    update_published(store, plan, &attempt, reopened, updated_at)
}

fn update_published(
    store: &mut ProjectDatabase,
    plan: &PublicationPlan,
    attempt: &AttemptRow,
    final_identity: QfNativeIdentity,
    updated_at: &str,
) -> CoreResult<()> {
    let table = if plan.collection {
        "publication_collection_attempts"
    } else {
        "publication_build_attempts"
    };
    let durability = if cfg!(windows) {
        json!({"contract":"file_synced_handle_bound_rename","platform":"windows"})
    } else {
        json!({"contract":"file_and_directory_synced","platform":"linux"})
    };
    let changed=store.connection_mut().execute(
        &format!("UPDATE {table} SET state='published',final_identity_json=?1,durability_json=?2, \
         state_version=state_version+1,updated_at=?3 WHERE build_id=?4 AND state='staged' AND state_version=?5"),
        params![identity_json(final_identity)?,serde_json::to_string(&durability)
            .map_err(|error|CoreError::Serialization(error.to_string()))?,updated_at,plan.build_id,attempt.state_version],
    ).map_err(storage)?;
    if changed != 1 {
        return Err(CoreError::AuthorityConflict(
            "publication publish state changed concurrently".into(),
        ));
    }
    Ok(())
}

fn finalize_build(
    store: &mut ProjectDatabase,
    plan: &PublicationPlan,
    created_at: &str,
) -> CoreResult<()> {
    let attempt = load_attempt(store.connection(), plan)?;
    if attempt.state == "committed" {
        return Ok(());
    }
    if attempt.state != "published" {
        return Err(CoreError::AuthorityConflict(
            "publication is not durably published".into(),
        ));
    }
    let current = rebuild_plan(store.connection(), plan)?;
    if current.build_id != plan.build_id
        || current.source_binding_json != plan.source_binding_json
        || current.artifact_fingerprint != plan.artifact_fingerprint
    {
        return Err(CoreError::AuthorityConflict(
            "publication source changed before commit".into(),
        ));
    }
    let final_path = artifact_path(store, &plan.final_ref)?;
    let (bytes, identity) =
        read_guarded_file(&final_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
    validate_artifact_bytes(&bytes, &plan.artifact_fingerprint, plan.byte_size)?;
    let expected =
        parse_identity(attempt.final_identity_json.as_deref().ok_or_else(|| {
            CoreError::Storage("published attempt has no final identity".into())
        })?)?;
    require_identity(expected, identity)?;
    let durability_json = attempt.durability_json.as_deref().ok_or_else(|| {
        CoreError::Storage("published attempt has no native durability receipt".into())
    })?;
    let durability: Value = serde_json::from_str(durability_json)
        .map_err(|error| CoreError::Storage(error.to_string()))?;
    let final_identity_json = attempt
        .final_identity_json
        .as_deref()
        .ok_or_else(|| CoreError::Storage("published attempt has no final identity".into()))?;
    let source_binding: Value = serde_json::from_str(&plan.source_binding_json)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let manifest=serde_json::to_string(&json!({"artifact_fingerprint":plan.artifact_fingerprint,
        "build_id":plan.build_id,"byte_size":plan.byte_size,"compiler_contract":plan.compiler_contract,
        "durability":durability,"format":plan.format.as_str(),"identity_fingerprint":plan.identity_fingerprint,
        "final_identity":serde_json::from_str::<Value>(final_identity_json)
            .map_err(|error|CoreError::Storage(error.to_string()))?,
        "output_ref":plan.final_ref,"source_acceptance_ids":plan.source_acceptance_ids,
        "source_binding":source_binding,"source_binding_fingerprint":plan.source_binding_fingerprint,
        "source_fingerprint":plan.source_fingerprint}))
        .map_err(|error|CoreError::Serialization(error.to_string()))?;
    let manifest_fingerprint = sha256_fingerprint(manifest.as_bytes());
    let transaction = store
        .connection_mut()
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(storage)?;
    let current_in_transaction = rebuild_plan(&transaction, plan)?;
    if current_in_transaction.build_id != plan.build_id
        || current_in_transaction.source_binding_json != plan.source_binding_json
    {
        return Err(CoreError::AuthorityConflict(
            "publication source changed during commit".into(),
        ));
    }
    if plan.collection {
        transaction.execute(
            "INSERT INTO publication_collection_builds(build_id,source_acceptance_ids_json,format,compiler_contract, \
             output_ref,source_fingerprint,validation_json,persistent,created_at,source_binding_json, \
             source_binding_fingerprint,artifact_fingerprint,byte_size,artifact_manifest_json,artifact_manifest_fingerprint) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,1,?8,?9,?10,?11,?12,?13,?14)",
            params![plan.build_id,plan.source_ids_json,plan.format.as_str(),plan.compiler_contract,plan.final_ref,
                plan.source_fingerprint,manifest,created_at,plan.source_binding_json,plan.source_binding_fingerprint,
                plan.artifact_fingerprint,plan.byte_size,manifest,manifest_fingerprint],
        ).map_err(storage)?;
        let changed=transaction.execute(
            "UPDATE publication_collection_attempts SET state='committed',state_version=state_version+1,updated_at=?1 \
             WHERE build_id=?2 AND state='published' AND state_version=?3",
            params![created_at,plan.build_id,attempt.state_version],
        ).map_err(storage)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "publication collection commit raced".into(),
            ));
        }
    } else {
        transaction.execute(
            "INSERT INTO publication_builds(build_id,source_acceptance_id,format,compiler_contract,output_ref, \
             source_fingerprint,validation_json,persistent,created_at,source_binding_json,source_binding_fingerprint, \
             artifact_fingerprint,byte_size,artifact_manifest_json,artifact_manifest_fingerprint) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,1,?8,?9,?10,?11,?12,?13,?14)",
            params![plan.build_id,plan.source_acceptance_ids[0],plan.format.as_str(),plan.compiler_contract,
                plan.final_ref,plan.source_fingerprint,manifest,created_at,plan.source_binding_json,
                plan.source_binding_fingerprint,plan.artifact_fingerprint,plan.byte_size,manifest,manifest_fingerprint],
        ).map_err(storage)?;
        let changed=transaction.execute(
            "UPDATE publication_build_attempts SET state='committed',state_version=state_version+1,updated_at=?1 \
             WHERE build_id=?2 AND state='published' AND state_version=?3",
            params![created_at,plan.build_id,attempt.state_version],
        ).map_err(storage)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "publication commit raced".into(),
            ));
        }
    }
    transaction.commit().map_err(storage)
}

fn rebuild_plan(connection: &Connection, plan: &PublicationPlan) -> CoreResult<PublicationPlan> {
    let mut sources = Vec::with_capacity(plan.source_acceptance_ids.len());
    for acceptance_id in &plan.source_acceptance_ids {
        sources.push(if plan.collection {
            load_current_source(connection, acceptance_id)?
        } else {
            load_accepted_source(connection, acceptance_id)?
        });
    }
    if plan.collection
        && sources
            .windows(2)
            .any(|pair| pair[0].binding.reading_order >= pair[1].binding.reading_order)
    {
        return Err(CoreError::AuthorityConflict(
            "publication reading order changed".into(),
        ));
    }
    make_plan(&plan.project_id, sources, plan.format, plan.collection)
}

fn load_build(
    store: &ProjectDatabase,
    project_id: &str,
    build_id: &str,
) -> CoreResult<PublicationBuild> {
    struct Row {
        ids: Vec<String>,
        format: String,
        compiler: String,
        source_fp: String,
        output_ref: String,
        identity_fp: String,
        artifact_fp: String,
        byte_size: u64,
        manifest: String,
        manifest_fp: String,
        source_binding: String,
        source_binding_fp: String,
        final_identity: String,
        durability: String,
    }
    let single=store.connection().query_row(
        "SELECT b.source_acceptance_id,b.format,b.compiler_contract,b.source_fingerprint,b.output_ref, \
         a.identity_fingerprint,b.artifact_fingerprint,b.byte_size,b.artifact_manifest_json,b.artifact_manifest_fingerprint, \
         b.source_binding_json,b.source_binding_fingerprint,a.final_identity_json,a.durability_json \
         FROM publication_builds b JOIN publication_build_attempts a ON a.build_id=b.build_id \
         WHERE b.build_id=?1 AND a.project_id=?2 AND a.state='committed'",
        params![build_id,project_id],|row|Ok(Row{ids:vec![row.get(0)?],format:row.get(1)?,compiler:row.get(2)?,
            source_fp:row.get(3)?,output_ref:row.get(4)?,identity_fp:row.get(5)?,artifact_fp:row.get(6)?,
            byte_size:row.get(7)?,manifest:row.get(8)?,manifest_fp:row.get(9)?,source_binding:row.get(10)?,
            source_binding_fp:row.get(11)?,final_identity:row.get(12)?,durability:row.get(13)?})
    ).optional().map_err(storage)?;
    let values = if let Some(values) = single {
        values
    } else {
        store.connection().query_row(
            "SELECT b.source_acceptance_ids_json,b.format,b.compiler_contract,b.source_fingerprint,b.output_ref, \
             a.identity_fingerprint,b.artifact_fingerprint,b.byte_size,b.artifact_manifest_json,b.artifact_manifest_fingerprint, \
             b.source_binding_json,b.source_binding_fingerprint,a.final_identity_json,a.durability_json \
             FROM publication_collection_builds b JOIN publication_collection_attempts a ON a.build_id=b.build_id \
             WHERE b.build_id=?1 AND a.project_id=?2 AND a.state='committed'",
            params![build_id,project_id],|row|{
                let ids_json:String=row.get(0)?;
                let ids=serde_json::from_str::<Vec<String>>(&ids_json).map_err(|error|rusqlite::Error::FromSqlConversionFailure(
                    0,rusqlite::types::Type::Text,Box::new(error)))?;
                Ok(Row{ids,format:row.get(1)?,compiler:row.get(2)?,source_fp:row.get(3)?,output_ref:row.get(4)?,
                    identity_fp:row.get(5)?,artifact_fp:row.get(6)?,byte_size:row.get(7)?,manifest:row.get(8)?,
                    manifest_fp:row.get(9)?,source_binding:row.get(10)?,source_binding_fp:row.get(11)?,
                    final_identity:row.get(12)?,durability:row.get(13)?})
            }
        ).map_err(storage)?
    };
    if sha256_fingerprint(values.manifest.as_bytes()) != values.manifest_fp
        || sha256_fingerprint(values.source_binding.as_bytes()) != values.source_binding_fp
    {
        return Err(CoreError::AuthorityConflict(
            "publication artifact manifest fingerprint is invalid".into(),
        ));
    }
    let manifest_value: Value = serde_json::from_str(&values.manifest)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let source_binding: Value = serde_json::from_str(&values.source_binding)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let final_identity: Value = serde_json::from_str(&values.final_identity)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let durability: Value = serde_json::from_str(&values.durability)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let expected = json!({"artifact_fingerprint":values.artifact_fp,"build_id":build_id,
        "byte_size":values.byte_size,"compiler_contract":values.compiler,"durability":durability,
        "final_identity":final_identity,"format":values.format,"identity_fingerprint":values.identity_fp,
        "output_ref":values.output_ref,"source_acceptance_ids":values.ids,"source_binding":source_binding,
        "source_binding_fingerprint":values.source_binding_fp,"source_fingerprint":values.source_fp});
    if manifest_value != expected {
        return Err(CoreError::AuthorityConflict(
            "publication artifact manifest is inconsistent".into(),
        ));
    }
    let final_path = artifact_path(store, &values.output_ref)?;
    let (bytes, actual_identity) =
        read_guarded_file(&final_path, MAX_ARTIFACT_BYTES).map_err(native_error)?;
    validate_artifact_bytes(&bytes, &values.artifact_fp, values.byte_size)?;
    require_identity(parse_identity(&values.final_identity)?, actual_identity)?;
    Ok(PublicationBuild {
        project_id: project_id.into(),
        build_id: build_id.into(),
        source_acceptance_ids: values.ids,
        format: PublicationFormat::parse(&values.format)?,
        compiler_contract: values.compiler,
        source_fingerprint: values.source_fp,
        output_ref: values.output_ref,
        identity_fingerprint: values.identity_fp,
        artifact_fingerprint: values.artifact_fp,
        byte_size: values.byte_size,
    })
}

fn validate_attempt_refs(plan: &PublicationPlan, attempt: &AttemptRow) -> CoreResult<()> {
    let token = attempt
        .owner_token
        .strip_prefix("qfpub:")
        .unwrap_or_default();
    let expected_stage = format!("exports/.{}.{token}.stage", plan.build_id);
    if token.is_empty()
        || attempt.final_ref != plan.final_ref
        || attempt.stage_ref != expected_stage
    {
        return Err(CoreError::AuthorityConflict(
            "publication attempt paths or ownership are invalid".into(),
        ));
    }
    Ok(())
}

fn artifact_path(store: &ProjectDatabase, reference: &str) -> CoreResult<PathBuf> {
    let parts = reference.split('/').collect::<Vec<_>>();
    if parts.len() != 2
        || parts[0] != "exports"
        || parts[1].is_empty()
        || matches!(parts[1], "." | "..")
        || parts[1].contains('\0')
        || parts[1].contains('\\')
    {
        return Err(CoreError::InvalidProject(
            "publication output reference is invalid".into(),
        ));
    }
    let data_root = store
        .path()
        .parent()
        .ok_or_else(|| CoreError::Storage("project database has no data root".into()))?;
    Ok(data_root
        .join(Path::new(parts[0]))
        .join(Path::new(parts[1])))
}

#[derive(Deserialize, Serialize)]
struct IdentityRecord {
    volume_id: u64,
    file_id_low: u64,
    file_id_high: u64,
    link_count: u64,
    byte_size: u64,
}

fn identity_json(identity: QfNativeIdentity) -> CoreResult<String> {
    serde_json::to_string(&IdentityRecord {
        volume_id: identity.volume_id,
        file_id_low: identity.file_id_low,
        file_id_high: identity.file_id_high,
        link_count: identity.link_count,
        byte_size: identity.byte_size,
    })
    .map_err(|error| CoreError::Serialization(error.to_string()))
}

fn parse_identity(value: &str) -> CoreResult<QfNativeIdentity> {
    let value: IdentityRecord =
        serde_json::from_str(value).map_err(|error| CoreError::Serialization(error.to_string()))?;
    Ok(QfNativeIdentity {
        volume_id: value.volume_id,
        file_id_low: value.file_id_low,
        file_id_high: value.file_id_high,
        link_count: value.link_count,
        byte_size: value.byte_size,
        attributes: 0,
        reparse_tag: 0,
    })
}

fn require_identity(expected: QfNativeIdentity, actual: QfNativeIdentity) -> CoreResult<()> {
    if expected.volume_id != actual.volume_id
        || expected.file_id_low != actual.file_id_low
        || expected.file_id_high != actual.file_id_high
        || expected.byte_size != actual.byte_size
        || actual.link_count != 1
    {
        return Err(CoreError::AuthorityConflict(
            "publication file identity changed".into(),
        ));
    }
    Ok(())
}

fn validate_artifact_bytes(bytes: &[u8], fingerprint: &str, byte_size: u64) -> CoreResult<()> {
    if bytes.len() as u64 != byte_size
        || sha256_fingerprint(bytes) != fingerprint
        || std::str::from_utf8(bytes).is_err()
    {
        return Err(CoreError::AuthorityConflict(
            "publication artifact bytes are invalid".into(),
        ));
    }
    Ok(())
}

fn native_error(error: quillframe_native::NativeError) -> CoreError {
    CoreError::Storage(error.to_string())
}
fn storage(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}
