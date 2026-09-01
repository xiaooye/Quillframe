use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use rusqlite::{params, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};

use crate::{
    fingerprint::sha256_fingerprint, AcceptanceDecision, AuthStyle, AuthorActivation,
    BoundRuleMaterial, CandidateArtifact, ChapterTrackingProposal, CharacterSimulation,
    ContextManifest, ContextQueryPlan, ContextSelectionProposal, ContextStage, CoreError,
    CoreResult, CorpusDatabase, FeedbackInterpretation, GlobalDatabase, ModelRequest, ModelResult,
    ModelRuntime, ModelServiceRecord, ModelUsage, NativeProject, PlanBody, PlanMode, PlanProposal,
    PlanProposalInput, PreferenceReviewResult, ProductionIntent, ProductionRelease,
    ProductionRequest, ProductionTaskMode, ProjectManifest, PromptAssembly, ProtocolFamily,
    RepairBinding, RepairComparison, RepairGenerationMode, RepairSpec, ReviewMode, ReviewReport,
    ReviewReportInput, RevisionRequest, SceneResolution, SecretStore, SemanticGate,
    SemanticGateDecision, ServiceEndpoint, SettlementAuthorization, StageCallState, StageJob,
    SurfaceRealization, WriterCorpusSelection, WriterPreferenceSelection,
};

const CONTRACT: &str = include_str!("../../../studio/host_bridge_contract.json");
const IMPLEMENTED_OPERATIONS: &[&str] = &[
    "bridge.describe",
    "database.doctor",
    "project.list",
    "project.create",
    "project.open",
    "project.inspect",
    "project.story.restore_latest_snapshot",
    "chapter.create",
    "chapter.list",
    "story.inspect",
    "plan.inspect",
    "plan.save",
    "model.service.add",
    "model.service.discover",
    "model.service.test",
    "model.service.list",
    "model.service.get",
    "model.service.token.replace",
    "model.service.token.remove",
    "model.service.delete",
    "author.run.start",
    "author.run.status",
    "author.run.cancel",
    "author.run.execute",
    "document.create",
    "document.list",
    "document.open",
    "document.revisions.list",
    "document.revision.save",
    "inspector.candidates.list",
    "candidate.review.get",
    "candidate.visible.get",
    "candidate.accept",
    "candidate.revision.request",
    "settlement.preflight",
    "settlement.apply",
    "publication.preview",
    "publication.build",
    "publication.artifact.get",
    "publication.collection.build",
    "corpus.collection.scan",
    "corpus.selection.propose",
    "corpus.selection.confirm",
    "corpus.study.start",
    "corpus.study.status",
    "corpus.study.resume",
    "corpus.study.cancel",
    "corpus.pack.preview",
    "corpus.pack.activate",
    "learning.feedback.observe",
    "learning.feedback.execute",
    "learning.feedback.resume",
    "learning.feedback.get",
    "learning.feedback.list",
    "learning.preference.get",
    "learning.preference.list",
    "learning.preference.review",
    "learning.preference.activate",
    "learning.preference.deactivate",
];

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct BridgeRequest {
    pub schema: String,
    pub bridge_version: String,
    pub request_id: String,
    pub operation: String,
    pub surface: String,
    pub args: Map<String, Value>,
    pub authority: bool,
}

pub struct HostBridgeRuntime {
    global_root: PathBuf,
    global: Mutex<GlobalDatabase>,
    contract: Value,
    secrets: Option<Arc<dyn SecretStore>>,
}

struct RepairMaterial {
    manuscript: String,
    diagnosis: Value,
    source_revision: u32,
    source_receipt: String,
}

impl HostBridgeRuntime {
    pub fn open(global_root: impl Into<PathBuf>) -> CoreResult<Self> {
        Self::open_internal(global_root.into(), None)
    }

    pub fn open_with_secret_store(
        global_root: impl Into<PathBuf>,
        secrets: Arc<dyn SecretStore>,
    ) -> CoreResult<Self> {
        Self::open_internal(global_root.into(), Some(secrets))
    }

    fn open_internal(
        global_root: PathBuf,
        secrets: Option<Arc<dyn SecretStore>>,
    ) -> CoreResult<Self> {
        let global = if global_root.join("global.sqlite").exists() {
            GlobalDatabase::open(&global_root)?
        } else {
            GlobalDatabase::create(&global_root, &timestamp())?
        };
        let contract: Value = serde_json::from_str(CONTRACT)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(Self {
            global_root,
            global: Mutex::new(global),
            contract,
            secrets,
        })
    }

    pub fn invoke_value(&self, value: Value) -> Value {
        let parsed = serde_json::from_value::<BridgeRequest>(value.clone());
        let request = match parsed {
            Ok(request) => request,
            Err(error) => {
                return self.envelope(
                    value,
                    None,
                    "invalid",
                    Value::Null,
                    json!({"code":"invalid_request","message":error.to_string()}),
                )
            }
        };
        if request.schema != "quillframe_host_bridge_request_v11"
            || request.bridge_version != "11"
            || request.authority
            || request.request_id.trim().is_empty()
        {
            return self.envelope(
                value,
                Some(&request),
                "invalid",
                Value::Null,
                json!({"code":"invalid_request_contract","message":"request contract mismatch"}),
            );
        }
        let Some(operation_contract) = self
            .contract
            .get("operations")
            .and_then(|operations| operations.get(&request.operation))
        else {
            return self.envelope(
                value,
                Some(&request),
                "unsupported",
                Value::Null,
                json!({"code":"unsupported_operation","message":"operation is not registered"}),
            );
        };
        if let Some(missing) = operation_contract
            .get("required_args")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .find(|name| !request.args.contains_key(*name))
        {
            return self.envelope(
                value,
                Some(&request),
                "invalid",
                Value::Null,
                json!({"code":"missing_required_arg","message":format!("missing {missing}")}),
            );
        }
        if let Some(allowed) = operation_contract
            .get("allowed_surfaces")
            .and_then(Value::as_array)
        {
            if !allowed
                .iter()
                .any(|surface| surface.as_str() == Some(&request.surface))
            {
                return self.envelope(
                    value,
                    Some(&request),
                    "invalid",
                    Value::Null,
                    json!({"code":"surface_rejected","message":"operation is unavailable on this surface"}),
                );
            }
        }
        match self.dispatch(&request) {
            Ok(data) => self.envelope(value, Some(&request), "ok", data, Value::Null),
            Err(CoreError::InvalidProject(message))
            | Err(CoreError::InvalidHierarchy(message))
            | Err(CoreError::InvalidPlan(message))
            | Err(CoreError::AuthorityConflict(message))
            | Err(CoreError::ContextBoundary(message)) => self.envelope(
                value,
                Some(&request),
                "failed",
                Value::Null,
                json!({"code":"core_contract_failed","message":message}),
            ),
            Err(error) => self.envelope(
                value,
                Some(&request),
                "error",
                Value::Null,
                json!({"code":"core_error","message":error.to_string()}),
            ),
        }
    }

    pub async fn invoke_value_async(&self, value: Value) -> Value {
        let Ok(request) = serde_json::from_value::<BridgeRequest>(value.clone()) else {
            return self.invoke_value(value);
        };
        if !matches!(
            request.operation.as_str(),
            "model.service.add"
                | "model.service.discover"
                | "model.service.test"
                | "author.run.execute"
                | "corpus.study.start"
                | "corpus.study.resume"
                | "learning.feedback.execute"
                | "learning.feedback.resume"
                | "learning.preference.review"
        ) {
            return self.invoke_value(value);
        }
        if request.schema != "quillframe_host_bridge_request_v11"
            || request.bridge_version != "11"
            || request.authority
            || request.request_id.trim().is_empty()
        {
            return self.invoke_value(value);
        }
        let Some(operation_contract) = self
            .contract
            .get("operations")
            .and_then(|operations| operations.get(&request.operation))
        else {
            return self.invoke_value(value);
        };
        let missing = operation_contract
            .get("required_args")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(Value::as_str)
            .any(|name| !request.args.contains_key(name));
        let surface_rejected = operation_contract
            .get("allowed_surfaces")
            .and_then(Value::as_array)
            .is_some_and(|allowed| {
                !allowed
                    .iter()
                    .any(|surface| surface.as_str() == Some(&request.surface))
            });
        if missing || surface_rejected {
            return self.invoke_value(value);
        }
        let result = match request.operation.as_str() {
            "model.service.add" => match self.model_service_add(&request) {
                Ok(saved) => {
                    let service_id = saved
                        .pointer("/service/service_id")
                        .and_then(Value::as_str)
                        .ok_or_else(|| {
                            CoreError::Storage("saved model service id is missing".into())
                        });
                    match service_id {
                        Ok(service_id) => self.discover_service(service_id).await,
                        Err(error) => Err(error),
                    }
                }
                Err(error) => Err(error),
            },
            "model.service.discover" | "model.service.test" => {
                self.model_service_discover(&request).await
            }
            "author.run.execute" => self.author_run_execute(&request).await,
            "corpus.study.start" | "corpus.study.resume" => {
                self.corpus_study_execute(&request).await
            }
            "learning.feedback.execute" | "learning.feedback.resume" => {
                self.learning_feedback_execute(&request).await
            }
            "learning.preference.review" => self.learning_preference_review(&request).await,
            _ => unreachable!(),
        };
        match result {
            Ok(data) => self.envelope(value, Some(&request), "ok", data, Value::Null),
            Err(CoreError::InvalidProject(message))
            | Err(CoreError::InvalidHierarchy(message))
            | Err(CoreError::InvalidPlan(message))
            | Err(CoreError::AuthorityConflict(message))
            | Err(CoreError::ContextBoundary(message)) => self.envelope(
                value,
                Some(&request),
                "failed",
                Value::Null,
                json!({"code":"core_contract_failed","message":message}),
            ),
            Err(error) => self.envelope(
                value,
                Some(&request),
                "error",
                Value::Null,
                json!({"code":"core_error","message":error.to_string()}),
            ),
        }
    }

    fn dispatch(&self, request: &BridgeRequest) -> CoreResult<Value> {
        match request.operation.as_str() {
            "bridge.describe" => {
                let registered = self.contract["operations"].as_object().unwrap();
                let operation_contracts = registered
                    .iter()
                    .filter(|(name, _)| IMPLEMENTED_OPERATIONS.contains(&name.as_str()))
                    .map(|(name, value)| (name.clone(), value.clone()))
                    .collect::<Map<_, _>>();
                let operations = operation_contracts.keys().cloned().collect::<Vec<_>>();
                let deferred_operations = registered
                    .iter()
                    .filter(|(name, _)| !IMPLEMENTED_OPERATIONS.contains(&name.as_str()))
                    .map(|(name, value)| (name.clone(), value.clone()))
                    .collect::<Map<_, _>>();
                Ok(json!({
                    "schema":"quillframe_bridge_description_v11",
                    "framework_version":self.contract["framework_version"],
                    "contract_version":self.contract["version"],
                    "surface":request.surface,
                    "operations":operations,
                    "operation_contracts":operation_contracts,
                    "deferred_operations":deferred_operations,
                    "authority":false,"canon_authority":false,
                    "framework_write_authority":false,"settlement_authority":false,
                    "direct_core_store_access":false
                }))
            }
            "database.doctor" => {
                let global = self.lock_global()?;
                crate::validate_current_global_schema(global.connection())?;
                Ok(
                    json!({"schema":"quillframe_database_doctor_v1","ok":true,"checks":["global_schema"],"errors":[],"authority":false}),
                )
            }
            "project.list" => {
                let projects = self.lock_global()?.projects()?;
                Ok(
                    json!({"schema":"quillframe_project_list_v1","items":projects,"authority":false}),
                )
            }
            "project.create" => self.create_project(request),
            "project.open" | "project.inspect" => self.inspect_project(request),
            "project.story.restore_latest_snapshot" => self.restore_story_snapshot(request),
            "chapter.create" => self.chapter_create(request),
            "chapter.list" => self.chapter_list(request),
            "story.inspect" => self.story_inspect(request),
            "plan.inspect" => self.plan_inspect(request),
            "plan.save" => self.plan_save(request),
            "model.service.add" => self.model_service_add(request),
            "model.service.list" => self.model_service_list(),
            "model.service.get" => self.model_service_get(request),
            "model.service.token.replace" => self.model_service_token_replace(request),
            "model.service.token.remove" => self.model_service_token_remove(request),
            "model.service.delete" => self.model_service_delete(request),
            "author.run.start" => self.author_run_start(request),
            "author.run.status" => self.author_run_status(request),
            "author.run.cancel" => self.author_run_cancel(request),
            "document.create" => self.document_create(request),
            "document.list" => self.document_list(request),
            "document.open" => self.document_open(request),
            "document.revisions.list" => self.document_revisions(request),
            "document.revision.save" => self.document_revision_save(request),
            "inspector.candidates.list" => self.candidate_list(request),
            "candidate.review.get" => self.candidate_review_get(request),
            "candidate.visible.get" => self.candidate_visible_get(request),
            "candidate.accept" => self.candidate_accept(request),
            "candidate.revision.request" => self.candidate_revision_request(request),
            "settlement.preflight" => self.settlement_preflight(request),
            "settlement.apply" => self.settlement_apply(request),
            "publication.preview" => self.publication_preview(request),
            "publication.build" => self.publication_build(request),
            "publication.artifact.get" => self.publication_artifact_get(request),
            "publication.collection.build" => self.publication_collection_build(request),
            "corpus.collection.scan" => self.corpus_collection_scan(request),
            "corpus.selection.propose" => self.corpus_selection_propose(request),
            "corpus.selection.confirm" => self.corpus_selection_confirm(request),
            "corpus.study.status" => self.corpus_study_status(request),
            "corpus.study.cancel" => self.corpus_study_cancel(request),
            "corpus.pack.preview" => self.corpus_pack_preview(request),
            "corpus.pack.activate" => self.corpus_pack_activate(request),
            "learning.feedback.observe" => self.learning_feedback_observe(request),
            "learning.feedback.get" => self.learning_feedback_get(request),
            "learning.feedback.list" => self.learning_feedback_list(request),
            "learning.preference.get" => self.learning_preference_get(request),
            "learning.preference.list" => self.learning_preference_list(request),
            "learning.preference.activate" => self.learning_preference_activation(request, true),
            "learning.preference.deactivate" => self.learning_preference_activation(request, false),
            "learning.feedback.execute"
            | "learning.feedback.resume"
            | "learning.preference.review" => Err(CoreError::ModelRuntime(
                "semantic learning operation requires async bridge invocation".into(),
            )),
            _ => Err(CoreError::InvalidProject(format!(
                "registered operation {} has not migrated to Rust yet",
                request.operation
            ))),
        }
    }

    fn create_project(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let title = string_arg(request, "title")?;
        let language = request
            .args
            .get("language")
            .and_then(Value::as_str)
            .unwrap_or("zh-CN");
        let root = self.global_root.join("projects").join(project_id);
        let manifest = ProjectManifest::new(project_id, title, language)?;
        let project = NativeProject::create(&root, manifest.clone(), &timestamp())?;
        let context_fingerprint = project.context.manifest_fingerprint.clone();
        drop(project);
        self.lock_global()?
            .register_project(&manifest, &root, &timestamp())?;
        Ok(json!({
            "schema":"quillframe_project_create_v1","project_id":project_id,
            "manifest":manifest,"project_dir":root,"project_fingerprint":context_fingerprint,
            "authority":false
        }))
    }

    fn restore_story_snapshot(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let expected_revision = request
            .args
            .get("expected_revision")
            .and_then(Value::as_u64)
            .ok_or_else(|| {
                CoreError::InvalidProject("expected_revision must be an unsigned integer".into())
            })?;
        let registered = self
            .lock_global()?
            .project(project_id)?
            .ok_or_else(|| CoreError::InvalidProject("project is not registered".into()))?;
        let project_root = PathBuf::from(registered.project_dir);
        let manifest_bytes = std::fs::read(project_root.join("quillframe.toml"))
            .map_err(|error| CoreError::Storage(format!("manifest read failed: {error}")))?;
        let context = ProjectManifest::resolve(&project_root, &manifest_bytes)?;
        let snapshot_id = crate::ProjectDatabase::restore_latest_story_snapshot(
            &context.data_root.join("project.sqlite"),
            &context.manifest,
            expected_revision,
        )?;
        Ok(json!({
            "schema":"quillframe_story_snapshot_restore_v1",
            "project_id":project_id,
            "revision":expected_revision,
            "snapshot_id":snapshot_id,
            "status":"restored",
            "semantic_inference":false,
            "authority":false
        }))
    }

    fn inspect_project(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let registered = self
            .lock_global()?
            .project(project_id)?
            .ok_or_else(|| CoreError::InvalidProject("project is not registered".into()))?;
        let project = NativeProject::open(Path::new(&registered.project_dir))?;
        Ok(json!({
            "schema":"quillframe_project_inspection_v1","manifest":project.context.manifest,
            "project_dir":registered.project_dir,"data_root":project.context.data_root,
            "manifest_fingerprint":project.context.manifest_fingerprint,
            "authority":false
        }))
    }

    fn chapter_list(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project = self.open_registered(string_arg(request, "project_id")?)?;
        let mut statement = project
            .database
            .connection()
            .prepare(
                "SELECT n.node_id,n.ordinal,n.title,d.document_id \
                 FROM story_nodes n JOIN documents d ON d.story_node_id=n.node_id \
                 WHERE n.kind='chapter' AND d.document_kind='manuscript' ORDER BY n.ordinal",
            )
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        let items = statement
            .query_map([], |row| {
                Ok(json!({"chapter_id":row.get::<_,String>(0)?,"ordinal":row.get::<_,u32>(1)?,"title":row.get::<_,String>(2)?,"document_id":row.get::<_,String>(3)?}))
            })
            .map_err(|error| CoreError::Storage(error.to_string()))?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        Ok(
            json!({"schema":"quillframe_chapter_list_v1","project_id":string_arg(request,"project_id")?,"items":items,"authority":false}),
        )
    }

    fn chapter_create(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let title = string_arg(request, "title")?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let unit_id = request.args.get("unit_id").and_then(Value::as_str);
        let mut project = self.open_registered(project_id)?;
        let receipt = project.database.create_chapter(
            project_id,
            unit_id,
            title,
            idempotency_key,
            &timestamp(),
        )?;
        Ok(json!({
            "schema":"quillframe_chapter_create_v1",
            "project_id":project_id,
            "chapter_id":receipt.chapter_id,
            "document_id":receipt.document_id,
            "unit_id":receipt.unit_id,
            "ordinal":receipt.ordinal,
            "title":receipt.title,
            "request_fingerprint":receipt.request_fingerprint,
            "replayed":receipt.replayed,
            "authority":false
        }))
    }

    fn story_inspect(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project = self.open_registered(string_arg(request, "project_id")?)?;
        let mut statement = project
            .database
            .connection()
            .prepare("SELECT node_id,parent_id,kind,ordinal,title FROM story_nodes ORDER BY kind,ordinal")
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        let nodes = statement
            .query_map([], |row| {
                Ok(json!({"node_id":row.get::<_,String>(0)?,"parent_id":row.get::<_,Option<String>>(1)?,"kind":row.get::<_,String>(2)?,"ordinal":row.get::<_,u32>(3)?,"title":row.get::<_,String>(4)?}))
            })
            .map_err(|error| CoreError::Storage(error.to_string()))?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        Ok(
            json!({"schema":"quillframe_story_inspection_v1","project_id":string_arg(request,"project_id")?,"nodes":nodes,"authority":false}),
        )
    }

    fn plan_inspect(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let requested_target = request.args.get("target_ref").and_then(Value::as_str);
        let canonical_target = requested_target.map(canonical_plan_target).transpose()?;
        let project = self.open_registered(project_id)?;
        let mut statement = project.database.connection().prepare(
            "SELECT v.proposal_id,v.target_ref,v.title,v.content,a.active_version,p.status, \
             v.reader_intent_json,v.expectation_refs_json FROM plan_editor_views v \
             JOIN plans p ON p.plan_id=v.proposal_id LEFT JOIN plan_activations a ON a.proposal_id=v.proposal_id \
             WHERE (?1 IS NULL OR v.target_ref=?1) ORDER BY v.created_at DESC,v.proposal_id DESC"
        ).map_err(storage)?;
        let rows=statement.query_map([canonical_target],|row|{
            let target:String=row.get(1)?;
            let reader:String=row.get(6)?;
            let expectations:String=row.get(7)?;
            Ok(json!({"plan_id":row.get::<_,String>(0)?,
                "target_ref":if requested_target==Some("book") && target=="book:BOOK" {"book"} else {target.as_str()},
                "title":row.get::<_,String>(2)?,"content":row.get::<_,String>(3)?,
                "version":row.get::<_,Option<u64>>(4)?.unwrap_or(1),"status":row.get::<_,String>(5)?,
                "reader_intent":serde_json::from_str::<Value>(&reader).unwrap_or_else(|_|json!({})),
                "expectation_refs":serde_json::from_str::<Value>(&expectations).unwrap_or_else(|_|json!([])),"horizon":null}))
        }).map_err(storage)?.collect::<Result<Vec<_>,_>>().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_plan_inspection_v1","project_id":project_id,"items":rows,"authority":false}),
        )
    }

    fn plan_save(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let requested_target = string_arg(request, "target_ref")?;
        let canonical_target = canonical_plan_target(requested_target)?;
        let title = string_arg(request, "title")?;
        let content = request
            .args
            .get("content")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidPlan("plan content must be text".into()))?;
        let expected_version = request
            .args
            .get("expected_version")
            .and_then(Value::as_u64)
            .ok_or_else(|| CoreError::InvalidPlan("expected plan version is required".into()))?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let reader_intent = request
            .args
            .get("reader_intent")
            .cloned()
            .unwrap_or_else(|| json!({}));
        if !reader_intent.is_object() {
            return Err(CoreError::InvalidPlan(
                "reader intent must be an object".into(),
            ));
        }
        let expectation_refs = request
            .args
            .get("expectation_refs")
            .cloned()
            .map(serde_json::from_value::<Vec<String>>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidPlan(format!("expectation refs are invalid: {error}"))
            })?
            .unwrap_or_default();
        let mut project = self.open_registered(project_id)?;
        if let Some(existing)=project.database.connection().query_row(
            "SELECT v.target_ref,v.title,v.content,v.reader_intent_json,v.expectation_refs_json,a.active_version,v.proposal_id \
             FROM plan_activations a JOIN plan_editor_views v ON v.proposal_id=a.proposal_id \
             WHERE json_extract(a.authorization_json,'$.idempotency_key')=?1",
            [idempotency_key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?,
                row.get::<_,String>(3)?,row.get::<_,String>(4)?,row.get::<_,u64>(5)?,row.get::<_,String>(6)?))
        ).optional().map_err(storage)? {
            let expected_reader=serde_json::to_string(&reader_intent).map_err(|error|CoreError::Serialization(error.to_string()))?;
            let expected_refs=serde_json::to_string(&expectation_refs).map_err(|error|CoreError::Serialization(error.to_string()))?;
            if existing.0!=canonical_target || existing.1!=title || existing.2!=content || existing.3!=expected_reader || existing.4!=expected_refs {
                return Err(CoreError::AuthorityConflict("plan idempotency key binds different content".into()));
            }
            return Ok(json!({"schema":"quillframe_plan_save_result_v1","project_id":project_id,"plan_id":existing.6,
                "target_ref":requested_target,"title":title,"content":content,"version":existing.5,"status":"active",
                "reader_intent":reader_intent,"expectation_refs":expectation_refs,"horizon":null,"authority":false}));
        }
        let graph = project.database.load_story_graph()?;
        let (mode, node_id) = if canonical_target == "book:BOOK" {
            (PlanMode::DesignBook, "BOOK".to_string())
        } else if let Some(node) = canonical_target.strip_prefix("volume:") {
            (PlanMode::DesignVolume, node.to_owned())
        } else if let Some(node) = canonical_target.strip_prefix("unit:") {
            (PlanMode::PlanUnit, node.to_owned())
        } else if let Some(node) = canonical_target.strip_prefix("chapter:") {
            (PlanMode::PlanChapter, node.to_owned())
        } else {
            return Err(CoreError::InvalidPlan(
                "Studio plan target must be book, volume, unit or chapter".into(),
            ));
        };
        let body_value = request
            .args
            .get("typed_body")
            .cloned()
            .unwrap_or_else(|| serde_json::from_str::<Value>(content).unwrap_or(Value::Null));
        let body: PlanBody = serde_json::from_value(body_value).map_err(|error| {
            CoreError::InvalidPlan(format!("typed plan body is invalid: {error}"))
        })?;
        let mut dependency_fingerprints = request
            .args
            .get("dependency_fingerprints")
            .cloned()
            .map(serde_json::from_value::<BTreeMap<String, String>>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidPlan(format!("plan dependencies are invalid: {error}"))
            })?
            .unwrap_or_default();
        for (reference, fingerprint) in project.database.active_ancestor_fingerprints(&node_id)? {
            if dependency_fingerprints
                .insert(reference.clone(), fingerprint.clone())
                .is_some_and(|explicit| explicit != fingerprint)
            {
                return Err(CoreError::AuthorityConflict(format!(
                    "explicit plan dependency conflicts with active ancestor {reference}"
                )));
            }
        }
        let proposal = PlanProposal::create(
            &graph,
            PlanProposalInput {
                mode,
                node_id,
                expected_active_version: expected_version,
                body,
                assumptions: request
                    .args
                    .get("assumptions")
                    .cloned()
                    .map(serde_json::from_value)
                    .transpose()
                    .map_err(|error| {
                        CoreError::InvalidPlan(format!("plan assumptions are invalid: {error}"))
                    })?
                    .unwrap_or_default(),
                open_questions: request
                    .args
                    .get("open_questions")
                    .cloned()
                    .map(serde_json::from_value)
                    .transpose()
                    .map_err(|error| {
                        CoreError::InvalidPlan(format!("plan open questions are invalid: {error}"))
                    })?
                    .unwrap_or_default(),
                dependency_fingerprints,
            },
        )?;
        let authorization =
            AuthorActivation::authorize(&proposal, "author:studio", timestamp(), idempotency_key)?;
        let version = project.database.save_and_activate_editor_plan(
            &proposal,
            &authorization,
            title,
            content,
            &reader_intent,
            &expectation_refs,
        )?;
        Ok(
            json!({"schema":"quillframe_plan_save_result_v1","project_id":project_id,"plan_id":proposal.id.to_string(),
            "target_ref":requested_target,"title":title,"content":content,"version":version,"status":"active",
            "reader_intent":reader_intent,"expectation_refs":expectation_refs,"horizon":null,"authority":false}),
        )
    }

    fn model_service_add(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let endpoint_url = string_arg(request, "endpoint")?;
        let existing = self
            .lock_global()?
            .model_service_by_endpoint(endpoint_url)?;
        let service_id = existing
            .as_ref()
            .map(|record| record.endpoint.service_id.clone())
            .unwrap_or_else(|| format!("svc-{}", uuid::Uuid::new_v4().simple()));
        let token = request
            .args
            .get("access_token")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty());
        let auth_style = parse_auth_style(
            request.args.get("auth_style").and_then(Value::as_str),
            token.is_some(),
        )?;
        let protocol_family =
            parse_protocol_family(request.args.get("protocol_family").and_then(Value::as_str))?;
        let new_credential_ref =
            token.map(|_| format!("keyring:qf:{}", uuid::Uuid::new_v4().simple()));
        if let (Some(secret), Some(reference)) = (token, new_credential_ref.as_deref()) {
            self.secret_store()?.write_secret(reference, secret)?;
        }
        let endpoint = ServiceEndpoint {
            service_id: service_id.clone(),
            endpoint: endpoint_url.into(),
            credential_ref: new_credential_ref.clone(),
            auth_style,
            protocol_family,
            allow_loopback_http: request
                .args
                .get("allow_loopback_http")
                .and_then(Value::as_bool)
                .unwrap_or(false),
        };
        let expected_version = existing.as_ref().map_or(0, |record| record.version);
        let saved =
            self.lock_global()?
                .save_model_service(&endpoint, expected_version, &timestamp());
        let saved = match saved {
            Ok(saved) => saved,
            Err(error) => {
                if let Some(reference) = new_credential_ref.as_deref() {
                    let _ = self.secret_store()?.delete_secret(reference);
                }
                return Err(error);
            }
        };
        if let Some(old) = existing
            .and_then(|record| record.endpoint.credential_ref)
            .filter(|old| Some(old.as_str()) != new_credential_ref.as_deref())
        {
            self.secret_store()?.delete_secret(&old)?;
        }
        Ok(json!({
            "schema":"quillframe_model_service_result_v1","service":model_service_projection(&saved),
            "secret_values_persisted":false,"authority":false
        }))
    }

    fn model_service_list(&self) -> CoreResult<Value> {
        let items = self
            .lock_global()?
            .model_services()?
            .iter()
            .map(model_service_projection)
            .collect::<Vec<_>>();
        Ok(json!({"schema":"quillframe_model_service_list_v1","items":items,"authority":false}))
    }

    fn model_service_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let service_id = string_arg(request, "service_id")?;
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        Ok(
            json!({"schema":"quillframe_model_service_result_v1","service":model_service_projection(&service),"authority":false}),
        )
    }

    fn model_service_token_replace(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let service_id = string_arg(request, "service_id")?;
        let access_token = string_arg(request, "access_token")?;
        let current = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        let new_reference = format!("keyring:qf:{}", uuid::Uuid::new_v4().simple());
        self.secret_store()?
            .write_secret(&new_reference, access_token)?;
        let mut endpoint = current.endpoint.clone();
        endpoint.credential_ref = Some(new_reference.clone());
        if endpoint.auth_style == AuthStyle::None {
            endpoint.auth_style = AuthStyle::Bearer;
        }
        let saved =
            self.lock_global()?
                .save_model_service(&endpoint, current.version, &timestamp());
        let saved = match saved {
            Ok(saved) => saved,
            Err(error) => {
                let _ = self.secret_store()?.delete_secret(&new_reference);
                return Err(error);
            }
        };
        if let Some(old) = current.endpoint.credential_ref {
            self.secret_store()?.delete_secret(&old)?;
        }
        Ok(
            json!({"schema":"quillframe_model_service_result_v1","service":model_service_projection(&saved),"authority":false}),
        )
    }

    fn model_service_token_remove(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let service_id = string_arg(request, "service_id")?;
        let current = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        let mut endpoint = current.endpoint.clone();
        endpoint.credential_ref = None;
        endpoint.auth_style = AuthStyle::None;
        let saved =
            self.lock_global()?
                .save_model_service(&endpoint, current.version, &timestamp())?;
        if let Some(old) = current.endpoint.credential_ref {
            self.secret_store()?.delete_secret(&old)?;
        }
        Ok(
            json!({"schema":"quillframe_model_service_result_v1","service":model_service_projection(&saved),"authority":false}),
        )
    }

    fn model_service_delete(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let service_id = string_arg(request, "service_id")?;
        let current = self.lock_global()?.model_service(service_id)?;
        if let Some(reference) = current
            .as_ref()
            .and_then(|record| record.endpoint.credential_ref.as_deref())
        {
            self.secret_store()?.delete_secret(reference)?;
        }
        let deleted = self.lock_global()?.delete_model_service(service_id)?;
        Ok(
            json!({"schema":"quillframe_model_service_delete_v1","service_id":service_id,"deleted":deleted,"authority":false}),
        )
    }

    async fn model_service_discover(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let service_id = string_arg(request, "service_id")?;
        self.discover_service(service_id).await
    }

    async fn discover_service(&self, service_id: &str) -> CoreResult<Value> {
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        if !service.enabled {
            return Err(CoreError::InvalidProject(
                "model service is disabled".into(),
            ));
        }
        let catalog = ModelRuntime::new(self.secret_store()?)
            .discover_models(&service.endpoint)
            .await?;
        self.lock_global()?
            .record_model_catalog(service_id, &catalog, &timestamp())?;
        let refreshed = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service disappeared".into()))?;
        Ok(json!({
            "schema":"quillframe_model_service_discovery_v1","service":model_service_projection(&refreshed),
            "catalog_fingerprint":catalog.fingerprint,"authority":false
        }))
    }

    fn author_run_start(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let task_mode_text = string_arg(request, "task_mode")?;
        let task_mode = match task_mode_text {
            "DRAFT" => ProductionTaskMode::Draft,
            "REVISE" => ProductionTaskMode::Revise,
            _ => {
                return Err(CoreError::InvalidProject(
                    "author run task_mode must be DRAFT or REVISE".into(),
                ))
            }
        };
        let payload = object_arg(request, "payload")?;
        let document_id = request
            .args
            .get("target_ref")
            .and_then(Value::as_str)
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| {
                CoreError::InvalidProject("author run requires a document target_ref".into())
            })?;
        let mut instruction = payload
            .get("instruction")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .trim()
            .to_owned();
        if task_mode == ProductionTaskMode::Draft && instruction.is_empty() {
            return Err(CoreError::InvalidProject(
                "DRAFT author run requires an instruction".into(),
            ));
        }
        let mut reader_grip = payload
            .get("reader_grip")
            .and_then(Value::as_str)
            .unwrap_or("high")
            .to_owned();
        let mut author_profile = payload
            .get("author_profile")
            .and_then(Value::as_str)
            .unwrap_or("balanced")
            .to_owned();
        let mut rule_material = payload
            .get("rule_material")
            .cloned()
            .map(serde_json::from_value::<Vec<BoundRuleMaterial>>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidProject(format!("rule material is invalid: {error}"))
            })?
            .unwrap_or_else(|| {
                if instruction.is_empty() {
                    vec![]
                } else {
                    vec![BoundRuleMaterial {
                        id: "current-request".into(),
                        authority: "current_request".into(),
                        statement: instruction.clone(),
                    }]
                }
            });
        let mut selected_preference_ids = payload
            .get("selected_preference_ids")
            .cloned()
            .map(serde_json::from_value::<Vec<String>>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidProject(format!("selected preference ids are invalid: {error}"))
            })?
            .unwrap_or_default();
        rule_material.retain(|rule| !rule.statement.trim().is_empty());
        let repair_source = payload
            .get("repair_source")
            .cloned()
            .map(serde_json::from_value::<RepairBinding>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidProject(format!("repair source is invalid: {error}"))
            })?;
        let mut project = self.open_registered(project_id)?;
        let chapter_id = project
            .database
            .connection()
            .query_row(
                "SELECT story_node_id FROM documents WHERE document_id=?1 AND document_kind='manuscript'",
                [document_id],
                |row| row.get::<_, String>(0),
            )
            .map_err(storage)?;
        if let Some(requested_chapter_id) = payload.get("chapter_id").and_then(Value::as_str) {
            if requested_chapter_id != chapter_id {
                return Err(CoreError::InvalidProject(
                    "author run chapter_id does not match the target document".into(),
                ));
            }
        }
        if task_mode == ProductionTaskMode::Revise {
            let binding = repair_source.as_ref().ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "REVISE requires an exact failed-candidate source".into(),
                )
            })?;
            let source = project.database.validate_repair_source(
                &binding.source_run_id,
                &binding.source_checkpoint_id,
                &binding.expected_candidate_fingerprint,
                document_id,
            )?;
            if instruction.is_empty() {
                instruction = source.intent.instruction;
            }
            if rule_material.is_empty() {
                rule_material = source.intent.rule_material;
            }
            if selected_preference_ids.is_empty() {
                selected_preference_ids = source.intent.selected_preference_ids;
            }
            if !payload.contains_key("reader_grip") {
                reader_grip = source.intent.reader_grip;
            }
            if !payload.contains_key("author_profile") {
                author_profile = source.intent.author_profile;
            }
        }
        let pack = project
            .database
            .freeze_writer_pack_for_chapter(&chapter_id, &timestamp())?;
        let run_id = format!("run-{}", uuid::Uuid::new_v4());
        let model_call_budget = payload
            .get("model_call_budget")
            .and_then(Value::as_u64)
            .map(u32::try_from)
            .transpose()
            .map_err(|_| CoreError::InvalidProject("model_call_budget exceeds u32".into()))?;
        let production = ProductionRequest::freeze(
            &run_id,
            task_mode,
            document_id,
            ProductionIntent {
                instruction,
                reader_grip,
                author_profile,
                rule_material,
                selected_preference_ids,
                repair_source,
            },
            &pack.fingerprint,
            sha256_fingerprint(CONTRACT.as_bytes()),
            payload
                .get("route_policy")
                .and_then(Value::as_str)
                .unwrap_or("role_capability_route"),
            model_call_budget,
        )?;
        project
            .database
            .start_production(&production, &timestamp())?;
        Ok(json!({
            "schema":"quillframe_author_run_start_result_v1","project_id":project_id,"run_id":run_id,"status":"ready",
            "task_mode":task_mode_text,"target_ref":production.target_ref,"request_fingerprint":production.fingerprint,
            "writer_pack_fingerprint":pack.fingerprint,"context_freeze_fingerprint":pack.context_freeze_fingerprint,
            "tracking_fingerprint":pack.tracking_fingerprint,"raw_draft_visible":false,"candidate_visible":false,
            "canon_authority":false,"settlement_authority":false,"message":"Production request frozen; no draft is visible before semantic gates complete.",
            "workflow":{"status":"ready","stage":"writer_pack_frozen","cursor":0,"authority":false},"authority":false
        }))
    }

    fn author_run_status(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let run_id = string_arg(request, "run_id")?;
        let project = self.open_registered(project_id)?;
        let (status, task_mode, target_ref, request_fingerprint, result_fingerprint): (
            String,
            String,
            Option<String>,
            String,
            Option<String>,
        ) = project
            .database
            .connection()
            .query_row(
                "SELECT status,task_mode,target_ref,request_fingerprint,result_fingerprint FROM runs WHERE run_id=?1",
                [run_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?)),
            )
            .map_err(storage)?;
        let calls = project.database.production_stage_calls(run_id)?;
        let confirmed = calls
            .iter()
            .filter(|call| call.state == crate::StageCallState::Confirmed)
            .count();
        let events = project.database.runtime_events(run_id)?;
        let journal_calls = calls
            .iter()
            .map(|call| {
                json!({"call_id":call.call_id,"stage_key":call.job.stage_key,"runtime_role":call.job.runtime_role,
                    "state":call.state,"error_code":call.error_code})
            })
            .collect::<Vec<_>>();
        let unconfirmed_call_ids = calls
            .iter()
            .filter(|call| call.state == StageCallState::Unconfirmed)
            .map(|call| call.call_id.clone())
            .collect::<Vec<_>>();
        let model_call_budget = project
            .database
            .load_production_request(run_id)?
            .model_call_budget;
        let candidate = project.database.connection().query_row(
            "SELECT c.candidate_id,c.document_id,c.revision_id,c.run_id,c.task_mode,c.candidate_kind,c.status, \
             c.content_fingerprint,c.user_visible_gate,c.created_at,p.release_fingerprint \
             FROM candidates c JOIN production_releases p ON p.candidate_id=c.candidate_id AND p.user_visible=1 \
             WHERE c.run_id=?1 ORDER BY c.created_at DESC,c.candidate_id DESC LIMIT 1",
            [run_id],|row|Ok(json!({"candidate_id":row.get::<_,String>(0)?,"document_id":row.get::<_,Option<String>>(1)?,
                "revision_id":row.get::<_,Option<String>>(2)?,"run_id":row.get::<_,Option<String>>(3)?,"task_mode":row.get::<_,String>(4)?,
                "candidate_kind":row.get::<_,String>(5)?,"status":row.get::<_,String>(6)?,"effective_status":row.get::<_,String>(6)?,
                "content_fingerprint":row.get::<_,String>(7)?,"candidate_fingerprint":row.get::<_,String>(7)?,
                "user_visible_gate":row.get::<_,String>(8)?,"created_at":row.get::<_,String>(9)?,"release_fingerprint":row.get::<_,String>(10)?}))
        ).optional().map_err(storage)?;
        let repair_source = project.database.connection().query_row(
            "SELECT checkpoint_id,artifact_fingerprint FROM checkpoints WHERE run_id=?1 \
             AND checkpoint_kind='failed_candidate_repair_source' ORDER BY created_at DESC,checkpoint_id DESC LIMIT 1",
            [run_id],|row|Ok(json!({"source_run_id":run_id,"source_checkpoint_id":row.get::<_,String>(0)?,
                "expected_candidate_fingerprint":row.get::<_,String>(1)?}))
        ).optional().map_err(storage)?;
        Ok(json!({
            "schema":"quillframe_author_run_status_v1","project_id":project_id,"run_id":run_id,"status":status,
            "task_mode":task_mode,"target_ref":target_ref,"request_fingerprint":request_fingerprint,
            "result_fingerprint":result_fingerprint,"events":events,"candidate":candidate,"repair_source":repair_source,
            "execution_journal":{"schema":"quillframe_production_execution_journal_v1","run_id":run_id,
                "request_fingerprint":request_fingerprint,"active_executor":false,"cancel_requested":false,
                "confirmed_call_count":confirmed,"dispatched_call_count":calls.len(),"model_call_budget":model_call_budget,
                "calls":journal_calls,"unconfirmed_call_ids":unconfirmed_call_ids,"private_payloads_visible":false,"authority":false},
            "dispatched_call_count":calls.len(),"confirmed_call_count":confirmed,
            "raw_draft_visible":false,"candidate_visible":candidate.is_some(),"active_executor":false,"authority":false
        }))
    }

    fn author_run_cancel(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let run_id = string_arg(request, "run_id")?;
        let cursor = request
            .args
            .get("cursor")
            .and_then(Value::as_u64)
            .ok_or_else(|| {
                CoreError::AuthorityConflict("cancellation cursor is required".into())
            })?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let mut project = self.open_registered(project_id)?;
        let (abandoned_call_count, replayed) =
            project
                .database
                .cancel_production(run_id, cursor, idempotency_key, &timestamp())?;
        Ok(json!({
            "schema":"quillframe_author_run_cancel_result_v1","project_id":project_id,
            "run_id":run_id,"status":"cancelled","abandoned_call_count":abandoned_call_count,
            "safe_replacement_allowed":true,"replacement_operation":"author.run.start",
            "replayed":replayed,"authority":false
        }))
    }

    async fn author_run_execute(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let run_id = string_arg(request, "run_id")?;
        let service_id = string_arg(request, "service_id")?;
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        if !service.enabled || service.discovery_state != "connected" {
            return Err(CoreError::ModelRuntime(
                "model service must pass discovery before production".into(),
            ));
        }
        let catalog = service.catalog.as_ref().ok_or_else(|| {
            CoreError::ModelRuntime("connected model service has no catalog".into())
        })?;
        catalog.validate()?;
        let model = request
            .args
            .get("model_id")
            .and_then(Value::as_str)
            .unwrap_or_else(|| catalog.models[0].model_id.as_str());
        if !catalog.models.iter().any(|item| item.model_id == model) {
            return Err(CoreError::ModelRuntime(
                "selected model is not in the discovered catalog".into(),
            ));
        }
        let (production, pack, tracking, repair_material) = {
            let project = self.open_registered(project_id)?;
            let production = project.database.load_production_request(run_id)?;
            if request
                .args
                .get("document_id")
                .and_then(Value::as_str)
                .is_some_and(|document_id| document_id != production.target_ref)
            {
                return Err(CoreError::AuthorityConflict(
                    "execute document does not match the frozen production target".into(),
                ));
            }
            let pack = project
                .database
                .load_writer_pack(&production.writer_pack_fingerprint)?;
            let tracking = project
                .database
                .load_tracking_state(project_id)?
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("tracking authority is unavailable".into())
                })?;
            tracking.validate()?;
            if tracking.fingerprint != pack.tracking_fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "tracking authority changed after Writer Pack freeze".into(),
                ));
            }
            let repair_material =
                if production.task_mode == ProductionTaskMode::Revise {
                    let binding = production.intent.repair_source.as_ref().ok_or_else(|| {
                        CoreError::AuthorityConflict("REVISE request has no repair source".into())
                    })?;
                    project.database.validate_repair_source(
                        &binding.source_run_id,
                        &binding.source_checkpoint_id,
                        &binding.expected_candidate_fingerprint,
                        &production.target_ref,
                    )?;
                    let surface = project
                        .database
                        .production_stage_call(&binding.source_run_id, "surface_realization")?
                        .filter(|call| call.state == StageCallState::Confirmed)
                        .and_then(|call| call.result)
                        .ok_or_else(|| {
                            CoreError::AuthorityConflict(
                                "repair source manuscript receipt is unavailable".into(),
                            )
                        })?;
                    let source: SurfaceRealization = strict_model_json(&surface)?;
                    source.validate()?;
                    if sha256_fingerprint(source.manuscript.as_bytes())
                        != binding.expected_candidate_fingerprint
                    {
                        return Err(CoreError::AuthorityConflict(
                            "repair source manuscript bytes changed".into(),
                        ));
                    }
                    let state_json:String=project.database.connection().query_row(
                    "SELECT state_json FROM checkpoints WHERE checkpoint_id=?1 AND run_id=?2",
                    params![binding.source_checkpoint_id,binding.source_run_id],|row|row.get(0)
                ).map_err(storage)?;
                    let diagnosis: Value = serde_json::from_str(&state_json)
                        .map_err(|error| CoreError::Storage(error.to_string()))?;
                    let source_revision = diagnosis
                        .get("revision")
                        .and_then(Value::as_u64)
                        .and_then(|value| u32::try_from(value).ok())
                        .ok_or_else(|| {
                            CoreError::AuthorityConflict(
                                "repair source revision is unavailable".into(),
                            )
                        })?;
                    Some(RepairMaterial {
                        manuscript: source.manuscript,
                        diagnosis,
                        source_revision,
                        source_receipt: binding.expected_candidate_fingerprint.clone(),
                    })
                } else {
                    None
                };
            (production, pack, tracking, repair_material)
        };
        let context_query = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "context_query_plan",
                "context_query_planner",
                json!({
                    "chapter_id":pack.chapter_id,
                    "plan_lock":pack.plan_lock,
                    "recent_settled_context":pack.continuity_context,
                    "instruction":production.intent.instruction,
                    "contract":"Return JSON only: {queries:[string],required_references:[string]}. Produce one to six short semantic evidence queries for facts, character knowledge, relationships, promises or old scenes needed by this exact chapter. Do not answer the queries. required_references may name only exact references visible in the supplied context; otherwise leave it empty."
                }),
                1_500,
                0.1,
            )
            .await?;
        let query_plan: ContextQueryPlan = strict_model_json(&context_query)?;
        query_plan.validate()?;
        let context_candidates = {
            let project = self.open_registered(project_id)?;
            project
                .database
                .writer_context_candidate_pool(&pack.chapter_id, &query_plan)?
        };
        let context_greenlight = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "context_greenlight",
                "context_greenlight_selector",
                json!({
                    "chapter_id":pack.chapter_id,
                    "plan_lock":pack.plan_lock,
                    "query_plan":query_plan,
                    "candidate_pool":context_candidates,
                    "contract":"Return JSON only: {selected_references:[string]}. Select one to twenty-four exact candidate references that materially constrain character choice, causality, continuity, reader promises or this chapter's scene execution. Use only exact references from candidate_pool; do not rank by recency alone and do not rewrite evidence."
                }),
                2_000,
                0.05,
            )
            .await?;
        let context_selection: ContextSelectionProposal = strict_model_json(&context_greenlight)?;
        context_selection.validate_against(&context_candidates)?;
        let mut context_manifest = ContextManifest::default();
        for entry in &context_candidates {
            context_manifest.select(entry.clone())?;
        }
        let writer_context = context_manifest.freeze_selected(
            ContextStage::Writer,
            &context_selection.selected_references,
            24,
            32 * 1024,
        )?;
        let scoped_context_freeze = {
            let mut project = self.open_registered(project_id)?;
            project.database.persist_writer_context_freeze(
                run_id,
                production.task_mode,
                &query_plan,
                &context_candidates,
                &context_selection,
                &writer_context,
                &timestamp(),
            )?
        };
        let corpus_candidates = {
            let project = self.open_registered(project_id)?;
            project.database.active_writer_corpus_candidates()?
        };
        let corpus_greenlight = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "corpus_greenlight",
                "corpus_greenlight_selector",
                json!({
                    "chapter_id":pack.chapter_id,
                    "chapter_plan":pack.plan_lock.chapter_plan(&pack.chapter_id)?,
                    "writer_context":writer_context,
                    "candidate_packs":corpus_candidates,
                    "contract":"Return JSON only: {selected_pack_fingerprints:[string]}. Select zero to four exact active source-free corpus packs whose narrative mechanisms materially help this chapter. Use only exact source_free_pack_fingerprint values from candidate_packs. Select none when no mechanism fits; never select by source identity or phrase similarity."
                }),
                1_500,
                0.05,
            )
            .await?;
        let corpus_selection: WriterCorpusSelection = strict_model_json(&corpus_greenlight)?;
        let selected_corpus = corpus_selection.project(&corpus_candidates)?;
        let preference_candidates = {
            let project = self.open_registered(project_id)?;
            project.database.active_writer_preference_candidates()?
        };
        let preference_greenlight = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "preference_greenlight",
                "preference_greenlight_selector",
                json!({
                    "chapter_id":pack.chapter_id,
                    "chapter_plan":pack.plan_lock.chapter_plan(&pack.chapter_id)?,
                    "current_author_direction":production.intent.instruction,
                    "explicitly_requested_ids":production.intent.selected_preference_ids,
                    "candidate_preferences":preference_candidates,
                    "contract":"Return JSON only: {selected_hypothesis_ids:[string]}. Select zero to twelve exact active preference hypotheses relevant to this chapter. Include every explicitly_requested_id, use only ids from candidate_preferences, and let the current author direction outrank any older preference."
                }),
                1_500,
                0.05,
            )
            .await?;
        let preference_selection: WriterPreferenceSelection =
            strict_model_json(&preference_greenlight)?;
        let selected_preferences = preference_selection.project(
            &preference_candidates,
            &production.intent.selected_preference_ids,
        )?;
        let repair_spec = if let Some(material) = repair_material.as_ref() {
            let result=self.execute_model_stage(project_id,run_id,&service,model,"repair_editor","repair_editor",
                json!({"failed_candidate":{"manuscript":material.manuscript,"fingerprint":material.source_receipt},
                    "diagnosis":material.diagnosis,"instruction":production.intent.instruction,"writer_pack":pack,
                    "contract":"Return JSON only: {repair_owner:'prose_writer',generation_mode:'local_or_bounded_repair'|'fresh_realization',objective_envelope:string,targets:[{location,source_excerpt,fix,preserve:[string]}],invalidation_boundary:[string],comparison_required:true}. For bounded repair, source_excerpt must be an exact, ordered excerpt from the incumbent defining the only editable window. Convert findings into exact FIX + PRESERVE constraints. Choose fresh_realization only when local repair cannot preserve causality."}),
                6_000,0.2).await?;
            let spec: RepairSpec = strict_model_json(&result)?;
            spec.validate_against_source(&material.manuscript)?;
            Some((spec, result))
        } else {
            None
        };
        let character = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "character_simulation",
                "character_simulator",
                json!({"writer_pack":pack,"writer_context":writer_context,"corpus_mechanisms":selected_corpus,"selected_preferences":selected_preferences,"instruction":production.intent.instruction,"author_profile":production.intent.author_profile,
                    "contract":"Return JSON only: {actions:[{scene_id,character,action,motive_pressure,observable_consequence}]}. Propose causal observable actions; do not write manuscript prose or private chain-of-thought."}),
                4_000,
                0.4,
            )
            .await?;
        let character_output: CharacterSimulation = strict_model_json(&character)?;
        character_output.validate_against(&pack.scenes)?;
        let scene_resolution = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "scene_resolution",
                "scene_resolver",
                json!({"scene_briefs":pack.scenes,"character_actions":character_output,"writer_context":writer_context,"corpus_mechanisms":selected_corpus,"selected_preferences":selected_preferences,
                    "contract":"Return JSON only: {scenes:[{scene_id,action_sequence:[string],turn,exit_state}]}. Resolve causal actions into each ordered scene without prose."}),
                4_000,
                0.35,
            )
            .await?;
        let scene_output: SceneResolution = strict_model_json(&scene_resolution)?;
        scene_output.validate_against(&pack.scenes)?;
        let chapter_plan = pack.plan_lock.chapter_plan(&pack.chapter_id)?.clone();
        let mut scene_receipts = BTreeMap::new();
        let mut scene_manuscripts = Vec::with_capacity(pack.scenes.len());
        let mut prior_scene_tail: Option<String> = None;
        for (brief, resolved) in pack.scenes.iter().zip(&scene_output.scenes) {
            let stage_key = format!("surface_scene_{:04}_{}", brief.ordinal, brief.scene_id);
            let scene_result = self
                .execute_model_stage(
                    project_id,
                    run_id,
                    &service,
                    model,
                    &stage_key,
                    "surface_writer",
                    json!({
                        "chapter_id":pack.chapter_id,
                        "plan_lock":pack.plan_lock,
                        "chapter_plan":chapter_plan,
                        "scene_brief":brief,
                        "resolved_scene":resolved,
                        "prior_scene_tail":prior_scene_tail,
                        "continuity_context":pack.continuity_context,
                        "writer_context":writer_context,
                        "corpus_mechanisms":selected_corpus,
                        "selected_preferences":selected_preferences,
                        "reader_grip":production.intent.reader_grip,
                        "author_profile":production.intent.author_profile,
                        "rule_material":production.intent.rule_material,
                        "repair_spec":repair_spec.as_ref().map(|value|&value.0),
                        "repair_source":repair_spec.as_ref().and_then(|value|if value.0.generation_mode==RepairGenerationMode::LocalOrBoundedRepair {
                            repair_material.as_ref().map(|material|json!({"manuscript":material.manuscript,"fingerprint":material.source_receipt}))}else{None}),
                        "instruction":production.intent.instruction,
                        "contract":"Return JSON only: {manuscript:string}. Write only this scene as natural Chinese web-novel prose, without a chapter title or process explanation. Begin from the frozen entry state, preserve causal actions and spatial continuity, realize the required turn, and end exactly in the frozen exit state. The prior_scene_tail is continuity evidence, not text to repeat."
                    }),
                    8_000,
                    0.9,
                )
                .await?;
            let scene_surface: SurfaceRealization = strict_model_json(&scene_result)?;
            scene_surface.validate()?;
            let scene_manuscript = scene_surface.manuscript.trim().to_string();
            let scene_fingerprint = sha256_fingerprint(scene_manuscript.as_bytes());
            {
                let mut project = self.open_registered(project_id)?;
                project.database.record_scene_checkpoint(
                    run_id,
                    &stage_key,
                    &brief.scene_id,
                    &scene_result.fingerprint,
                    &scene_fingerprint,
                    &timestamp(),
                )?;
            }
            prior_scene_tail = Some(last_chars(&scene_manuscript, 1_200));
            scene_receipts.insert(stage_key, scene_result.fingerprint);
            scene_manuscripts.push(scene_manuscript);
        }
        let assembled_manuscript = scene_manuscripts.join("\n\n");
        let surface = self.confirm_derived_surface_stage(
            project_id,
            run_id,
            &scene_receipts,
            &assembled_manuscript,
        )?;
        let surface_output: SurfaceRealization = strict_model_json(&surface)?;
        surface_output.validate()?;
        if let (Some(material), Some((spec, _))) = (repair_material.as_ref(), repair_spec.as_ref())
        {
            spec.verify_bounded_output(&material.manuscript, &surface_output.manuscript)?;
        }
        let candidate_fingerprint = sha256_fingerprint(surface_output.manuscript.as_bytes());

        let reader = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "reader_engagement",
                "blind_reader",
                json!({"manuscript":surface_output.manuscript,"reader_pressure":pack.reader_pressure,
                    "contract":semantic_gate_contract("Judge only lived reader engagement, payoff, emotional continuity and next-chapter pull. Do not inspect rules or other reviews.")}),
                4_000,
                0.25,
            )
            .await?;
        let reader_gate: SemanticGate = strict_model_json(&reader)?;
        reader_gate.validate()?;
        if reader_gate.decision == SemanticGateDecision::Revise {
            return self.failed_gate_projection(
                project_id,
                run_id,
                &candidate_fingerprint,
                "reader_engagement",
                &reader.fingerprint,
            );
        }
        let continuity = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "continuity_rule_audit",
                "continuity_auditor",
                json!({"manuscript":surface_output.manuscript,"tracking_authority":tracking,"writer_context":writer_context,
                    "scene_briefs":pack.scenes,"rule_material":production.intent.rule_material,
                    "contract":semantic_gate_contract("Judge causal/state continuity and exact authoritative rule material. Do not rewrite prose.")}),
                5_000,
                0.2,
            )
            .await?;
        let continuity_gate: SemanticGate = strict_model_json(&continuity)?;
        continuity_gate.validate()?;
        if continuity_gate.decision == SemanticGateDecision::Revise {
            return self.failed_gate_projection(
                project_id,
                run_id,
                &candidate_fingerprint,
                "continuity_rule_audit",
                &continuity.fingerprint,
            );
        }
        let self_audit = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "candidate_self_audit",
                "candidate_qualifier",
                json!({"manuscript":surface_output.manuscript,"writer_pack":pack,"writer_context":writer_context,
                    "instruction":production.intent.instruction,"reader_grip":production.intent.reader_grip,
                    "contract":semantic_gate_contract("Judge objective-by-objective fulfillment, character choice/cost, scene turns, emotion targets and web-novel chapter pull.")}),
                5_000,
                0.25,
            )
            .await?;
        let self_gate: SemanticGate = strict_model_json(&self_audit)?;
        self_gate.validate()?;
        if self_gate.decision == SemanticGateDecision::Revise {
            return self.failed_gate_projection(
                project_id,
                run_id,
                &candidate_fingerprint,
                "candidate_self_audit",
                &self_audit.fingerprint,
            );
        }
        let repair_comparison = if let (Some(material), Some((spec, _))) =
            (repair_material.as_ref(), repair_spec.as_ref())
        {
            let comparison=self.execute_model_stage(project_id,run_id,&service,model,"repair_comparison","repair_comparator",
                json!({"incumbent":{"manuscript":material.manuscript,"fingerprint":material.source_receipt},
                    "challenger":{"manuscript":surface_output.manuscript,"fingerprint":candidate_fingerprint},
                    "repair_spec":spec,"objective_envelope":spec.objective_envelope,
                    "contract":"Return JSON only: {target_outcome:'improved'|'not_fixed'|'regressed'|'inconclusive',objective_preservation:'preserved'|'regressed'|'inconclusive',winner:'challenger'|'incumbent'|'tie',outcome_class:'successful_repair'|'target_not_fixed'|'objective_regression'|'inconclusive',introduced_regressions:[string]}. Compare exact incumbent and challenger; pass only a challenger that fixes the target while preserving the objective."}),
                6_000,0.1).await?;
            let result: RepairComparison = strict_model_json(&comparison)?;
            result.validate()?;
            if !result.passed() {
                return self.failed_gate_projection(
                    project_id,
                    run_id,
                    &candidate_fingerprint,
                    "repair_comparison",
                    &comparison.fingerprint,
                );
            }
            Some(comparison)
        } else {
            None
        };
        let tracking_projection = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "settlement_tracking_projection",
                "tracking_projector",
                json!({
                    "chapter_id":pack.chapter_id,
                    "manuscript":surface_output.manuscript,
                    "prior_continuity":pack.continuity_context,
                    "writer_context":writer_context,
                    "contract":"Return JSON only with net_change, open_expectations, paid_expectations, relationship_changes, state_changes, next_pull, character_snapshot_updates, plus typed entity_deltas, relationship_deltas, knowledge_deltas, timeline_deltas and expectation_deltas. Every typed delta requires a stable id and an exact evidence_excerpt copied from this manuscript. State/fact values must be JSON objects. Extract only observable changes established by this exact manuscript; do not infer authority."
                }),
                5_000,
                0.1,
            )
            .await?;
        let tracking_output: ChapterTrackingProposal = strict_model_json(&tracking_projection)?;
        tracking_output.validate()?;
        let tracking_audit = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "settlement_tracking_audit",
                "tracking_projection_auditor",
                json!({
                    "manuscript":surface_output.manuscript,
                    "tracking_projection":tracking_output,
                    "contract":semantic_gate_contract("Check that every proposed change and expectation is supported by the exact manuscript, omits no material end-state change, and invents no Canon. Do not review prose or rewrite the projection.")
                }),
                4_000,
                0.1,
            )
            .await?;
        let tracking_gate: SemanticGate = strict_model_json(&tracking_audit)?;
        tracking_gate.validate()?;
        if tracking_gate.decision == SemanticGateDecision::Revise {
            return self.failed_gate_projection(
                project_id,
                run_id,
                &candidate_fingerprint,
                "settlement_tracking_audit",
                &tracking_audit.fingerprint,
            );
        }
        {
            let mut project = self.open_registered(project_id)?;
            project.database.append_runtime_event(
                run_id,
                "production_candidate_qualified",
                &json!({"candidate_fingerprint":candidate_fingerprint}),
                &timestamp(),
            )?;
            project.database.set_run_status(
                run_id,
                "awaiting_external",
                Some(&candidate_fingerprint),
                &timestamp(),
            )?;
            project.database.append_runtime_event(
                run_id,
                "production_independent_requested",
                &json!({"candidate_fingerprint":candidate_fingerprint,"independent_context":true}),
                &timestamp(),
            )?;
        }
        let independent = self
            .execute_model_stage(
                project_id,
                run_id,
                &service,
                model,
                "independent_semantic_gate",
                "independent_reviewer",
                json!({"manuscript":surface_output.manuscript,"reader_contract":pack.reader_pressure,
                    "scene_briefs":pack.scenes,"instruction":production.intent.instruction,
                    "contract":semantic_gate_contract("Independently judge release readiness from this exact candidate and objectives. You have no other reviewer outputs. Reject any material causal, character, continuity, prose or reader-payoff defect.")}),
                6_000,
                0.15,
            )
            .await?;
        let independent_gate: SemanticGate = strict_model_json(&independent)?;
        independent_gate.validate()?;
        if independent_gate.decision == SemanticGateDecision::Revise {
            return self.failed_gate_projection(
                project_id,
                run_id,
                &candidate_fingerprint,
                "independent_semantic_gate",
                &independent.fingerprint,
            );
        }
        let report = ReviewReport::create(ReviewReportInput {
            candidate_fingerprint: candidate_fingerprint.clone(),
            mode: ReviewMode::Solo,
            reviewer_sessions: BTreeSet::from([format!("call:{}", independent.request_id)]),
            independent_context: true,
            deterministic_prechecks: vec![
                "candidate_bytes_frozen".into(),
                "writer_pack_bound".into(),
                "stage_receipts_bound".into(),
            ],
            findings: independent_gate.review_findings("independent_reviewer"),
            disagreements: vec![],
            infrastructure_failed: false,
        })?;
        let user_visible_receipt = sha256_fingerprint(
            serde_json::to_vec(&json!({
                "candidate_fingerprint":candidate_fingerprint,"review_report_fingerprint":report.fingerprint,
                "reader":reader.fingerprint,"continuity":continuity.fingerprint,
                "self_audit":self_audit.fingerprint,"independent":independent.fingerprint,
                "repair_editor":repair_spec.as_ref().map(|value|&value.1.fingerprint),
                "repair_comparison":repair_comparison.as_ref().map(|value|&value.fingerprint),
                "repair_source":repair_material.as_ref().map(|value|&value.source_receipt),
                "context_query_plan":context_query.fingerprint,
                "context_greenlight":context_greenlight.fingerprint,
                "context_freeze":scoped_context_freeze,
                "corpus_greenlight":corpus_greenlight.fingerprint,
                "preference_greenlight":preference_greenlight.fingerprint,
                "surface_scenes":scene_receipts,
                "settlement_tracking_projection":tracking_projection.fingerprint,
                "settlement_tracking_audit":tracking_audit.fingerprint
            }))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let mut stage_receipts = BTreeMap::from([
            (
                "context_query_plan".into(),
                context_query.fingerprint.clone(),
            ),
            (
                "context_greenlight".into(),
                context_greenlight.fingerprint.clone(),
            ),
            ("context_freeze".into(), scoped_context_freeze),
            (
                "corpus_greenlight".into(),
                corpus_greenlight.fingerprint.clone(),
            ),
            (
                "preference_greenlight".into(),
                preference_greenlight.fingerprint.clone(),
            ),
            ("character_simulation".into(), character.fingerprint.clone()),
            (
                "scene_resolution".into(),
                scene_resolution.fingerprint.clone(),
            ),
            ("surface_realization".into(), surface.fingerprint.clone()),
            ("reader_engagement".into(), reader.fingerprint.clone()),
            ("continuity".into(), continuity.fingerprint.clone()),
            (
                "candidate_self_audit".into(),
                self_audit.fingerprint.clone(),
            ),
            (
                "independent_semantic_gate".into(),
                independent.fingerprint.clone(),
            ),
            (
                "settlement_tracking_projection".into(),
                tracking_projection.fingerprint.clone(),
            ),
            (
                "settlement_tracking_audit".into(),
                tracking_audit.fingerprint.clone(),
            ),
            ("user_visible_gate".into(), user_visible_receipt),
        ]);
        stage_receipts.extend(scene_receipts);
        if let Some((_, receipt)) = &repair_spec {
            stage_receipts.insert("repair_editor".into(), receipt.fingerprint.clone());
        }
        if let Some(receipt) = &repair_comparison {
            stage_receipts.insert("repair_comparison".into(), receipt.fingerprint.clone());
        }
        if let Some(material) = &repair_material {
            stage_receipts.insert("repair_source".into(), material.source_receipt.clone());
        }
        let candidate_id = format!("candidate-{}", uuid::Uuid::new_v4());
        let candidate = match production.task_mode {
            ProductionTaskMode::Draft => {
                CandidateArtifact::draft(&candidate_id, &pack, &surface_output.manuscript)?
            }
            ProductionTaskMode::Revise => CandidateArtifact::revision(
                &candidate_id,
                &pack,
                production
                    .intent
                    .repair_source
                    .as_ref()
                    .ok_or_else(|| CoreError::AuthorityConflict("repair source is missing".into()))?
                    .expected_candidate_fingerprint
                    .clone(),
                repair_material
                    .as_ref()
                    .ok_or_else(|| {
                        CoreError::AuthorityConflict("repair material is missing".into())
                    })?
                    .source_revision
                    .checked_add(1)
                    .ok_or_else(|| {
                        CoreError::AuthorityConflict("repair revision overflowed".into())
                    })?,
                &surface_output.manuscript,
            )?,
        };
        let release = ProductionRelease::create_for_mode(
            &candidate.candidate_id,
            &candidate.fingerprint,
            production.task_mode,
            &pack.fingerprint,
            &pack.tracking_fingerprint,
            &report.fingerprint,
            stage_receipts,
            timestamp(),
        )?;
        let (revision_id, release_id) = {
            let mut project = self.open_registered(project_id)?;
            project.database.set_run_status(
                run_id,
                "awaiting_release",
                Some(&candidate.fingerprint),
                &timestamp(),
            )?;
            project.database.commit_released_candidate(
                run_id,
                &production.target_ref,
                production.task_mode,
                &candidate,
                &report,
                &release,
                &timestamp(),
            )?
        };
        Ok(json!({
            "schema":"quillframe_production_execution_v1","project_id":project_id,"run_id":run_id,
            "status":"review","candidate_visible":true,"raw_draft_visible":false,
            "candidate_id":candidate.candidate_id,"candidate_fingerprint":candidate.fingerprint,
            "revision_id":revision_id,"production_release_id":release_id,"authority":false
        }))
    }

    #[allow(clippy::too_many_arguments)]
    async fn execute_model_stage(
        &self,
        project_id: &str,
        run_id: &str,
        service: &ModelServiceRecord,
        model: &str,
        stage_key: &str,
        runtime_role: &str,
        input: Value,
        max_output_tokens: u32,
        temperature: f32,
    ) -> CoreResult<ModelResult> {
        let assembly = PromptAssembly::build(stage_key, semantic_system(stage_key), input)?;
        let input_fingerprint = assembly.fingerprint.clone();
        if let Some(call) = {
            let project = self.open_registered(project_id)?;
            project.database.production_stage_call(run_id, stage_key)?
        } {
            if call.job.input_fingerprint != input_fingerprint {
                return Err(CoreError::AuthorityConflict(format!(
                    "stage {stage_key} input changed after dispatch"
                )));
            }
            return match (call.state, call.result) {
                (StageCallState::Confirmed, Some(result)) => Ok(result),
                (StageCallState::Dispatched | StageCallState::Unconfirmed, _) => {
                    Err(CoreError::ModelRuntime(
                        "unconfirmed_model_outcome: stage will not be sent twice".into(),
                    ))
                }
                _ => Err(CoreError::AuthorityConflict(format!(
                    "stage {stage_key} is not executable"
                ))),
            };
        }
        let request_id = format!("model-{}-{}", stage_key, &input_fingerprint[7..23]);
        let model_request = ModelRequest {
            request_id,
            model: model.into(),
            system: assembly.system_text(),
            user: assembly.user_text()?,
            temperature: Some(temperature),
            max_output_tokens: Some(max_output_tokens),
            absolute_deadline_ms: 120_000,
        };
        let job = StageJob::freeze(
            stage_key,
            runtime_role,
            model_request.clone(),
            input_fingerprint,
        )?;
        let call_id = {
            let mut project = self.open_registered(project_id)?;
            project.database.dispatch_stage(
                run_id,
                &job,
                &format!("executor-{}", uuid::Uuid::new_v4()),
                unix_millis().saturating_add(120_000),
                &timestamp(),
            )?
        };
        let result = ModelRuntime::new(self.secret_store()?)
            .execute(&service.endpoint, &model_request)
            .await;
        match result {
            Ok(result) => {
                let mut project = self.open_registered(project_id)?;
                project
                    .database
                    .confirm_stage(&call_id, &result, &timestamp())?;
                project.database.append_runtime_event(
                    run_id,
                    "production_stage_confirmed",
                    &json!({"stage_key":stage_key,"result_fingerprint":result.fingerprint}),
                    &timestamp(),
                )?;
                Ok(result)
            }
            Err(error) => {
                let mut project = self.open_registered(project_id)?;
                project.database.mark_stage_unconfirmed(
                    &call_id,
                    "model_transport_unconfirmed",
                    &timestamp(),
                )?;
                project.database.append_runtime_event(
                    run_id,
                    "production_stage_unconfirmed",
                    &json!({"stage_key":stage_key,"error_code":"model_transport_unconfirmed"}),
                    &timestamp(),
                )?;
                Err(error)
            }
        }
    }

    fn confirm_derived_surface_stage(
        &self,
        project_id: &str,
        run_id: &str,
        scene_receipts: &BTreeMap<String, String>,
        manuscript: &str,
    ) -> CoreResult<ModelResult> {
        if scene_receipts.is_empty() || manuscript.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "surface assembly requires confirmed scene artifacts".into(),
            ));
        }
        let assembly_manifest = json!({
            "schema":"quillframe_surface_assembly_v1",
            "separator":"\\n\\n",
            "scene_receipts":scene_receipts,
            "manuscript_fingerprint":sha256_fingerprint(manuscript.as_bytes())
        });
        let input_fingerprint = sha256_fingerprint(
            serde_json::to_vec(&assembly_manifest)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let request_id = format!("derived-surface-{}", &input_fingerprint[7..23]);
        let model_request = ModelRequest {
            request_id: request_id.clone(),
            model: "scene-assembler-v1".into(),
            system: "Quillframe deterministic ordered scene assembler".into(),
            user: serde_json::to_string(&assembly_manifest)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
            temperature: Some(0.0),
            max_output_tokens: None,
            absolute_deadline_ms: 1,
        };
        let job = StageJob::freeze(
            "surface_realization",
            "deterministic_scene_assembler",
            model_request,
            input_fingerprint,
        )?;
        let result = ModelResult::record(
            request_id,
            "quillframe-deterministic",
            "scene-assembler-v1",
            serde_json::to_string(&SurfaceRealization {
                manuscript: manuscript.into(),
            })
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
            None,
            ModelUsage {
                input_tokens: Some(0),
                output_tokens: Some(0),
                total_tokens: Some(0),
                cost_micros: Some(0),
            },
        )?;
        let artifact_fingerprint = sha256_fingerprint(manuscript.as_bytes());
        let mut project = self.open_registered(project_id)?;
        project.database.confirm_derived_stage(
            run_id,
            &job,
            &result,
            "chapter_surface_assembled",
            &assembly_manifest,
            &artifact_fingerprint,
            &timestamp(),
        )?;
        Ok(result)
    }

    fn failed_gate_projection(
        &self,
        project_id: &str,
        run_id: &str,
        candidate_fingerprint: &str,
        mechanism: &str,
        stage_result_fingerprint: &str,
    ) -> CoreResult<Value> {
        let checkpoint_id = {
            let mut project = self.open_registered(project_id)?;
            project.database.record_failed_gate(
                run_id,
                candidate_fingerprint,
                mechanism,
                stage_result_fingerprint,
                &timestamp(),
            )?
        };
        Ok(json!({
            "schema":"quillframe_production_execution_v1","project_id":project_id,"run_id":run_id,
            "status":"failed_gate","candidate_visible":false,"raw_draft_visible":false,
            "repair_source":{"source_run_id":run_id,"source_checkpoint_id":checkpoint_id,
                "expected_candidate_fingerprint":candidate_fingerprint},"authority":false
        }))
    }

    fn document_create(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let mut project = self.open_registered(string_arg(request, "project_id")?)?;
        let document_id = string_arg(request, "document_id")?;
        let title = string_arg(request, "title")?;
        let kind = request
            .args
            .get("document_kind")
            .and_then(Value::as_str)
            .unwrap_or("manuscript");
        if !matches!(
            kind,
            "manuscript" | "note" | "plan" | "research_note" | "publication_source"
        ) {
            return Err(CoreError::InvalidProject(
                "document kind is not supported".into(),
            ));
        }
        let story_node_id = request.args.get("story_node_id").and_then(Value::as_str);
        if kind == "manuscript" && story_node_id.is_none() {
            return Err(CoreError::InvalidProject(
                "manuscript requires a chapter story_node_id".into(),
            ));
        }
        let transaction = project
            .database
            .connection_mut()
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        if let Some(node_id) = story_node_id {
            let node_kind = transaction
                .query_row(
                    "SELECT kind FROM story_nodes WHERE node_id=?1",
                    [node_id],
                    |row| row.get::<_, String>(0),
                )
                .optional()
                .map_err(storage)?;
            if node_kind.as_deref() != Some("chapter") && kind == "manuscript" {
                return Err(CoreError::InvalidHierarchy(
                    "manuscript must belong to an existing chapter".into(),
                ));
            }
        }
        transaction.execute(
            "INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?1,?2,?3,?4,?5)",
            params![document_id, story_node_id, kind, title, timestamp()],
        ).map_err(storage)?;
        transaction.commit().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_document_create_result_v1","created":true,"document_id":document_id,"authority":false}),
        )
    }

    fn document_list(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project = self.open_registered(string_arg(request, "project_id")?)?;
        let kind = request.args.get("document_kind").and_then(Value::as_str);
        let limit = request
            .args
            .get("limit")
            .and_then(Value::as_u64)
            .unwrap_or(500)
            .clamp(1, 500);
        let mut statement = project.database.connection().prepare(
            "SELECT d.document_id,d.story_node_id,d.document_kind,d.title,d.created_at, \
             r.revision_id,r.content_fingerprint,r.authority_class,r.created_at \
             FROM documents d LEFT JOIN document_revisions r ON r.revision_id=( \
             SELECT revision_id FROM document_revisions WHERE document_id=d.document_id \
             AND (source<>'production_candidate' OR authority_class='accepted') ORDER BY created_at DESC,revision_id DESC LIMIT 1) \
             WHERE (?1 IS NULL OR d.document_kind=?1) ORDER BY d.created_at,d.document_id LIMIT ?2"
        ).map_err(storage)?;
        let items = statement.query_map(params![kind, limit], |row| Ok(json!({
            "document_id":row.get::<_,String>(0)?,"story_node_id":row.get::<_,Option<String>>(1)?,
            "document_kind":row.get::<_,String>(2)?,"title":row.get::<_,String>(3)?,"created_at":row.get::<_,String>(4)?,
            "latest_revision_id":row.get::<_,Option<String>>(5)?,"latest_content_fingerprint":row.get::<_,Option<String>>(6)?,
            "latest_authority_class":row.get::<_,Option<String>>(7)?,"latest_revision_created_at":row.get::<_,Option<String>>(8)?
        }))).map_err(storage)?.collect::<Result<Vec<_>,_>>().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_document_list_projection_v1","project_id":string_arg(request,"project_id")?,"document_kind":kind,"items":items,"authority":false,"canon_authority":false}),
        )
    }

    fn document_open(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project = self.open_registered(string_arg(request, "project_id")?)?;
        let document_id = string_arg(request, "document_id")?;
        let document = project.database.connection().query_row(
            "SELECT document_id,story_node_id,document_kind,title,created_at FROM documents WHERE document_id=?1",
            [document_id], |row| Ok(json!({"document_id":row.get::<_,String>(0)?,"story_node_id":row.get::<_,Option<String>>(1)?,"document_kind":row.get::<_,String>(2)?,"title":row.get::<_,String>(3)?,"created_at":row.get::<_,String>(4)?}))
        ).map_err(storage)?;
        let latest = project.database.connection().query_row(
            "SELECT revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json \
             FROM document_revisions WHERE document_id=?1 AND authority_class IN ('proposal','review','accepted') \
             AND (source<>'production_candidate' OR authority_class='accepted') ORDER BY created_at DESC,revision_id DESC LIMIT 1",
            [document_id], |row| {
                let provenance: String = row.get(8)?;
                Ok(json!({"revision_id":row.get::<_,String>(0)?,"document_id":row.get::<_,String>(1)?,"parent_revision_id":row.get::<_,Option<String>>(2)?,"content":row.get::<_,String>(3)?,"content_fingerprint":row.get::<_,String>(4)?,"created_at":row.get::<_,String>(5)?,"source":row.get::<_,String>(6)?,"authority_class":row.get::<_,String>(7)?,"provenance":serde_json::from_str::<Value>(&provenance).unwrap_or_else(|_|json!({}))}))
            }
        ).optional().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_document_projection_v1","project_id":string_arg(request,"project_id")?,"document":document,"latest_revision":latest,"authority":false}),
        )
    }

    fn document_revisions(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project = self.open_registered(string_arg(request, "project_id")?)?;
        let document_id = string_arg(request, "document_id")?;
        let limit = request
            .args
            .get("limit")
            .and_then(Value::as_u64)
            .unwrap_or(100)
            .clamp(1, 500);
        let mut statement = project.database.connection().prepare(
            "SELECT revision_id,document_id,parent_revision_id,content_fingerprint,created_at,source,authority_class,provenance_json \
             FROM document_revisions WHERE document_id=?1 ORDER BY created_at DESC,revision_id DESC LIMIT ?2"
        ).map_err(storage)?;
        let items = statement.query_map(params![document_id,limit], |row| {
            let provenance: String = row.get(7)?;
            Ok(json!({"revision_id":row.get::<_,String>(0)?,"document_id":row.get::<_,String>(1)?,"parent_revision_id":row.get::<_,Option<String>>(2)?,"content_fingerprint":row.get::<_,String>(3)?,"created_at":row.get::<_,String>(4)?,"source":row.get::<_,String>(5)?,"authority_class":row.get::<_,String>(6)?,"provenance":serde_json::from_str::<Value>(&provenance).unwrap_or_else(|_|json!({}))}))
        }).map_err(storage)?.collect::<Result<Vec<_>,_>>().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_document_revision_list_v1","project_id":string_arg(request,"project_id")?,"document_id":document_id,"items":items,"authority":false}),
        )
    }

    fn document_revision_save(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let mut project = self.open_registered(string_arg(request, "project_id")?)?;
        let document_id = string_arg(request, "document_id")?;
        let content = request
            .args
            .get("content")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidProject("content must be a string".into()))?;
        let source = string_arg(request, "source")?;
        if source == "production_runtime" {
            return Err(CoreError::AuthorityConflict(
                "production revisions must use the production pipeline".into(),
            ));
        }
        let authority = request
            .args
            .get("authority_class")
            .and_then(Value::as_str)
            .unwrap_or("proposal");
        if !matches!(authority, "proposal" | "review") {
            return Err(CoreError::AuthorityConflict(
                "manual revision authority must be proposal or review".into(),
            ));
        }
        let expected_parent = request
            .args
            .get("expected_parent_revision_id")
            .and_then(Value::as_str);
        let provenance = request
            .args
            .get("provenance")
            .filter(|value| value.is_object())
            .cloned()
            .unwrap_or_else(|| json!({}));
        let content_fingerprint = sha256_fingerprint(content.as_bytes());
        let transaction = project
            .database
            .connection_mut()
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        if let Some(existing) = transaction.query_row("SELECT revision_id FROM document_revisions WHERE document_id=?1 AND content_fingerprint=?2",params![document_id,content_fingerprint],|row|row.get::<_,String>(0)).optional().map_err(storage)? {
            return Ok(json!({"revision_id":existing,"content_fingerprint":content_fingerprint,"deduplicated":true}));
        }
        let current = transaction.query_row("SELECT revision_id FROM document_revisions WHERE document_id=?1 AND (source<>'production_candidate' OR authority_class='accepted') ORDER BY created_at DESC,revision_id DESC LIMIT 1",[document_id],|row|row.get::<_,String>(0)).optional().map_err(storage)?;
        if current.as_deref() != expected_parent {
            return Err(CoreError::AuthorityConflict("document head changed".into()));
        }
        let revision_id = format!("REV-{}", uuid::Uuid::new_v4());
        transaction.execute("INSERT INTO document_revisions(revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)",params![revision_id,document_id,current,content,content_fingerprint,timestamp(),source,authority,provenance.to_string()]).map_err(storage)?;
        transaction.commit().map_err(storage)?;
        Ok(
            json!({"revision_id":revision_id,"content_fingerprint":content_fingerprint,"deduplicated":false}),
        )
    }

    fn candidate_list(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let project = self.open_registered(project_id)?;
        let limit = request
            .args
            .get("limit")
            .and_then(Value::as_u64)
            .unwrap_or(100)
            .clamp(1, 500);
        let mut statement = project.database.connection().prepare(
            "SELECT c.candidate_id,c.document_id,c.revision_id,c.run_id,c.task_mode,c.candidate_kind,c.status, \
             c.content_fingerprint,c.user_visible_gate,c.created_at \
             FROM candidates c JOIN production_releases p ON p.candidate_id=c.candidate_id AND p.user_visible=1 \
             ORDER BY c.created_at DESC,c.candidate_id DESC LIMIT ?1"
        ).map_err(storage)?;
        let items = statement.query_map([limit], |row| Ok(json!({
            "candidate_id":row.get::<_,String>(0)?,"document_id":row.get::<_,Option<String>>(1)?,
            "revision_id":row.get::<_,Option<String>>(2)?,"run_id":row.get::<_,Option<String>>(3)?,
            "task_mode":row.get::<_,String>(4)?,"candidate_kind":row.get::<_,String>(5)?,
            "status":row.get::<_,String>(6)?,"content_fingerprint":row.get::<_,String>(7)?,
            "candidate_fingerprint":row.get::<_,String>(7)?,"user_visible_gate":row.get::<_,String>(8)?,
            "created_at":row.get::<_,String>(9)?
        }))).map_err(storage)?.collect::<Result<Vec<_>,_>>().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_inspector_candidate_list_v1","project_id":project_id,
            "items":items,"limit":limit,"authority":false}),
        )
    }

    fn candidate_review_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let candidate_id = string_arg(request, "candidate_id")?;
        let project = self.open_registered(project_id)?;
        let (candidate, revision_id, parent_revision_id, run_id, candidate_fingerprint, persisted_status) = project.database.connection().query_row(
            "SELECT c.document_id,c.revision_id,c.run_id,c.task_mode,c.candidate_kind,c.status,c.content_fingerprint,c.user_visible_gate,c.created_at, \
             r.parent_revision_id FROM candidates c JOIN document_revisions r ON r.revision_id=c.revision_id \
             JOIN production_releases p ON p.candidate_id=c.candidate_id AND p.user_visible=1 WHERE c.candidate_id=?1",
            [candidate_id],|row|{
                let status:String=row.get(5)?;
                let fingerprint:String=row.get(6)?;
                let document_id:Option<String>=row.get(0)?;
                let revision_id:Option<String>=row.get(1)?;
                let run_id:Option<String>=row.get(2)?;
                Ok((json!({"candidate_id":candidate_id,"document_id":document_id,"revision_id":revision_id,"run_id":run_id,
                    "task_mode":row.get::<_,String>(3)?,"candidate_kind":row.get::<_,String>(4)?,"status":status,
                    "persisted_status":status,"effective_status":status,"content_fingerprint":fingerprint,
                    "candidate_fingerprint":fingerprint,"user_visible_gate":row.get::<_,String>(7)?,"created_at":row.get::<_,String>(8)?}),
                    revision_id,row.get::<_,Option<String>>(9)?,run_id,fingerprint,status))
            }
        ).map_err(storage)?;
        let revision_id = revision_id
            .ok_or_else(|| CoreError::AuthorityConflict("candidate revision is missing".into()))?;
        let run_id = run_id
            .ok_or_else(|| CoreError::AuthorityConflict("candidate run is missing".into()))?;
        let candidate_revision = project.database.connection().query_row(
            "SELECT revision_id,document_id,parent_revision_id,content_fingerprint,created_at,source,authority_class,provenance_json \
             FROM document_revisions WHERE revision_id=?1",
            [&revision_id],|row|{let provenance:String=row.get(7)?;Ok(json!({"revision_id":row.get::<_,String>(0)?,
                "document_id":row.get::<_,String>(1)?,"parent_revision_id":row.get::<_,Option<String>>(2)?,"content":"",
                "content_fingerprint":row.get::<_,String>(3)?,"created_at":row.get::<_,String>(4)?,"source":row.get::<_,String>(5)?,
                "authority_class":row.get::<_,String>(6)?,"provenance":serde_json::from_str::<Value>(&provenance).unwrap_or_else(|_|json!({}))}))}
        ).map_err(storage)?;
        let incumbent_revision = parent_revision_id.map(|parent|project.database.connection().query_row(
            "SELECT revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json FROM document_revisions WHERE revision_id=?1",
            [parent],|row|{let provenance:String=row.get(8)?;Ok(json!({"revision_id":row.get::<_,String>(0)?,"document_id":row.get::<_,String>(1)?,
                "parent_revision_id":row.get::<_,Option<String>>(2)?,"content":row.get::<_,String>(3)?,"content_fingerprint":row.get::<_,String>(4)?,
                "created_at":row.get::<_,String>(5)?,"source":row.get::<_,String>(6)?,"authority_class":row.get::<_,String>(7)?,
                "provenance":serde_json::from_str::<Value>(&provenance).unwrap_or_else(|_|json!({}))}))}
        ).map_err(storage)).transpose()?;
        let calls = project.database.production_stage_calls(&run_id)?;
        let receipt = |stage: &str| {
            calls.iter().find(|call| call.job.stage_key==stage).and_then(|call|call.result.as_ref())
            .map(|result|json!({"stage_key":stage,"result_fingerprint":result.fingerprint,
                "judgment":{"artifact_fingerprint":candidate_fingerprint,"status":"PASS","evidence_refs":[]}}))
            .unwrap_or_else(||json!({"stage_key":stage,"status":"missing"}))
        };
        let release_json:String=project.database.connection().query_row(
            "SELECT payload_json FROM production_releases WHERE candidate_id=?1 AND candidate_fingerprint=?2 AND user_visible=1",
            params![candidate_id,candidate_fingerprint],|row|row.get(0)).map_err(storage)?;
        let mut readiness: Value = serde_json::from_str(&release_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        readiness
            .as_object_mut()
            .unwrap()
            .insert("ready_for_user_visible_review".into(), Value::Bool(true));
        Ok(
            json!({"schema":"quillframe_candidate_review_projection_v1","project_id":project_id,
            "candidate":candidate,"candidate_revision":candidate_revision,"incumbent_revision":incumbent_revision,"diff":null,
            "evidence":{"reader":receipt("reader_engagement"),"character":receipt("character_simulation"),
                "continuity":receipt("continuity_rule_audit"),"independent":receipt("independent_semantic_gate"),
                "production_readiness":readiness,"user_visible_gate":{"status":"PASS"}},
            "revision_request":null,"persisted_status":persisted_status,"private_reasoning_exposed":false,
            "authority":false,"canon_authority":false,"settlement_authority":false}),
        )
    }

    fn candidate_visible_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let candidate_id = string_arg(request, "candidate_id")?;
        let project = self.open_registered(project_id)?;
        let (document_id,revision_id,content,content_fingerprint,authority_class,status,release_json):(String,String,String,String,String,String,String)=project.database.connection().query_row(
            "SELECT c.document_id,c.revision_id,r.content,r.content_fingerprint,r.authority_class,c.status,p.payload_json \
             FROM candidates c JOIN document_revisions r ON r.revision_id=c.revision_id \
             JOIN production_releases p ON p.candidate_id=c.candidate_id AND p.candidate_fingerprint=c.content_fingerprint AND p.user_visible=1 \
             WHERE c.candidate_id=?1",
            [candidate_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?,row.get(5)?,row.get(6)?))
        ).map_err(storage)?;
        if sha256_fingerprint(content.as_bytes()) != content_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "released candidate bytes changed".into(),
            ));
        }
        let release: ProductionRelease = serde_json::from_str(&release_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        release.validate()?;
        if release.candidate_id != candidate_id
            || release.candidate_fingerprint != content_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "production release binding changed".into(),
            ));
        }
        let mut release_projection = serde_json::to_value(&release)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        release_projection
            .as_object_mut()
            .unwrap()
            .insert("ready_for_user_visible_review".into(), Value::Bool(true));
        Ok(
            json!({"schema":"quillframe_user_visible_candidate_v1","project_id":project_id,
            "candidate_id":candidate_id,"candidate_fingerprint":content_fingerprint,"document_id":document_id,
            "revision_id":revision_id,"content":content,"authority_class":authority_class,"production_release":release_projection,
            "content_access":"production_release_only","accepted":status=="accepted","settled":false,
            "private_reasoning_exposed":false,"authority":false,"canon_authority":false}),
        )
    }

    fn candidate_accept(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let candidate_id = string_arg(request, "candidate_id")?;
        let candidate_fingerprint = string_arg(request, "candidate_fingerprint")?;
        let authorized_by = string_arg(request, "authorized_by")?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let authorization = object_arg(request, "authorization")?;
        let mut project = self.open_registered(project_id)?;
        let review_report_fingerprint = project
            .database
            .connection()
            .query_row(
                "SELECT report_fingerprint FROM structured_review_reports \
             WHERE candidate_fingerprint=?1 AND decision='accept' AND independent_context=1 \
             ORDER BY created_at DESC,report_fingerprint DESC LIMIT 1",
                [candidate_fingerprint],
                |row| row.get::<_, String>(0),
            )
            .map_err(storage)?;
        let decision = AcceptanceDecision::create(
            candidate_id,
            candidate_fingerprint,
            review_report_fingerprint,
            authorized_by,
            idempotency_key,
            timestamp(),
        )?;
        let acceptance_id = project.database.accept_candidate(&decision)?;
        Ok(json!({
            "schema":"quillframe_candidate_acceptance_result_v1","acceptance_id":acceptance_id,
            "candidate_id":candidate_id,"candidate_fingerprint":candidate_fingerprint,
            "authorized_by":authorized_by,"authorization":authorization,"accepted":true,
            "settled":false,"canon_mutated":false,"request_fingerprint":request_args_fingerprint(request)
        }))
    }

    fn candidate_revision_request(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let candidate_id = string_arg(request, "candidate_id")?;
        let candidate_fingerprint = string_arg(request, "candidate_fingerprint")?;
        let authorized_by = string_arg(request, "authorized_by")?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let revision_request = object_arg(request, "revision_request")?;
        let instruction = revision_request
            .get("instruction")
            .and_then(Value::as_str)
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| {
                CoreError::AuthorityConflict("revision instruction is required".into())
            })?;
        let authorization = object_arg(request, "authorization")?;
        let mut project = self.open_registered(project_id)?;
        let document_id = project.database.connection().query_row(
            "SELECT document_id FROM candidates WHERE candidate_id=?1 AND content_fingerprint=?2",
            params![candidate_id,candidate_fingerprint], |row| row.get::<_,String>(0)
        ).map_err(storage)?;
        let typed = RevisionRequest::create(
            candidate_id,
            candidate_fingerprint,
            authorized_by,
            instruction,
            idempotency_key,
            timestamp(),
        )?;
        let (revision_request_id, source_checkpoint_id) =
            project.database.request_candidate_revision(&typed)?;
        let source_run_id: String = project
            .database
            .connection()
            .query_row(
                "SELECT run_id FROM candidates WHERE candidate_id=?1",
                [candidate_id],
                |row| row.get(0),
            )
            .map_err(storage)?;
        Ok(json!({
            "schema":"quillframe_candidate_revision_request_result_v1","revision_request_id":revision_request_id,
            "candidate_id":candidate_id,"candidate_fingerprint":candidate_fingerprint,"persisted_candidate_status":"review_draft",
            "effective_status":"revision_requested","revision_request":revision_request,"authorized_by":authorized_by,
            "authorization":authorization,"next_action":{"operation":"author.run.start","task_mode":"REVISE","target_ref":document_id,
            "requires_explicit_user_action":true,"auto_started":false,"source_candidate_id":candidate_id,
            "source_candidate_fingerprint":candidate_fingerprint,"payload":{"document_id":document_id,
            "instruction":instruction,"repair_source":{"source_run_id":source_run_id,
            "source_checkpoint_id":source_checkpoint_id,"expected_candidate_fingerprint":candidate_fingerprint}}},
            "canon_mutated":false,"settled":false,"authority":false,"request_fingerprint":request_args_fingerprint(request)
        }))
    }

    fn settlement_preflight(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let acceptance_id = string_arg(request, "acceptance_id")?;
        let target_ref = string_arg(request, "target_ref")?;
        let project = self.open_registered(project_id)?;
        let preflight =
            project
                .database
                .settlement_preflight(acceptance_id, target_ref, &timestamp())?;
        let (document_id,chapter_id,run_id) = project.database.connection().query_row(
            "SELECT c.document_id,d.story_node_id,c.run_id FROM candidates c JOIN documents d ON d.document_id=c.document_id WHERE c.candidate_id=?1",
            [&preflight.candidate_id], |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?))
        ).map_err(storage)?;
        if target_ref != format!("chapter:{chapter_id}") {
            return Err(CoreError::AuthorityConflict(
                "settlement target does not match the candidate chapter".into(),
            ));
        }
        let tracking_result_json: String = project.database.connection().query_row(
            "SELECT result_json FROM production_stage_calls WHERE run_id=?1 AND stage_key='settlement_tracking_projection' AND state='confirmed'",
            [&run_id],|row|row.get(0)
        ).map_err(storage)?;
        let tracking_result: ModelResult = serde_json::from_str(&tracking_result_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        tracking_result.validate()?;
        let narrative_proposal: ChapterTrackingProposal = strict_model_json(&tracking_result)?;
        narrative_proposal.validate()?;
        Ok(json!({
            "schema":"quillframe_settlement_preflight_v1","project_id":project_id,"acceptance_id":acceptance_id,
            "candidate_id":preflight.candidate_id,"candidate_fingerprint":preflight.candidate_fingerprint,
            "document_id":document_id,"revision_id":preflight.revision_id,"chapter_id":chapter_id,"target_ref":target_ref,
            "expected_before_fingerprint":preflight.before_fingerprint,"current_before_fingerprint":preflight.before_fingerprint,
            "narrative_proposal":narrative_proposal,"reader_observations":[],"settleable":true,"mutation_performed":false,
            "canon_mutated":false,"authority":false,"preflight_fingerprint":preflight.fingerprint
        }))
    }

    fn settlement_apply(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let acceptance_id = string_arg(request, "acceptance_id")?;
        let target_ref = string_arg(request, "target_ref")?;
        let expected_before = string_arg(request, "expected_before_fingerprint")?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let mut project = self.open_registered(project_id)?;
        let preflight =
            project
                .database
                .settlement_preflight(acceptance_id, target_ref, &timestamp())?;
        if preflight.before_fingerprint != expected_before {
            return Ok(
                json!({"schema":"quillframe_settlement_result_v1","settlement_id":null,"status":"settlement_incomplete",
                "target_ref":target_ref,"expected_before_fingerprint":expected_before,"actual_before_fingerprint":preflight.before_fingerprint,
                "canon_mutated":false,"request_fingerprint":request_args_fingerprint(request)}),
            );
        }
        if let Some(expected_preflight) = request
            .args
            .get("expected_preflight_fingerprint")
            .and_then(Value::as_str)
        {
            if expected_preflight != preflight.fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "settlement preflight changed".into(),
                ));
            }
        }
        let authorization = SettlementAuthorization::create(
            &preflight,
            "author:local",
            idempotency_key,
            timestamp(),
        )?;
        let settlement_id = project.database.apply_settlement(&authorization)?;
        let after_fingerprint: String = project
            .database
            .connection()
            .query_row(
                "SELECT after_fingerprint FROM settlements WHERE settlement_id=?1",
                [&settlement_id],
                |row| row.get(0),
            )
            .map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_settlement_result_v1","settlement_id":settlement_id,"status":"settled",
                "target_ref":target_ref,"before_fingerprint":preflight.before_fingerprint,"after_fingerprint":after_fingerprint,
                "state_delta":{"before":null,"after":{"acceptance_id":acceptance_id,"candidate_id":preflight.candidate_id,
                "revision_id":preflight.revision_id,"content_fingerprint":preflight.candidate_fingerprint},"narrative_changes":[],"stale_chapter_ids":[],
                "reader_invalidations":{"observation_ids":[],"expectation_ids":[]}},"canon_mutated":true,
                "request_fingerprint":request_args_fingerprint(request),"reader_memory":[]
            }),
        )
    }

    fn publication_preview(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let acceptance_id = string_arg(request, "acceptance_id")?;
        let project = self.open_registered(project_id)?;
        let preview = project.database.preview_publication(acceptance_id)?;
        Ok(
            json!({"schema":"quillframe_publication_preview_v1","persistent":false,
            "source_acceptance_id":preview.source_acceptance_id,"source_fingerprint":preview.source_fingerprint,
            "document_id":preview.document_id,"content":preview.content}),
        )
    }

    fn publication_build(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let acceptance_id = string_arg(request, "acceptance_id")?;
        let format = crate::PublicationFormat::parse(
            request
                .args
                .get("format")
                .and_then(Value::as_str)
                .unwrap_or("md"),
        )?;
        let mut project = self.open_registered(project_id)?;
        let build =
            project
                .database
                .build_publication(project_id, acceptance_id, format, &timestamp())?;
        Ok(
            json!({"schema":"quillframe_publication_build_v1","build_id":build.build_id,"persistent":true,
            "source_acceptance_id":acceptance_id,"source_fingerprint":build.source_fingerprint,
            "output_ref":build.output_ref,"format":build.format,"compiler_contract":build.compiler_contract,
            "identity_fingerprint":build.identity_fingerprint,"artifact_fingerprint":build.artifact_fingerprint,
            "byte_size":build.byte_size}),
        )
    }

    fn publication_collection_build(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let acceptance_ids = request
            .args
            .get("acceptance_ids")
            .cloned()
            .map(serde_json::from_value::<Vec<String>>)
            .transpose()
            .map_err(|error| {
                CoreError::InvalidProject(format!(
                    "publication acceptance list is invalid: {error}"
                ))
            })?
            .ok_or_else(|| {
                CoreError::InvalidProject("publication acceptance list is required".into())
            })?;
        let format = crate::PublicationFormat::parse(string_arg(request, "format")?)?;
        let idempotency_key = string_arg(request, "idempotency_key")?;
        let mut project = self.open_registered(project_id)?;
        let build = project.database.build_publication_collection(
            project_id,
            &acceptance_ids,
            format,
            idempotency_key,
            true,
            &timestamp(),
        )?;
        Ok(
            json!({"schema":"quillframe_publication_collection_result_v1","project_id":project_id,
            "build_id":build.build_id,"source_acceptance_ids":build.source_acceptance_ids,"format":build.format,
            "artifact_fingerprint":build.artifact_fingerprint,"byte_size":build.byte_size,"output_ref":build.output_ref,
            "persistent":true,"authority":false}),
        )
    }

    fn publication_artifact_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let build_id = string_arg(request, "build_id")?;
        let project = self.open_registered(project_id)?;
        let artifact = project
            .database
            .publication_artifact(project_id, build_id)?;
        Ok(
            json!({"schema":"quillframe_publication_artifact_v1","project_id":artifact.project_id,
            "build_id":artifact.build_id,"filename":artifact.filename,"media_type":artifact.media_type,
            "byte_size":artifact.byte_size,"artifact_fingerprint":artifact.artifact_fingerprint,
            "content_base64":artifact.content_base64,"source_acceptance_ids":artifact.source_acceptance_ids,
            "authority":false}),
        )
    }

    fn open_corpus(&self) -> CoreResult<CorpusDatabase> {
        CorpusDatabase::open(self.global_root.join("corpus"), &timestamp())
    }

    fn corpus_collection_scan(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let path = PathBuf::from(string_arg(request, "collection_path")?);
        self.open_corpus()?.scan_collection(&path, &timestamp())
    }

    fn learning_preference_list(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let project = self.open_registered(project_id)?;
        Ok(json!({
            "schema":"quillframe_learning_preference_list_v1",
            "project_id":project_id,
            "items":project.database.learning_preferences()?,
            "authority":false
        }))
    }

    fn learning_feedback_observe(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let mut project = self.open_registered(project_id)?;
        let event = Value::Object(request.args.clone());
        let (event_id, replayed) = project
            .database
            .capture_learning_feedback(&event, &timestamp())?;
        Ok(json!({
            "schema":"quillframe_learning_feedback_observation_v1",
            "project_id":project_id,"event_id":event_id,"status":"captured",
            "replayed":replayed,"preference_authority":false,"canon_authority":false,
            "authority":false
        }))
    }

    fn learning_feedback_list(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let project = self.open_registered(project_id)?;
        Ok(
            json!({"schema":"quillframe_learning_feedback_list_v1","project_id":project_id,
            "items":project.database.learning_feedback(None)?,"authority":false}),
        )
    }

    fn learning_feedback_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let project = self.open_registered(project_id)?;
        let item = project
            .database
            .learning_feedback(Some(string_arg(request, "event_id")?))?
            .into_iter()
            .next()
            .ok_or_else(|| {
                CoreError::InvalidProject("learning feedback event does not exist".into())
            })?;
        Ok(
            json!({"schema":"quillframe_learning_feedback_get_v1","project_id":project_id,
            "item":item,"authority":false}),
        )
    }

    fn learning_preference_get(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let hypothesis_id = string_arg(request, "hypothesis_id")?;
        let project = self.open_registered(project_id)?;
        let item = project
            .database
            .learning_preferences()?
            .into_iter()
            .find(|item| item.get("hypothesis_id").and_then(Value::as_str) == Some(hypothesis_id))
            .ok_or_else(|| {
                CoreError::InvalidProject("preference hypothesis does not exist".into())
            })?;
        Ok(json!({
            "schema":"quillframe_learning_preference_get_v1",
            "project_id":project_id,"item":item,"authority":false
        }))
    }

    fn learning_preference_activation(
        &self,
        request: &BridgeRequest,
        activate: bool,
    ) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let expected_version = request
            .args
            .get("expected_version")
            .and_then(Value::as_u64)
            .ok_or_else(|| CoreError::InvalidProject("expected_version must be u64".into()))?;
        let mut project = self.open_registered(project_id)?;
        let (version, state, replayed) = project.database.set_preference_activation(
            string_arg(request, "hypothesis_id")?,
            expected_version,
            activate,
            string_arg(request, "authorized_by")?,
            string_arg(request, "idempotency_key")?,
            true,
            &timestamp(),
        )?;
        Ok(json!({
            "schema":"quillframe_learning_preference_activation_v1",
            "project_id":project_id,"hypothesis_id":string_arg(request,"hypothesis_id")?,
            "version":version,"state":state,"replayed":replayed,"authority":false
        }))
    }

    fn corpus_selection_propose(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let profile = string_arg(request, "profile")?;
        let limit = request
            .args
            .get("limit")
            .and_then(Value::as_u64)
            .and_then(|value| usize::try_from(value).ok());
        let mut corpus = self.open_corpus()?;
        let value = if let Some(study_id) = request.args.get("study_id").and_then(Value::as_str) {
            let existing = corpus.selection(study_id)?;
            if existing.profile != profile {
                return Err(CoreError::AuthorityConflict(
                    "Corpus study profile does not match the stored proposal".into(),
                ));
            }
            existing
        } else {
            corpus.propose_selection(
                string_arg(request, "collection_id")?,
                profile,
                limit,
                &timestamp(),
            )?
        };
        let mut projection = serde_json::to_value(value)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        projection
            .as_object_mut()
            .unwrap()
            .insert("schema".into(), json!("quillframe_corpus_selection_v2"));
        projection
            .as_object_mut()
            .unwrap()
            .insert("private_local_only".into(), json!(true));
        Ok(projection)
    }

    fn corpus_selection_confirm(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let work_ids =
            serde_json::from_value::<Vec<String>>(
                request.args.get("work_ids").cloned().ok_or_else(|| {
                    CoreError::InvalidProject("Corpus work_ids are required".into())
                })?,
            )
            .map_err(|error| {
                CoreError::InvalidProject(format!("Corpus work_ids are invalid: {error}"))
            })?;
        let value = self.open_corpus()?.confirm_selection(
            string_arg(request, "study_id")?,
            &work_ids,
            string_arg(request, "proposal_fingerprint")?,
            string_arg(request, "profile")?,
            &timestamp(),
        )?;
        let mut projection = serde_json::to_value(value)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        projection
            .as_object_mut()
            .unwrap()
            .insert("schema".into(), json!("quillframe_corpus_selection_v2"));
        projection
            .as_object_mut()
            .unwrap()
            .insert("private_local_only".into(), json!(true));
        Ok(projection)
    }

    fn corpus_study_status(&self, request: &BridgeRequest) -> CoreResult<Value> {
        self.open_corpus()?
            .study_status(string_arg(request, "study_id")?)
    }

    fn corpus_study_cancel(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        self.open_corpus()?
            .cancel_study(string_arg(request, "study_id")?, &timestamp())
    }

    fn corpus_pack_preview(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let study_id = string_arg(request, "study_id")?;
        let pack = self
            .open_corpus()?
            .source_free_pack(study_id)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict("Corpus study has no complete source-free pack".into())
            })?;
        let writer = pack.writer_projection()?;
        Ok(
            json!({"schema":"quillframe_corpus_pack_preview_v2","study_id":study_id,
            "source_free_pack_fingerprint":pack.fingerprint,"genre":writer.genre,
            "mechanism_count":writer.mechanisms.len(),"style_guidance":writer.style_guidance,
            "evidence_absent":writer.evidence_absent,"source_prose_visible":false,"authority":false}),
        )
    }

    fn corpus_pack_activate(&self, request: &BridgeRequest) -> CoreResult<Value> {
        require_authorized(request)?;
        let project_id = string_arg(request, "project_id")?;
        let study_id = string_arg(request, "study_id")?;
        let pack = self
            .open_corpus()?
            .source_free_pack(study_id)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict("Corpus study has no complete source-free pack".into())
            })?;
        let applicability = request
            .args
            .get("applicability")
            .ok_or_else(|| CoreError::InvalidProject("Corpus applicability is required".into()))?;
        let expected_version = request
            .args
            .get("expected_version")
            .and_then(Value::as_u64)
            .ok_or_else(|| {
                CoreError::InvalidProject("Corpus expected_version is required".into())
            })?;
        let authorization = json!({"authorized_by":"author:local","study_id":study_id,
            "pack_fingerprint":pack.fingerprint,"user_authorized":true});
        let mut project = self.open_registered(project_id)?;
        let (activation_id, version) = project.database.activate_source_free_corpus_pack(
            &pack,
            applicability,
            expected_version,
            &authorization,
            string_arg(request, "idempotency_key")?,
            &timestamp(),
        )?;
        Ok(
            json!({"schema":"quillframe_corpus_pack_activation_v1","project_id":project_id,"study_id":study_id,
            "activation_id":activation_id,"version":version,"pack_fingerprint":pack.fingerprint,
            "writer_projection_fingerprint":pack.writer_projection()?.fingerprint,"authority":false}),
        )
    }

    async fn learning_feedback_execute(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let event_id = string_arg(request, "event_id")?;
        let event = {
            let project = self.open_registered(project_id)?;
            project
                .database
                .learning_feedback(Some(event_id))?
                .into_iter()
                .next()
                .ok_or_else(|| {
                    CoreError::InvalidProject("learning feedback event does not exist".into())
                })?
        };
        let service_id = string_arg(request, "service_id")?;
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        let catalog = service.catalog.as_ref().ok_or_else(|| {
            CoreError::ModelRuntime("learning model service has no discovered catalog".into())
        })?;
        if !service.enabled || service.discovery_state != "connected" {
            return Err(CoreError::ModelRuntime(
                "learning model service is not connected".into(),
            ));
        }
        let model = request
            .args
            .get("model_id")
            .and_then(Value::as_str)
            .unwrap_or_else(|| catalog.models[0].model_id.as_str());
        let result=self.execute_learning_model_stage(
            project_id,event_id,&service,model,"learning_feedback_interpret",
            json!({"feedback_event":event,
                "contract":"Return JSON only: {capture_decision:'capture'|'skip',scope:'one_off'|'project'|'user_taste'|'general_craft'|null,statement:string|null,reason:string}. Capture only a durable author preference evidenced by this exact feedback. Skip transient fixes, ambiguous comments or candidate-specific defects. Skip must return null scope and statement; capture must return both."}),
            2_000,0.1
        ).await?;
        let interpretation: FeedbackInterpretation = strict_model_json(&result)?;
        interpretation.validate()?;
        let hypothesis_id = {
            let mut project = self.open_registered(project_id)?;
            project.database.apply_feedback_interpretation(
                event_id,
                &interpretation,
                &result.fingerprint,
                &timestamp(),
            )?
        };
        Ok(
            json!({"schema":"quillframe_learning_feedback_execution_v1","project_id":project_id,
            "event_id":event_id,"status":if hypothesis_id.is_some(){"interpreted"}else{"skipped"},
            "hypothesis_id":hypothesis_id,"preference_authority":false,"canon_authority":false,"authority":false}),
        )
    }

    async fn learning_preference_review(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let project_id = string_arg(request, "project_id")?;
        let hypothesis_id = string_arg(request, "hypothesis_id")?;
        let expected_version = request
            .args
            .get("expected_version")
            .and_then(Value::as_u64)
            .ok_or_else(|| CoreError::InvalidProject("expected_version must be u64".into()))?;
        let preference = {
            let project = self.open_registered(project_id)?;
            project
                .database
                .learning_preferences()?
                .into_iter()
                .find(|item| {
                    item.get("hypothesis_id").and_then(Value::as_str) == Some(hypothesis_id)
                })
                .ok_or_else(|| {
                    CoreError::InvalidProject("preference hypothesis does not exist".into())
                })?
        };
        let service_id = string_arg(request, "service_id")?;
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        let catalog = service.catalog.as_ref().ok_or_else(|| {
            CoreError::ModelRuntime("preference review service has no catalog".into())
        })?;
        if !service.enabled || service.discovery_state != "connected" {
            return Err(CoreError::ModelRuntime(
                "preference review service is not connected".into(),
            ));
        }
        let model = request
            .args
            .get("model_id")
            .and_then(Value::as_str)
            .unwrap_or_else(|| catalog.models[0].model_id.as_str());
        let aggregate_id = format!("{hypothesis_id}:v{expected_version}");
        let result=self.execute_learning_model_stage(
            project_id,&aggregate_id,&service,model,"learning_preference_review",
            json!({"preference":preference,
                "contract":"Return JSON only: {decision:'validated'|'contested',reason:string}. Validate only when the evidence supports a reusable author preference rather than a one-off candidate repair, and contest contradictions or overgeneralization."}),
            2_000,0.1
        ).await?;
        let review: PreferenceReviewResult = strict_model_json(&result)?;
        review.validate()?;
        let (version, decision) = {
            let mut project = self.open_registered(project_id)?;
            project.database.apply_preference_review(
                hypothesis_id,
                expected_version,
                &review,
                &result.fingerprint,
                &timestamp(),
            )?
        };
        Ok(
            json!({"schema":"quillframe_learning_preference_review_v1","project_id":project_id,
            "hypothesis_id":hypothesis_id,"version":version,"decision":decision,
            "preference_authority":false,"authority":false}),
        )
    }

    #[allow(clippy::too_many_arguments)]
    async fn execute_learning_model_stage(
        &self,
        project_id: &str,
        aggregate_id: &str,
        service: &ModelServiceRecord,
        model: &str,
        stage_key: &str,
        input: Value,
        max_output_tokens: u32,
        temperature: f32,
    ) -> CoreResult<ModelResult> {
        let assembly = PromptAssembly::build(stage_key, semantic_system(stage_key), input)?;
        let input_fingerprint = assembly.fingerprint.clone();
        let request_id = format!("learning-{stage_key}-{}", &input_fingerprint[7..23]);
        let model_request = ModelRequest {
            request_id,
            model: model.into(),
            system: assembly.system_text(),
            user: assembly.user_text()?,
            temperature: Some(temperature),
            max_output_tokens: Some(max_output_tokens),
            absolute_deadline_ms: 120_000,
        };
        if let Some(result) = {
            let mut project = self.open_registered(project_id)?;
            project.database.begin_learning_semantic_call(
                aggregate_id,
                stage_key,
                &model_request,
                &input_fingerprint,
                &timestamp(),
            )?
        } {
            return Ok(result);
        }
        let result = ModelRuntime::new(self.secret_store()?)
            .execute(&service.endpoint, &model_request)
            .await;
        match result {
            Ok(result) => {
                let mut project = self.open_registered(project_id)?;
                project.database.finish_learning_semantic_call(
                    aggregate_id,
                    stage_key,
                    Some(&result),
                    &timestamp(),
                )?;
                Ok(result)
            }
            Err(error) => {
                let mut project = self.open_registered(project_id)?;
                project.database.finish_learning_semantic_call(
                    aggregate_id,
                    stage_key,
                    None,
                    &timestamp(),
                )?;
                Err(error)
            }
        }
    }

    async fn corpus_study_execute(&self, request: &BridgeRequest) -> CoreResult<Value> {
        let study_id = string_arg(request, "study_id")?;
        let service_id = string_arg(request, "service_id")?;
        let service = self
            .lock_global()?
            .model_service(service_id)?
            .ok_or_else(|| CoreError::InvalidProject("model service does not exist".into()))?;
        if !service.enabled || service.discovery_state != "connected" {
            return Err(CoreError::ModelRuntime(
                "model service must pass discovery before Corpus analysis".into(),
            ));
        }
        let catalog = service.catalog.as_ref().ok_or_else(|| {
            CoreError::ModelRuntime("connected model service has no catalog".into())
        })?;
        catalog.validate()?;
        let model = request
            .args
            .get("model_id")
            .and_then(Value::as_str)
            .unwrap_or(&catalog.models[0].model_id)
            .to_string();
        if !catalog.models.iter().any(|item| item.model_id == model) {
            return Err(CoreError::ModelRuntime(
                "selected Corpus model is not in the discovered catalog".into(),
            ));
        }
        let max_jobs = request
            .args
            .get("max_jobs")
            .and_then(Value::as_u64)
            .unwrap_or(8)
            .clamp(1, 32);
        if request.operation == "corpus.study.resume" {
            let mut corpus = self.open_corpus()?;
            let status = corpus.study_status(study_id)?;
            if status.get("continue_required").and_then(Value::as_bool) == Some(true) {
                let checkpoint = status
                    .get("checkpoint_fingerprint")
                    .and_then(Value::as_str)
                    .ok_or_else(|| CoreError::Storage("Corpus checkpoint is missing".into()))?;
                corpus.continue_after_golden_three(
                    study_id,
                    checkpoint,
                    "explicit Studio resume",
                    &timestamp(),
                )?;
            }
        }
        for _ in 0..max_jobs {
            let dispatch = {
                let mut corpus = self.open_corpus()?;
                corpus.dispatch_next_stage(study_id, &model, &timestamp())?
            };
            let Some(dispatch) = dispatch else { break };
            let result = ModelRuntime::new(self.secret_store()?)
                .execute(&service.endpoint, &dispatch.request)
                .await;
            match result {
                Ok(result) => {
                    self.open_corpus()?.confirm_stage(
                        study_id,
                        &dispatch.call_id,
                        &result,
                        &timestamp(),
                    )?;
                }
                Err(error) => {
                    self.open_corpus()?.mark_stage_unconfirmed(
                        study_id,
                        &dispatch.call_id,
                        "model_transport_unconfirmed",
                        &timestamp(),
                    )?;
                    return Err(error);
                }
            }
        }
        self.open_corpus()?.study_status(study_id)
    }

    fn open_registered(&self, project_id: &str) -> CoreResult<NativeProject> {
        let registered = self
            .lock_global()?
            .project(project_id)?
            .ok_or_else(|| CoreError::InvalidProject("project is not registered".into()))?;
        NativeProject::open(Path::new(&registered.project_dir))
    }

    fn lock_global(&self) -> CoreResult<std::sync::MutexGuard<'_, GlobalDatabase>> {
        self.global
            .lock()
            .map_err(|_| CoreError::Storage("global database mutex was poisoned".into()))
    }

    fn secret_store(&self) -> CoreResult<&dyn SecretStore> {
        self.secrets.as_deref().ok_or_else(|| {
            CoreError::ModelRuntime("OS credential store is unavailable on this host".into())
        })
    }

    fn envelope(
        &self,
        raw_request: Value,
        request: Option<&BridgeRequest>,
        status: &str,
        data: Value,
        error: Value,
    ) -> Value {
        let request_fingerprint = sha256_fingerprint(canonical_bytes(&redact(raw_request)));
        let mut envelope = json!({
            "schema":"quillframe_host_bridge_result_v11","bridge_version":"11",
            "request_id":request.map(|v|v.request_id.as_str()).unwrap_or(""),
            "operation":request.map(|v|v.operation.as_str()).unwrap_or(""),
            "surface":request.map(|v|v.surface.as_str()).unwrap_or("local_app"),
            "status":status,"data":data,"error":error,
            "request_fingerprint":request_fingerprint,"secret_values_persisted":false,
            "authority":false,"canon_authority":false,"framework_write_authority":false,
            "settlement_authority":false
        });
        let result_fingerprint = sha256_fingerprint(canonical_bytes(&envelope));
        envelope.as_object_mut().unwrap().insert(
            "result_fingerprint".into(),
            Value::String(result_fingerprint),
        );
        envelope
    }
}

fn string_arg<'a>(request: &'a BridgeRequest, name: &str) -> CoreResult<&'a str> {
    request
        .args
        .get(name)
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| CoreError::InvalidProject(format!("{name} must be a non-empty string")))
}

fn object_arg<'a>(request: &'a BridgeRequest, name: &str) -> CoreResult<&'a Map<String, Value>> {
    request
        .args
        .get(name)
        .and_then(Value::as_object)
        .ok_or_else(|| CoreError::InvalidProject(format!("{name} must be an object")))
}

fn require_authorized(request: &BridgeRequest) -> CoreResult<()> {
    if request.args.get("user_authorized").and_then(Value::as_bool) != Some(true) {
        return Err(CoreError::AuthorityConflict(
            "explicit user authorization is required".into(),
        ));
    }
    Ok(())
}

fn request_args_fingerprint(request: &BridgeRequest) -> String {
    sha256_fingerprint(canonical_bytes(&redact(Value::Object(
        request.args.clone(),
    ))))
}

fn storage(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

fn parse_auth_style(value: Option<&str>, has_token: bool) -> CoreResult<AuthStyle> {
    match value {
        None if has_token => Ok(AuthStyle::Bearer),
        None => Ok(AuthStyle::None),
        Some("bearer") if has_token => Ok(AuthStyle::Bearer),
        Some("x_api_key") if has_token => Ok(AuthStyle::XApiKey),
        Some("none") if !has_token => Ok(AuthStyle::None),
        _ => Err(CoreError::ModelRuntime(
            "model authentication style does not match the supplied credential".into(),
        )),
    }
}

fn parse_protocol_family(value: Option<&str>) -> CoreResult<ProtocolFamily> {
    match value.unwrap_or("openai_chat_completions") {
        "openai_chat_completions" => Ok(ProtocolFamily::OpenaiChatCompletions),
        "openai_responses" => Ok(ProtocolFamily::OpenaiResponses),
        "anthropic_messages" => Ok(ProtocolFamily::AnthropicMessages),
        _ => Err(CoreError::ModelRuntime(
            "model protocol family is unsupported".into(),
        )),
    }
}

fn model_service_projection(record: &ModelServiceRecord) -> Value {
    let auth_style = match record.endpoint.auth_style {
        AuthStyle::Bearer => "bearer",
        AuthStyle::XApiKey => "x_api_key",
        AuthStyle::None => "none",
    };
    let protocol_family = match record.endpoint.protocol_family {
        ProtocolFamily::OpenaiChatCompletions => "openai_chat_completions",
        ProtocolFamily::OpenaiResponses => "openai_responses",
        ProtocolFamily::AnthropicMessages => "anthropic_messages",
    };
    json!({
        "service_id":record.endpoint.service_id,"endpoint":record.endpoint.endpoint,
        "auth_style":auth_style,"protocol_family":protocol_family,
        "credential_present":record.endpoint.credential_ref.is_some(),"allow_loopback_http":record.endpoint.allow_loopback_http,
        "enabled":record.enabled,"discovery_state":record.discovery_state,
        "models":record.catalog.as_ref().map(|catalog| catalog.models.clone()).unwrap_or_default(),
        "last_checked_at":record.last_checked_at,"version":record.version,"created_at":record.created_at,"updated_at":record.updated_at
    })
}

fn strict_model_json<T: for<'de> Deserialize<'de>>(result: &ModelResult) -> CoreResult<T> {
    serde_json::from_str(&result.content).map_err(|error| {
        CoreError::InvalidProject(format!(
            "semantic stage returned invalid typed JSON for {}: {error}",
            result.request_id
        ))
    })
}

fn canonical_plan_target(value: &str) -> CoreResult<String> {
    if value == "book" || value == "book:BOOK" {
        return Ok("book:BOOK".into());
    }
    for prefix in ["volume:", "unit:", "chapter:"] {
        if value
            .strip_prefix(prefix)
            .is_some_and(|node| !node.is_empty())
        {
            return Ok(value.into());
        }
    }
    Err(CoreError::InvalidPlan(
        "plan target must be book or a typed volume, unit or chapter reference".into(),
    ))
}

fn semantic_gate_contract(instruction: &str) -> Value {
    json!({
        "instruction":instruction,
        "output":"Return JSON only: {decision:'accept'|'revise',findings:[{finding_id,severity:'s1'|'s2'|'s3'|'s4',category:'structure'|'character'|'prose'|'consistency'|'platform'|'factual'|'format'|'causal'|'rule_boundary',location,evidence,issue,fix_direction}]}. accept requires an empty findings array; revise requires at least one concrete finding."
    })
}

fn semantic_system(stage_key: &str) -> &'static str {
    if stage_key.starts_with("surface_scene_") {
        return "You are Quillframe's direct Chinese web-novel Surface Writer. Produce only the frozen scene as lived prose and return only the requested JSON artifact.";
    }
    match stage_key {
        "context_query_plan" => "You are Quillframe's semantic context query planner. Ask for bounded evidence needed by the frozen chapter and return only exact JSON selectors.",
        "context_greenlight" => "You are Quillframe's context greenlight selector. Select only exact candidate references based on narrative relevance and return only the requested JSON artifact.",
        "corpus_greenlight" => "You are Quillframe's source-free corpus mechanism selector. Select only exact active pack fingerprints for narrative applicability and return only the requested JSON artifact.",
        "preference_greenlight" => "You are Quillframe's author-preference relevance selector. Select only exact active hypothesis ids, preserve explicit current choices, and return only the requested JSON artifact.",
        "learning_feedback_interpret" => "You are Quillframe's bounded author-feedback interpreter. Distinguish durable preference evidence from one-off repair and return only the requested JSON artifact.",
        "learning_preference_review" => "You are Quillframe's independent preference evidence reviewer. Check reuse scope and overgeneralization, then return only the requested JSON artifact.",
        "character_simulation" => "You are Quillframe's private character-action simulator. Return only the requested JSON artifact, never chain-of-thought.",
        "scene_resolution" => "You are Quillframe's causal scene resolver. Return only the requested JSON artifact.",
        "repair_editor" => "You are Quillframe's repair editor. Convert exact failed evidence into FIX + PRESERVE constraints without writing prose. Return only the requested JSON artifact.",
        "surface_realization" => "You are Quillframe's direct Chinese web-novel Surface Writer. Produce the chapter once from the frozen material and return only the requested JSON artifact.",
        "reader_engagement" => "You are a blind web-novel reader. Judge lived reading experience without rule checklists and return only the requested JSON artifact.",
        "continuity_rule_audit" => "You are Quillframe's continuity and rule auditor. Return only exact, evidence-bound JSON findings.",
        "candidate_self_audit" => "You are Quillframe's objective-bound candidate qualifier. Return only the requested JSON gate result.",
        "repair_comparison" => "You are Quillframe's exact repair comparator. Compare incumbent and challenger against the frozen objective; return only the requested JSON artifact.",
        "settlement_tracking_projection" => "You are Quillframe's source-bound chapter continuity projector. Extract a compact settlement proposal from the exact manuscript and return only the requested JSON artifact.",
        "settlement_tracking_audit" => "You are Quillframe's independent tracking projection auditor. Verify every proposed state change against exact manuscript evidence and return only the requested JSON gate result.",
        "independent_semantic_gate" => "You are a fresh independent fiction reviewer. You have no access to other review outputs. Return only the requested JSON gate result.",
        _ => "Return only the exact JSON artifact requested by Quillframe.",
    }
}

fn last_chars(value: &str, maximum: usize) -> String {
    let start = value
        .char_indices()
        .rev()
        .nth(maximum.saturating_sub(1))
        .map(|(index, _)| index)
        .unwrap_or(0);
    value[start..].to_string()
}

fn unix_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .try_into()
        .unwrap_or(u64::MAX)
}

fn timestamp() -> String {
    let millis = unix_millis();
    format!("unix-ms:{millis}")
}

fn canonical_bytes(value: &Value) -> Vec<u8> {
    serde_json::to_vec(value).expect("JSON value is serializable")
}

fn redact(value: Value) -> Value {
    match value {
        Value::Array(values) => Value::Array(values.into_iter().map(redact).collect()),
        Value::Object(values) => Value::Object(
            values
                .into_iter()
                .map(|(key, value)| {
                    let normalized = key.to_ascii_lowercase().replace('-', "_");
                    let secret = matches!(
                        normalized.as_str(),
                        "access_token" | "api_key" | "apikey" | "password" | "secret" | "token"
                    );
                    (
                        key,
                        if secret {
                            Value::String("<redacted>".into())
                        } else {
                            redact(value)
                        },
                    )
                })
                .collect(),
        ),
        other => other,
    }
}

#[cfg(all(test, any(windows, target_os = "linux")))]
mod tests {
    use std::collections::BTreeSet;
    use std::sync::Arc;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    struct MemorySecrets;
    impl SecretStore for MemorySecrets {
        fn read_secret(&self, _credential_ref: &str) -> CoreResult<Option<String>> {
            Ok(None)
        }
        fn write_secret(&self, _credential_ref: &str, _secret: &str) -> CoreResult<()> {
            Ok(())
        }
        fn delete_secret(&self, _credential_ref: &str) -> CoreResult<()> {
            Ok(())
        }
    }

    fn root() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("qf-bridge-{}-{nonce}", std::process::id()))
    }

    fn request(operation: &str, args: Value) -> Value {
        json!({"schema":"quillframe_host_bridge_request_v11","bridge_version":"11","request_id":"REQ1","operation":operation,"surface":"local_app","args":args,"authority":false})
    }

    fn save_ancestor_plans(runtime: &HostBridgeRuntime) {
        let plans = [
            json!({"target_ref":"book","title":"全书设计","idempotency_key":"plan-book",
                "typed_body":{"kind":"book","body":{"reader_promise":"主角以主动选择改变困局",
                    "protagonist_agency":"每次升级来自行动与代价","central_conflict":"追查真相与守护同伴冲突",
                    "progression":["从逃亡者成长为破局者"],"endgame_reserve":["幕后契约真相"],
                    "anti_exhaustion_limits":["不提前透支终局真相"]}}}),
            json!({"target_ref":"volume:VOL001","title":"第一卷设计","idempotency_key":"plan-volume-1",
                "typed_body":{"kind":"volume","body":{"volume_promise":"摆脱第一轮追捕并发现更大敌人",
                    "net_situation_change":"从被动逃亡转为主动追查","opposition":"追兵与内部背叛",
                    "relationship_movements":["与同伴建立互信"],"climax":"在封锁中反向设局",
                    "inherited_debts":["死者身份"]}}}),
            json!({"target_ref":"unit:UNIT001","title":"第一单元计划","idempotency_key":"plan-unit-1",
                "typed_body":{"kind":"unit","body":{"loop_question":"主角能否带同伴穿过封锁？",
                    "setup":["追兵封路"],"release":"找到维修井","aftermath":"身份暴露",
                    "rewards":["同伴获救"],"delay_costs":["追兵锁定主角"],
                    "foreshadowing":["死者现身"],"callbacks":[]}}}),
        ];
        for plan in plans {
            let saved = runtime.invoke_value(request(
                "plan.save",
                json!({"project_id":"BOOK","target_ref":plan["target_ref"],"title":plan["title"],
                    "content":"{}","expected_version":0,"typed_body":plan["typed_body"],
                    "reader_intent":{},"expectation_refs":[],"idempotency_key":plan["idempotency_key"],
                    "user_authorized":true}),
            ));
            assert_eq!(saved["status"], "ok", "{saved}");
        }
    }

    async fn mock_model_service() -> (String, tokio::task::JoinHandle<()>) {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let task = tokio::spawn(async move {
            loop {
                let Ok((mut socket, _)) = listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let mut request_bytes = Vec::new();
                    let mut buffer = [0_u8; 4096];
                    let header_end;
                    loop {
                        let read = socket.read(&mut buffer).await.unwrap();
                        if read == 0 {
                            return;
                        }
                        request_bytes.extend_from_slice(&buffer[..read]);
                        if let Some(index) = request_bytes
                            .windows(4)
                            .position(|part| part == b"\r\n\r\n")
                        {
                            header_end = index + 4;
                            break;
                        }
                    }
                    let headers =
                        String::from_utf8_lossy(&request_bytes[..header_end]).into_owned();
                    let content_length = headers
                        .lines()
                        .find_map(|line| {
                            let (name, value) = line.split_once(':')?;
                            name.eq_ignore_ascii_case("content-length")
                                .then(|| value.trim().parse::<usize>().ok())
                                .flatten()
                        })
                        .unwrap_or(0);
                    while request_bytes.len() < header_end + content_length {
                        let read = socket.read(&mut buffer).await.unwrap();
                        if read == 0 {
                            return;
                        }
                        request_bytes.extend_from_slice(&buffer[..read]);
                    }
                    let response = if headers.starts_with("GET ") {
                        json!({"data":[{"id":"mock-fiction-model","display_name":"Mock Fiction Model"}]})
                    } else {
                        let body: Value = serde_json::from_slice(
                            &request_bytes[header_end..header_end + content_length],
                        )
                        .unwrap();
                        let system = body
                            .pointer("/messages/0/content")
                            .and_then(Value::as_str)
                            .unwrap_or("");
                        let user = body
                            .pointer("/messages/1/content")
                            .and_then(Value::as_str)
                            .unwrap_or("");
                        let first_context_reference = serde_json::from_str::<Value>(user)
                            .ok()
                            .and_then(|assembly| {
                                assembly
                                    .get("blocks")?
                                    .as_array()?
                                    .iter()
                                    .find_map(|block| {
                                        block
                                            .get("content")?
                                            .get("candidate_pool")?
                                            .as_array()?
                                            .first()?
                                            .get("reference")?
                                            .as_str()
                                            .map(str::to_string)
                                    })
                            });
                        let first_corpus_fingerprint = serde_json::from_str::<Value>(user)
                            .ok()
                            .and_then(|assembly| {
                                assembly
                                    .get("blocks")?
                                    .as_array()?
                                    .iter()
                                    .find_map(|block| {
                                        block
                                            .get("content")?
                                            .get("candidate_packs")?
                                            .as_array()?
                                            .first()?
                                            .get("source_free_pack_fingerprint")?
                                            .as_str()
                                            .map(str::to_string)
                                    })
                            });
                        let content = if system.contains("semantic context query planner") {
                            json!({"queries":["rain pursuit unexpected return"],"required_references":[]})
                        } else if system.contains("context greenlight selector") {
                            json!({"selected_references":[first_context_reference.unwrap_or_else(||"plan-chain:CH001".into())]})
                        } else if system.contains("corpus mechanism selector") {
                            json!({"selected_pack_fingerprints":first_corpus_fingerprint.into_iter().collect::<Vec<_>>()})
                        } else if system.contains("author-preference relevance selector") {
                            json!({"selected_hypothesis_ids":[]})
                        } else if system.contains("author-feedback interpreter") {
                            json!({"capture_decision":"capture","scope":"project","statement":"å¯¹ç™½å¿…é¡»ç»‘å®šè¯´è¯äººã€ç©ºé—´ä¸Žå¯è§ååº”","reason":"feedback states a reusable project prose preference"})
                        } else if system.contains("preference evidence reviewer") {
                            json!({"decision":"validated","reason":"exact feedback supports a reusable bounded project preference"})
                        } else if system.contains("character-action") {
                            json!({"actions":[{"scene_id":"SC001","character":"主角","action":"推开门走入雨夜","motive_pressure":"必须赶在追兵前抵达","observable_consequence":"留下带血脚印"}]})
                        } else if system.contains("causal scene resolver") {
                            json!({"scenes":[{"scene_id":"SC001","action_sequence":["主角推门","追兵看见脚印"],"turn":"门外早有伏兵","exit_state":"主角被迫改道"}]})
                        } else if system.contains("repair editor") {
                            json!({"repair_owner":"prose_writer","generation_mode":"local_or_bounded_repair",
                                "objective_envelope":"保留雨夜追逃、主动选择与死者现身的章尾拉力",
                                "targets":[{"location":"章中行动转折","source_excerpt":"REPAIR_SOURCE_MARKER 雨夜里，行动与反应断开了。","fix":"补足可见的因果反应","preserve":["角色主动性","章尾悬念"]}],
                                "invalidation_boundary":["surface_realization","downstream_reviews"],"comparison_required":true})
                        } else if system.contains("repair comparator") {
                            json!({"target_outcome":"improved","objective_preservation":"preserved","winner":"challenger",
                                "outcome_class":"successful_repair","introduced_regressions":[]})
                        } else if system.contains("chapter continuity projector") {
                            json!({"net_change":"主角逃过追兵但发现死者现身",
                                "open_expectations":["死者为何现身"],"paid_expectations":["主角暂时甩开追兵"],
                                "relationship_changes":[],"state_changes":["主角改道进入侧门"],
                                "next_pull":"本该死去的人站在门后","character_snapshot_updates":{"主角":"暂时脱离追捕，面对死者现身"},
                                "entity_deltas":[{"entity_kind":"character","entity_id":"CHAR-SHEN-YAN","display_name":"沈砚",
                                    "state":{"situation":"暂时脱离追捕，面对死者现身"},"evidence_excerpt":"沈砚"}],
                                "relationship_deltas":[],
                                "knowledge_deltas":[{"knowledge_id":"KNOW-DEAD-APPEARED","character_id":"CHAR-SHEN-YAN",
                                    "fact":{"dead_person_appeared":true},"confidence":"observed","evidence_excerpt":"本该死去的人"}],
                                "timeline_deltas":[{"event_id":"EVT-DEAD-APPEARS","title":"死者现身",
                                    "description":"主角改道后看见本该死去的人","evidence_excerpt":"门后"}],
                                "expectation_deltas":[{"expectation_id":"EXP-DEAD-IDENTITY","kind":"mystery","action":"open",
                                    "description":"死者为何现身","evidence_excerpt":"本该死去的人"}]})
                        } else if system.contains("Surface Writer") {
                            if user.contains("force repair")
                                && user.contains("\"repair_spec\":null")
                            {
                                json!({"manuscript":"REPAIR_SOURCE_MARKER 雨夜里，行动与反应断开了。"})
                            } else if user.contains("\"repair_spec\":{") {
                                json!({"manuscript":"雨砸在门板上。沈砚踏进积水，故意把带血的脚印引向东巷；追兵果然分出两人扑过去，他这才撞开西侧木门。\n\n门后，本该死去的人抬起了头。"})
                            } else {
                                json!({"manuscript":"雨砸在门板上。沈砚推门出去，鞋底的血刚落进积水，巷口便亮起三盏灯。\n\n“他在这里。”\n\n沈砚没回头。他踢翻竹筐，借着满街滚动的青梨撞开侧门——门后，却站着本该死去的人。"})
                            }
                        } else if system.contains("blind web-novel reader")
                            && user.contains("REPAIR_SOURCE_MARKER")
                        {
                            json!({"decision":"revise","findings":[{"finding_id":"reader-causality-1","severity":"s2",
                                "category":"causal","location":"章中转折","evidence":"行动后没有可见反应","issue":"因果链断裂",
                                "fix_direction":"补足对手反应并保留角色主动选择"}]})
                        } else {
                            json!({"decision":"accept","findings":[]})
                        };
                        json!({"id":"mock-response","model":"mock-fiction-model","choices":[{"message":{"content":content.to_string()}}],
                            "usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150}})
                    };
                    let bytes = response.to_string();
                    let wire=format!("HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",bytes.len(),bytes);
                    socket.write_all(wire.as_bytes()).await.unwrap();
                });
            }
        });
        (format!("http://{address}/"), task)
    }

    async fn produce_and_settle_chapter(
        runtime: &HostBridgeRuntime,
        service_id: &str,
        ordinal: u32,
    ) -> (String, String) {
        save_ancestor_plans(runtime);
        let chapter_id = format!("CH{ordinal:03}");
        let document_id = format!("DOC-{chapter_id}");
        let plan = runtime.invoke_value(request(
            "plan.save",
            json!({
                "project_id":"BOOK","target_ref":format!("chapter:{chapter_id}"),
                "title":format!("Chapter {ordinal} Plan"),"content":"{}","expected_version":0,
                "typed_body":{"kind":"chapter","body":{"reader_contract":{
                    "reader_question":"Can the lead escape?","visible_reward":"See through the ambush",
                    "character_choice":"Enter danger deliberately","cost":"Expose the route",
                    "net_change":"The pursuers lock onto the lead","next_pull":"Why did the dead person appear?"},
                    "constraint_lock":{"length":{"min":2800,"max":3800,"unit":"chinese_characters"},
                        "must_happen":[{"id":"dead-person","statement":"The dead person appears after the lead chooses to enter danger"}],
                        "must_not_happen":[],"exact_time_anchors":[],"stop_point":"Stop when the dead person appears",
                        "end_debt":"Why did the dead person appear?"},
                    "scenes":[{"scene_id":"SC001","ordinal":1,"viewpoint":"lead","location":"rain alley",
                        "entry_state":"wounded and pursued","objective":"reach the contact","opposition":"blocked route",
                        "turn":"the dead person appears","exit_state":"forced to reroute","emotion_target":"pressure to doubt",
                        "reader_effect":"respect the choice and question the dead person"}]}},
                "reader_intent":{"reader_question":"Can the lead escape?","visible_reward":"See through the ambush",
                    "character_choice":"Enter danger deliberately","cost":"Expose the route",
                    "net_change":"The pursuers lock onto the lead","next_chapter_pull":"Why did the dead person appear?"},
                "expectation_refs":[],"idempotency_key":format!("plan-{ordinal}"),"user_authorized":true
            }),
        ));
        assert_eq!(plan["status"], "ok", "{plan}");
        let started = runtime.invoke_value(request(
            "author.run.start",
            json!({"project_id":"BOOK","task_mode":"DRAFT","target_ref":document_id,
                "payload":{"chapter_id":chapter_id,"author_profile":"balanced",
                    "instruction":format!("Write chapter {ordinal}"),"reader_grip":"high",
                    "rule_material":[{"id":"request","authority":"current_request","statement":format!("Write chapter {ordinal}")}]},
                "idempotency_key":format!("run-{ordinal}")}),
        ));
        assert_eq!(started["status"], "ok", "{started}");
        let run_id = started["data"]["run_id"].as_str().unwrap().to_owned();
        let executed = runtime
            .invoke_value_async(request(
                "author.run.execute",
                json!({"project_id":"BOOK","run_id":run_id,"service_id":service_id,
                    "document_id":format!("DOC-{chapter_id}")}),
            ))
            .await;
        assert_eq!(executed["status"], "ok", "{executed}");
        assert_eq!(executed["data"]["candidate_visible"], true, "{executed}");
        let candidate_id = executed["data"]["candidate_id"].as_str().unwrap();
        let candidate_fingerprint = executed["data"]["candidate_fingerprint"].as_str().unwrap();
        let accepted = runtime.invoke_value(request(
            "candidate.accept",
            json!({"project_id":"BOOK","candidate_id":candidate_id,
                "candidate_fingerprint":candidate_fingerprint,"authorized_by":"author:local",
                "authorization":{"intent":"accept"},"idempotency_key":format!("accept-{ordinal}"),
                "user_authorized":true}),
        ));
        assert_eq!(accepted["status"], "ok", "{accepted}");
        let acceptance_id = accepted["data"]["acceptance_id"]
            .as_str()
            .unwrap()
            .to_owned();
        let preflight = runtime.invoke_value(request(
            "settlement.preflight",
            json!({"project_id":"BOOK","acceptance_id":acceptance_id,
                "target_ref":format!("chapter:{chapter_id}")}),
        ));
        assert_eq!(preflight["status"], "ok", "{preflight}");
        assert!(preflight["data"]["narrative_proposal"].is_object());
        let settled = runtime.invoke_value(request(
            "settlement.apply",
            json!({"project_id":"BOOK","acceptance_id":acceptance_id,
                "target_ref":format!("chapter:{chapter_id}"),
                "expected_before_fingerprint":preflight["data"]["expected_before_fingerprint"],
                "expected_preflight_fingerprint":preflight["data"]["preflight_fingerprint"],
                "idempotency_key":format!("settle-{ordinal}"),"user_authorized":true}),
        ));
        assert_eq!(settled["status"], "ok", "{settled}");
        assert_eq!(settled["data"]["status"], "settled", "{settled}");
        (acceptance_id, run_id)
    }

    #[tokio::test]
    async fn three_chapters_run_through_model_review_settlement_continuity_and_publication() {
        let root = root();
        let (endpoint, server) = mock_model_service().await;
        let runtime =
            HostBridgeRuntime::open_with_secret_store(&root, Arc::new(MemorySecrets)).unwrap();
        let created = runtime.invoke_value(request(
            "project.create",
            json!({"project_id":"BOOK","title":"Long Running Book"}),
        ));
        assert_eq!(created["status"], "ok", "{created}");
        let connected = runtime
            .invoke_value_async(request(
                "model.service.add",
                json!({"endpoint":endpoint,"auth_style":"none",
                    "protocol_family":"openai_chat_completions","allow_loopback_http":true}),
            ))
            .await;
        assert_eq!(connected["status"], "ok", "{connected}");
        let service_id = connected["data"]["service"]["service_id"].as_str().unwrap();
        let mut acceptance_ids = Vec::new();
        let mut last_run_id = String::new();
        for ordinal in 1..=3 {
            if ordinal > 1 {
                let chapter = runtime.invoke_value(request(
                    "chapter.create",
                    json!({"project_id":"BOOK","title":format!("Chapter {ordinal}"),
                        "idempotency_key":format!("chapter-{ordinal}"),"user_authorized":true}),
                ));
                assert_eq!(chapter["status"], "ok", "{chapter}");
            }
            let (acceptance_id, run_id) =
                produce_and_settle_chapter(&runtime, service_id, ordinal).await;
            last_run_id = run_id.clone();
            acceptance_ids.push(acceptance_id);
            let project = runtime.open_registered("BOOK").unwrap();
            let tracking = project
                .database
                .load_tracking_state("BOOK")
                .unwrap()
                .unwrap();
            assert_eq!(tracking.version, u64::from(ordinal));
            assert_eq!(tracking.chapters.len(), ordinal as usize);
            let production = project.database.load_production_request(&run_id).unwrap();
            let pack = project
                .database
                .load_writer_pack(&production.writer_pack_fingerprint)
                .unwrap();
            assert_eq!(
                pack.continuity_context.len(),
                ordinal.saturating_sub(1) as usize
            );
            let dependency_count: u32 = project.database.connection().query_row(
                "SELECT COUNT(*) FROM chapter_dependencies WHERE run_id=?1 AND status='current'",
                [&run_id],|row|row.get(0)
            ).unwrap();
            assert_eq!(dependency_count, ordinal.saturating_sub(1));
            let (project_revision, event_count, snapshot_count): (u64, u64, u64) = project
                .database
                .connection()
                .query_row(
                    "SELECT h.revision,(SELECT COUNT(*) FROM story_events e WHERE e.project_id=h.project_id), \
                     (SELECT COUNT(*) FROM story_state_snapshots s WHERE s.project_id=h.project_id) \
                     FROM project_state_heads h WHERE h.project_id='BOOK'",
                    [],
                    |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
                )
                .unwrap();
            assert_eq!(project_revision, u64::from(ordinal));
            assert_eq!(event_count, u64::from(ordinal));
            assert_eq!(snapshot_count, u64::from(ordinal));
        }
        let (candidate_id, candidate_fingerprint, document_id): (String, String, String) = {
            let project = runtime.open_registered("BOOK").unwrap();
            project.database.connection().query_row(
                "SELECT candidate_id,content_fingerprint,document_id FROM candidates WHERE run_id=?1",
                [&last_run_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))
            ).unwrap()
        };
        let observed=runtime.invoke_value(request(
            "learning.feedback.observe",
            json!({"project_id":"BOOK","event_id":"feedback-1","feedback_text":"Dialogue should remain embodied in speaker, space and reaction.",
                "evidence_kind":"correction","candidate_id":candidate_id,"candidate_fingerprint":candidate_fingerprint,
                "document_id":document_id,"run_id":last_run_id,"source_type":"author_feedback","source_id":"turn-1"})
        ));
        assert_eq!(observed["status"], "ok", "{observed}");
        let interpreted = runtime
            .invoke_value_async(request(
                "learning.feedback.execute",
                json!({"project_id":"BOOK","event_id":"feedback-1","service_id":service_id}),
            ))
            .await;
        assert_eq!(interpreted["status"], "ok", "{interpreted}");
        let hypothesis_id = interpreted["data"]["hypothesis_id"].as_str().unwrap();
        let reviewed=runtime.invoke_value_async(request(
            "learning.preference.review",
            json!({"project_id":"BOOK","hypothesis_id":hypothesis_id,"expected_version":1,"service_id":service_id})
        )).await;
        assert_eq!(reviewed["status"], "ok", "{reviewed}");
        let activated=runtime.invoke_value(request(
            "learning.preference.activate",
            json!({"project_id":"BOOK","hypothesis_id":hypothesis_id,"expected_version":0,
                "authorized_by":"author:local","idempotency_key":"activate-feedback-1","user_authorized":true})
        ));
        assert_eq!(activated["status"], "ok", "{activated}");
        assert_eq!(
            runtime
                .open_registered("BOOK")
                .unwrap()
                .database
                .active_writer_preference_candidates()
                .unwrap()
                .len(),
            1
        );
        let project = runtime.open_registered("BOOK").unwrap();
        for (table, expected) in [
            ("characters", 1_u64),
            ("character_knowledge", 1),
            ("timeline_events", 1),
            ("expectations", 1),
            ("narrative_state_sources", 3),
        ] {
            let count: u64 = project
                .database
                .connection()
                .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
                    row.get(0)
                })
                .unwrap();
            assert_eq!(count, expected, "unexpected {table} projection count");
        }
        drop(project);
        let collection = runtime.invoke_value(request(
            "publication.collection.build",
            json!({"project_id":"BOOK","acceptance_ids":acceptance_ids,"format":"txt",
                "idempotency_key":"three-chapter-collection","user_authorized":true}),
        ));
        assert_eq!(collection["status"], "ok", "{collection}");
        assert_eq!(
            collection["data"]["source_acceptance_ids"]
                .as_array()
                .unwrap()
                .len(),
            3
        );
        let (project_root, database_path) = {
            let project = runtime.open_registered("BOOK").unwrap();
            (
                project.context.project_root.clone(),
                project.context.data_root.join("project.sqlite"),
            )
        };
        server.abort();
        drop(runtime);
        let damaged = rusqlite::Connection::open(&database_path).unwrap();
        damaged
            .execute(
                "UPDATE characters SET state_json='{\"corrupted\":true}' WHERE character_id='CHAR-SHEN-YAN'",
                [],
            )
            .unwrap();
        drop(damaged);
        assert!(NativeProject::open(&project_root).is_err());
        let recovery_runtime =
            HostBridgeRuntime::open_with_secret_store(&root, Arc::new(MemorySecrets)).unwrap();
        let recovery = recovery_runtime.invoke_value(request(
            "project.story.restore_latest_snapshot",
            json!({"project_id":"BOOK","expected_revision":3,"user_authorized":true}),
        ));
        assert_eq!(recovery["status"], "ok", "{recovery}");
        assert_eq!(recovery["data"]["semantic_inference"], false);
        drop(recovery_runtime);
        let restored = NativeProject::open(&project_root).unwrap();
        let restored_state: String = restored
            .database
            .connection()
            .query_row(
                "SELECT state_json FROM characters WHERE character_id='CHAR-SHEN-YAN'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert!(!restored_state.contains("corrupted"));
        drop(restored);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn direct_bridge_creates_and_reopens_native_project_through_rust_core() {
        let root = root();
        let runtime = HostBridgeRuntime::open(&root).unwrap();
        let created = runtime.invoke_value(request(
            "project.create",
            json!({"project_id":"BOOK","title":"长篇"}),
        ));
        assert_eq!(created["status"], "ok");
        let chapter = runtime.invoke_value(request(
            "chapter.create",
            json!({
                "project_id":"BOOK","title":"Chapter Two","idempotency_key":"chapter-2",
                "user_authorized":true
            }),
        ));
        assert_eq!(chapter["status"], "ok", "{chapter}");
        assert_eq!(chapter["data"]["chapter_id"], "CH002");
        assert_eq!(chapter["data"]["replayed"], false);
        let replay = runtime.invoke_value(request(
            "chapter.create",
            json!({
                "project_id":"BOOK","title":"Chapter Two","idempotency_key":"chapter-2",
                "user_authorized":true
            }),
        ));
        assert_eq!(replay["status"], "ok");
        assert_eq!(replay["data"]["chapter_id"], "CH002");
        assert_eq!(replay["data"]["replayed"], true);
        let mismatch = runtime.invoke_value(request(
            "chapter.create",
            json!({
                "project_id":"BOOK","title":"Different Title","idempotency_key":"chapter-2",
                "user_authorized":true
            }),
        ));
        assert_eq!(mismatch["status"], "failed");
        let chapters = runtime.invoke_value(request("chapter.list", json!({"project_id":"BOOK"})));
        assert_eq!(chapters["status"], "ok");
        assert_eq!(chapters["data"]["items"].as_array().unwrap().len(), 2);
        let description = runtime.invoke_value(request("bridge.describe", json!({})));
        assert_eq!(description["status"], "ok");
        assert_eq!(
            description["data"]["operations"].as_array().unwrap().len(),
            IMPLEMENTED_OPERATIONS.len()
        );
        assert!(description["data"]["deferred_operations"]
            .as_object()
            .is_some_and(|operations| !operations.is_empty()));
        drop(runtime);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[tokio::test]
    async fn studio_plan_to_released_candidate_runs_entirely_through_rust() {
        let root = root();
        let (endpoint, server) = mock_model_service().await;
        let runtime =
            HostBridgeRuntime::open_with_secret_store(&root, Arc::new(MemorySecrets)).unwrap();
        assert_eq!(
            runtime.invoke_value(request(
                "project.create",
                json!({"project_id":"BOOK","title":"长篇"})
            ))["status"],
            "ok"
        );
        save_ancestor_plans(&runtime);
        let plan=runtime.invoke_value(request("plan.save",json!({
            "project_id":"BOOK","target_ref":"chapter:CH001","title":"第一章计划","content":"{\"scenes\":[]}","expected_version":0,
            "typed_body":{"kind":"chapter","body":{"reader_contract":{"reader_question":"他能否脱身？","visible_reward":"识破伏击",
                "character_choice":"主动进入险地","cost":"暴露行踪","net_change":"追兵锁定目标","next_pull":"死者为何现身"},
                "constraint_lock":{"length":{"min":2800,"max":3800,"unit":"chinese_characters"},
                    "must_happen":[{"id":"dead-person","statement":"主角主动入险后死者现身"}],"must_not_happen":[],
                    "exact_time_anchors":[],"stop_point":"死者现身时停笔","end_debt":"死者为何现身"},
                "scenes":[{"scene_id":"SC001","ordinal":1,"viewpoint":"沈砚","location":"雨巷","entry_state":"负伤被追",
                    "objective":"抵达接头点","opposition":"追兵封路","turn":"死者现身","exit_state":"被迫改道",
                    "emotion_target":"压迫转惊疑","reader_effect":"认可选择并追问死者身份"}]}},
            "reader_intent":{"reader_question":"他能否脱身？","visible_reward":"识破伏击","character_choice":"主动进入险地",
                "cost":"暴露行踪","net_change":"追兵锁定目标","next_chapter_pull":"死者为何现身"},
            "expectation_refs":[],"idempotency_key":"plan-1","user_authorized":true
        })));
        assert_eq!(plan["status"], "ok", "{plan}");
        let connected=runtime.invoke_value_async(request("model.service.add",json!({"endpoint":endpoint,
            "auth_style":"none","protocol_family":"openai_chat_completions","allow_loopback_http":true}))).await;
        assert_eq!(connected["status"], "ok", "{connected}");
        let service_id = connected
            .pointer("/data/service/service_id")
            .and_then(Value::as_str)
            .unwrap();
        let started=runtime.invoke_value(request("author.run.start",json!({"project_id":"BOOK","task_mode":"DRAFT",
            "target_ref":"DOC-CH001","payload":{"chapter_id":"CH001","author_profile":"balanced","instruction":"写出第一章",
                "reader_grip":"high","rule_material":[{"id":"request","authority":"current_request","statement":"写出第一章"}]},
            "idempotency_key":"run-1"})));
        assert_eq!(started["status"], "ok", "{started}");
        let run_id = started
            .pointer("/data/run_id")
            .and_then(Value::as_str)
            .unwrap();
        let executed = runtime
            .invoke_value_async(request(
                "author.run.execute",
                json!({"project_id":"BOOK","run_id":run_id,
            "service_id":service_id,"document_id":"DOC-CH001"}),
            ))
            .await;
        assert_eq!(executed["status"], "ok", "{executed}");
        assert_eq!(executed["data"]["candidate_visible"], true);
        assert_eq!(executed["data"]["raw_draft_visible"], false);
        let candidate_id = executed
            .pointer("/data/candidate_id")
            .and_then(Value::as_str)
            .unwrap();
        let visible = runtime.invoke_value(request(
            "candidate.visible.get",
            json!({"project_id":"BOOK","candidate_id":candidate_id}),
        ));
        assert_eq!(visible["status"], "ok", "{visible}");
        assert!(visible["data"]["content"]
            .as_str()
            .unwrap()
            .contains("雨砸在门板上"));
        let document = runtime.invoke_value(request(
            "document.open",
            json!({"project_id":"BOOK","document_id":"DOC-CH001"}),
        ));
        assert!(
            document["data"]["latest_revision"].is_null(),
            "unaccepted review draft leaked into document.open: {document}"
        );
        let failed_started=runtime.invoke_value(request("author.run.start",json!({"project_id":"BOOK","task_mode":"DRAFT",
            "target_ref":"DOC-CH001","payload":{"chapter_id":"CH001","author_profile":"balanced",
                "instruction":"force repair","reader_grip":"high","rule_material":[{"id":"repair-fixture",
                    "authority":"current_request","statement":"force repair"}]},"idempotency_key":"failed-run"})));
        assert_eq!(failed_started["status"], "ok", "{failed_started}");
        let failed_run = failed_started
            .pointer("/data/run_id")
            .and_then(Value::as_str)
            .unwrap();
        let failed = runtime
            .invoke_value_async(request(
                "author.run.execute",
                json!({"project_id":"BOOK","run_id":failed_run,
            "service_id":service_id,"document_id":"DOC-CH001"}),
            ))
            .await;
        assert_eq!(failed["status"], "ok", "{failed}");
        assert_eq!(failed["data"]["status"], "failed_gate", "{failed}");
        assert_eq!(failed["data"]["candidate_visible"], false);
        let repair_source = failed["data"]["repair_source"].clone();
        let revised_started=runtime.invoke_value(request("author.run.start",json!({"project_id":"BOOK","task_mode":"REVISE",
            "target_ref":"DOC-CH001","payload":{"chapter_id":"CH001","instruction":"修复因果链并保留人物主动性",
                "reader_grip":"high","author_profile":"balanced","repair_source":repair_source},
            "idempotency_key":"revise-run"})));
        assert_eq!(revised_started["status"], "ok", "{revised_started}");
        let revised_run = revised_started
            .pointer("/data/run_id")
            .and_then(Value::as_str)
            .unwrap();
        let revised = runtime
            .invoke_value_async(request(
                "author.run.execute",
                json!({"project_id":"BOOK","run_id":revised_run,
            "service_id":service_id,"document_id":"DOC-CH001"}),
            ))
            .await;
        assert_eq!(revised["status"], "ok", "{revised}");
        assert_eq!(revised["data"]["candidate_visible"], true, "{revised}");
        let revised_status = runtime.invoke_value(request(
            "author.run.status",
            json!({"project_id":"BOOK","run_id":revised_run}),
        ));
        let stages = revised_status
            .pointer("/data/execution_journal/calls")
            .and_then(Value::as_array)
            .unwrap()
            .iter()
            .filter_map(|call| call.get("stage_key").and_then(Value::as_str))
            .collect::<BTreeSet<_>>();
        assert!(stages.contains("repair_editor"));
        assert!(stages.contains("repair_comparison"));
        server.abort();
        drop(runtime);
        std::fs::remove_dir_all(root).unwrap();
    }
}
