use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::time::Duration;

use quillframe_native::{
    atomic_write_new, guard_directory, guard_file, FileMode, QfNativeGuard, QfNativeLock,
};
use rusqlite::{
    params, Connection, OpenFlags, OptionalExtension, Transaction, TransactionBehavior,
};

use crate::{
    apply_fresh_project_schema, validate_current_project_schema, AcceptanceDecision, AnalyzeStage,
    AuthorActivation, BookSetupApprovalReceipt, BookSetupArtifact, BookSetupProposalReceipt,
    CandidateArtifact, ContextEntry, ContextFreeze, ContextManifest, ContextQueryPlan,
    ContextSelectionProposal, ContextStage, ContextTier, CoreError, CoreResult, CorpusProgress,
    ExpectationDeltaAction, FrozenPlanLayer, HierarchicalPlanLock, ModelResult,
    NarrativeEntityKind, PlanProposal, ProductionRelease, ProductionRequest, ProductionTaskMode,
    ProjectContext, ProjectManifest, ReviewReport, RevisionRequest, SettlementAuthorization,
    SettlementPreflight, SourceFreeCorpusPack, StageCall, StageCallState, StageJob, StoryEvent,
    StoryGraph, StoryKind, StoryNode, StoryStateSnapshot, SurfaceRealization, TrackingState,
    WriterContinuityEntry, WriterPack,
};

pub struct NativeProject {
    pub context: ProjectContext,
    pub database: ProjectDatabase,
    _root_guard: QfNativeGuard,
    _manifest_guard: QfNativeGuard,
    _data_guard: QfNativeGuard,
}

impl NativeProject {
    pub fn create(root: &Path, manifest: ProjectManifest, created_at: &str) -> CoreResult<Self> {
        manifest.validate()?;
        require_timestamp(created_at)?;
        let root_guard = guard_directory(root, true).map_err(native_error)?;
        let manifest_bytes = manifest.to_toml_bytes()?;
        let manifest_guard = atomic_write_new(&root.join("quillframe.toml"), &manifest_bytes)
            .map_err(native_error)?;
        let context = ProjectManifest::resolve(root, &manifest_bytes)?;
        let data_guard = guard_directory(&context.data_root, true).map_err(native_error)?;
        let database = ProjectDatabase::create_reserved(
            &context.data_root.join("project.sqlite"),
            &manifest,
            created_at,
        )?;
        root_guard.revalidate().map_err(native_error)?;
        manifest_guard.revalidate().map_err(native_error)?;
        data_guard.revalidate().map_err(native_error)?;
        Ok(Self {
            context,
            database,
            _root_guard: root_guard,
            _manifest_guard: manifest_guard,
            _data_guard: data_guard,
        })
    }

    pub fn open(root: &Path) -> CoreResult<Self> {
        let root_guard = guard_directory(root, false).map_err(native_error)?;
        let manifest_path = root.join("quillframe.toml");
        let manifest_guard =
            guard_file(&manifest_path, FileMode::OpenRead, true).map_err(native_error)?;
        manifest_guard.revalidate().map_err(native_error)?;
        let manifest_bytes = std::fs::read(&manifest_path)
            .map_err(|error| CoreError::Storage(format!("manifest read failed: {error}")))?;
        manifest_guard.revalidate().map_err(native_error)?;
        let context = ProjectManifest::resolve(root, &manifest_bytes)?;
        let data_guard = guard_directory(&context.data_root, false).map_err(native_error)?;
        let database = ProjectDatabase::open_strict(
            &context.data_root.join("project.sqlite"),
            &context.manifest,
        )?;
        root_guard.revalidate().map_err(native_error)?;
        data_guard.revalidate().map_err(native_error)?;
        Ok(Self {
            context,
            database,
            _root_guard: root_guard,
            _manifest_guard: manifest_guard,
            _data_guard: data_guard,
        })
    }
}

pub struct ProjectDatabase {
    connection: Connection,
    _database_guard: QfNativeGuard,
    _lock: QfNativeLock,
    path: PathBuf,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChapterCreationReceipt {
    pub chapter_id: String,
    pub document_id: String,
    pub unit_id: String,
    pub ordinal: u32,
    pub title: String,
    pub request_fingerprint: String,
    pub replayed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StoryNodeCreationReceipt {
    pub node_id: String,
    pub parent_id: String,
    pub kind: StoryKind,
    pub ordinal: u32,
    pub title: String,
    pub request_fingerprint: String,
    pub replayed: bool,
}

impl ProjectDatabase {
    /// Re-materialize deterministic story projections from the latest committed snapshot.
    ///
    /// This is an explicit recovery operation: normal open remains strict and never repairs
    /// state. The snapshot and event-chain fingerprints must still match the caller's expected
    /// revision before any projection table is replaced.
    pub fn restore_latest_story_snapshot(
        database_path: &Path,
        manifest: &ProjectManifest,
        expected_revision: u64,
    ) -> CoreResult<String> {
        require_handle_bound_sqlite()?;
        manifest.validate()?;
        let parent = database_path
            .parent()
            .ok_or_else(|| CoreError::Storage("project database requires a parent".into()))?;
        let _lock =
            QfNativeLock::try_acquire(&parent.join(".project.lock")).map_err(native_error)?;
        let database_guard =
            guard_file(database_path, FileMode::OpenReadWrite, true).map_err(native_error)?;
        let mut connection = open_connection(database_path)?;
        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        validate_current_project_schema(&transaction)?;
        validate_project_identity(&transaction, manifest)?;
        validate_novel_topology(&transaction)?;
        let (revision, latest_event_seq, snapshot_id, head_fingerprint): (
            u64,
            Option<i64>,
            Option<String>,
            String,
        ) = transaction
            .query_row(
                "SELECT revision,latest_event_seq,latest_snapshot_id,state_fingerprint \
                 FROM project_state_heads WHERE project_id=?1",
                [&manifest.id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .map_err(storage_error)?;
        if revision != expected_revision || revision == 0 {
            return Err(CoreError::AuthorityConflict(
                "story snapshot recovery revision is stale or has no committed state".into(),
            ));
        }
        let snapshot_id = snapshot_id.ok_or_else(|| {
            CoreError::AuthorityConflict("committed story head has no recovery snapshot".into())
        })?;
        let payload: String = transaction
            .query_row(
                "SELECT payload_json FROM story_state_snapshots \
                 WHERE snapshot_id=?1 AND project_id=?2 AND through_event_seq=?3",
                params![snapshot_id, manifest.id, latest_event_seq],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let snapshot: StoryStateSnapshot = serde_json::from_str(&payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        snapshot.validate()?;
        if snapshot.project_id != manifest.id
            || snapshot.through_revision != revision
            || Some(snapshot.through_event_seq) != latest_event_seq
            || snapshot.event_chain_fingerprint != head_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "story snapshot recovery binding does not match the committed head".into(),
            ));
        }
        materialize_story_projection(&transaction, &payload)?;
        verify_story_history(&transaction)?;
        database_guard.revalidate().map_err(native_error)?;
        transaction.commit().map_err(storage_error)?;
        database_guard.revalidate().map_err(native_error)?;
        Ok(snapshot_id)
    }

    pub fn create_reserved(
        database_path: &Path,
        manifest: &ProjectManifest,
        created_at: &str,
    ) -> CoreResult<Self> {
        require_handle_bound_sqlite()?;
        manifest.validate()?;
        require_timestamp(created_at)?;
        let parent = database_path
            .parent()
            .ok_or_else(|| CoreError::Storage("project database requires a parent".into()))?;
        let lock =
            QfNativeLock::try_acquire(&parent.join(".project.lock")).map_err(native_error)?;
        let database_guard =
            guard_file(database_path, FileMode::CreateNew, true).map_err(native_error)?;
        let mut connection = open_connection(database_path)?;
        connection
            .pragma_update(None, "journal_mode", "WAL")
            .map_err(storage_error)?;
        connection
            .pragma_update(None, "synchronous", "FULL")
            .map_err(storage_error)?;
        apply_fresh_project_schema(&mut connection, created_at)?;

        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        insert_initial_project(&transaction, manifest, created_at)?;
        validate_project_identity(&transaction, manifest)?;
        validate_novel_topology(&transaction)?;
        verify_story_history(&transaction)?;
        database_guard.revalidate().map_err(native_error)?;
        transaction.commit().map_err(storage_error)?;
        validate_current_project_schema(&connection)?;
        database_guard.revalidate().map_err(native_error)?;
        Ok(Self {
            connection,
            _database_guard: database_guard,
            _lock: lock,
            path: database_path.to_path_buf(),
        })
    }

    pub fn open_strict(database_path: &Path, manifest: &ProjectManifest) -> CoreResult<Self> {
        require_handle_bound_sqlite()?;
        manifest.validate()?;
        let parent = database_path
            .parent()
            .ok_or_else(|| CoreError::Storage("project database requires a parent".into()))?;
        let lock =
            QfNativeLock::try_acquire(&parent.join(".project.lock")).map_err(native_error)?;
        let database_guard =
            guard_file(database_path, FileMode::OpenReadWrite, true).map_err(native_error)?;
        let mut connection = open_connection(database_path)?;
        let transaction = connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        validate_current_project_schema(&transaction)?;
        validate_project_identity(&transaction, manifest)?;
        validate_novel_topology(&transaction)?;
        verify_story_history(&transaction)?;
        database_guard.revalidate().map_err(native_error)?;
        transaction.commit().map_err(storage_error)?;
        database_guard.revalidate().map_err(native_error)?;
        Ok(Self {
            connection,
            _database_guard: database_guard,
            _lock: lock,
            path: database_path.to_path_buf(),
        })
    }

    pub fn connection(&self) -> &Connection {
        &self.connection
    }

    pub fn load_story_graph(&self) -> CoreResult<StoryGraph> {
        let mut statement = self.connection.prepare(
            "SELECT n.node_id,n.parent_id,n.kind,n.ordinal,n.title, \
             (SELECT d.document_id FROM documents d WHERE d.story_node_id=n.node_id AND d.document_kind='manuscript') \
             FROM story_nodes n ORDER BY CASE n.kind WHEN 'book' THEN 1 WHEN 'volume' THEN 2 \
             WHEN 'unit' THEN 3 WHEN 'chapter' THEN 4 WHEN 'scene' THEN 5 END,n.ordinal,n.node_id"
        ).map_err(storage_error)?;
        let nodes = statement
            .query_map([], |row| {
                let kind: String = row.get(2)?;
                Ok(StoryNode {
                    id: row.get(0)?,
                    parent_id: row.get(1)?,
                    kind: match kind.as_str() {
                        "book" => StoryKind::Book,
                        "volume" => StoryKind::Volume,
                        "unit" => StoryKind::Unit,
                        "chapter" => StoryKind::Chapter,
                        _ => StoryKind::Scene,
                    },
                    ordinal: row.get(3)?,
                    title: row.get(4)?,
                    manuscript_id: row.get(5)?,
                })
            })
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        let mut graph = StoryGraph::default();
        for node in nodes {
            graph.insert(node)?;
        }
        Ok(graph)
    }

    pub fn create_chapter(
        &mut self,
        project_id: &str,
        requested_unit_id: Option<&str>,
        title: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> CoreResult<ChapterCreationReceipt> {
        require_timestamp(created_at)?;
        if title.trim().is_empty() || title != title.trim() {
            return Err(CoreError::InvalidHierarchy(
                "chapter title must be non-empty and trimmed".into(),
            ));
        }
        if idempotency_key.trim().is_empty() || idempotency_key != idempotency_key.trim() {
            return Err(CoreError::AuthorityConflict(
                "chapter idempotency key must be non-empty and trimmed".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let stored_project: String = transaction
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        if stored_project != project_id {
            return Err(CoreError::AuthorityConflict(
                "chapter project binding does not match the database".into(),
            ));
        }
        let existing = transaction
            .query_row(
                "SELECT chapter_id,document_id,unit_id,ordinal,title,request_fingerprint \
                 FROM chapter_creation_receipts WHERE idempotency_key=?1",
                [idempotency_key],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, u32>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, String>(5)?,
                    ))
                },
            )
            .optional()
            .map_err(storage_error)?;
        if let Some((chapter_id, document_id, unit_id, ordinal, stored_title, fingerprint)) =
            existing
        {
            let expected = crate::fingerprint::sha256_fingerprint(
                serde_json::to_vec(&serde_json::json!({
                    "project_id": project_id,
                    "unit_id": unit_id,
                    "title": title
                }))
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
            );
            if stored_title != title
                || requested_unit_id.is_some_and(|requested| requested != unit_id)
                || fingerprint != expected
            {
                return Err(CoreError::AuthorityConflict(
                    "chapter idempotency key is bound to different input".into(),
                ));
            }
            transaction.commit().map_err(storage_error)?;
            return Ok(ChapterCreationReceipt {
                chapter_id,
                document_id,
                unit_id,
                ordinal,
                title: stored_title,
                request_fingerprint: fingerprint,
                replayed: true,
            });
        }
        let unit_id = if let Some(unit_id) = requested_unit_id {
            let kind: Option<String> = transaction
                .query_row(
                    "SELECT kind FROM story_nodes WHERE node_id=?1",
                    [unit_id],
                    |row| row.get(0),
                )
                .optional()
                .map_err(storage_error)?;
            if kind.as_deref() != Some("unit") {
                return Err(CoreError::InvalidHierarchy(
                    "chapter parent must be an existing unit".into(),
                ));
            }
            unit_id.to_owned()
        } else {
            transaction
                .query_row(
                    "SELECT u.node_id FROM story_nodes u \
                     JOIN story_nodes v ON v.node_id=u.parent_id AND v.kind='volume' \
                     WHERE u.kind='unit' ORDER BY v.ordinal DESC,u.ordinal DESC,u.node_id DESC LIMIT 1",
                    [],
                    |row| row.get::<_, String>(0),
                )
                .map_err(storage_error)?
        };
        let next_id: u32 = transaction
            .query_row(
                "SELECT COALESCE(MAX(CASE WHEN node_id GLOB 'CH[0-9]*' THEN CAST(SUBSTR(node_id,3) AS INTEGER) END),0)+1 \
                 FROM story_nodes WHERE kind='chapter'",
                [],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let ordinal: u32 = transaction
            .query_row(
                "SELECT COALESCE(MAX(ordinal),0)+1 FROM story_nodes WHERE parent_id=?1 AND kind='chapter'",
                [&unit_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let chapter_id = format!("CH{next_id:03}");
        let document_id = format!("DOC-{chapter_id}");
        let request_fingerprint = crate::fingerprint::sha256_fingerprint(
            serde_json::to_vec(&serde_json::json!({
                "project_id": project_id,
                "unit_id": unit_id,
                "title": title
            }))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        transaction
            .execute(
                "INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title,metadata_json) \
                 VALUES(?1,?2,'chapter',?3,?4,'{}')",
                params![chapter_id, unit_id, ordinal, title],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) \
                 VALUES(?1,?2,'manuscript',?3,?4)",
                params![document_id, chapter_id, title, created_at],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO search_index(entity_type,entity_id,title,body) \
                 VALUES('document',?1,?2,'')",
                params![document_id, title],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO chapter_creation_receipts( \
                 idempotency_key,project_id,unit_id,chapter_id,document_id,ordinal,title,request_fingerprint,created_at \
                 ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)",
                params![
                    idempotency_key,
                    project_id,
                    unit_id,
                    chapter_id,
                    document_id,
                    ordinal,
                    title,
                    request_fingerprint,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        validate_novel_topology(&transaction)?;
        transaction.commit().map_err(storage_error)?;
        Ok(ChapterCreationReceipt {
            chapter_id,
            document_id,
            unit_id,
            ordinal,
            title: title.to_owned(),
            request_fingerprint,
            replayed: false,
        })
    }

    pub fn create_story_container(
        &mut self,
        project_id: &str,
        kind: StoryKind,
        requested_parent_id: Option<&str>,
        title: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> CoreResult<StoryNodeCreationReceipt> {
        require_timestamp(created_at)?;
        let (kind_name, parent_kind, id_prefix, default_parent_query) = match kind {
            StoryKind::Volume => (
                "volume",
                "book",
                "VOL",
                "SELECT node_id FROM story_nodes WHERE kind='book' LIMIT 1",
            ),
            StoryKind::Unit => (
                "unit",
                "volume",
                "UNIT",
                "SELECT node_id FROM story_nodes WHERE kind='volume' ORDER BY ordinal DESC,node_id DESC LIMIT 1",
            ),
            _ => {
                return Err(CoreError::InvalidHierarchy(
                    "story container creation only supports volume or unit".into(),
                ))
            }
        };
        if title.trim().is_empty() || title != title.trim() {
            return Err(CoreError::InvalidHierarchy(format!(
                "{kind_name} title must be non-empty and trimmed"
            )));
        }
        require_idempotency_key(idempotency_key)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let stored_project: String = transaction
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        if stored_project != project_id {
            return Err(CoreError::AuthorityConflict(
                "story container project binding does not match the database".into(),
            ));
        }

        let existing: Option<(String, String)> = transaction
            .query_row(
                "SELECT receipt_kind,payload_json FROM receipts WHERE idempotency_key=?1",
                [idempotency_key],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .optional()
            .map_err(storage_error)?;
        if let Some((receipt_kind, payload)) = existing {
            if receipt_kind != "story_container_created" {
                return Err(CoreError::AuthorityConflict(
                    "story container idempotency key is already bound to another operation".into(),
                ));
            }
            let value: serde_json::Value = serde_json::from_str(&payload)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let stored_kind = value["kind"].as_str().unwrap_or_default();
            let stored_parent = value["parent_id"].as_str().unwrap_or_default();
            let stored_title = value["title"].as_str().unwrap_or_default();
            let stored_project_id = value["project_id"].as_str().unwrap_or_default();
            let expected_parent = requested_parent_id.unwrap_or(stored_parent);
            let expected_fingerprint =
                story_container_request_fingerprint(project_id, kind_name, expected_parent, title)?;
            if stored_project_id != project_id
                || stored_kind != kind_name
                || stored_parent != expected_parent
                || stored_title != title
                || value["request_fingerprint"].as_str() != Some(expected_fingerprint.as_str())
            {
                return Err(CoreError::AuthorityConflict(
                    "story container idempotency key is bound to different input".into(),
                ));
            }
            let ordinal = u32::try_from(value["ordinal"].as_u64().unwrap_or_default())
                .map_err(|_| CoreError::Storage("story container ordinal overflow".into()))?;
            transaction.commit().map_err(storage_error)?;
            return Ok(StoryNodeCreationReceipt {
                node_id: value["node_id"].as_str().unwrap_or_default().into(),
                parent_id: stored_parent.into(),
                kind,
                ordinal,
                title: stored_title.into(),
                request_fingerprint: expected_fingerprint,
                replayed: true,
            });
        }

        let parent_id = if let Some(parent_id) = requested_parent_id {
            let stored_kind: Option<String> = transaction
                .query_row(
                    "SELECT kind FROM story_nodes WHERE node_id=?1",
                    [parent_id],
                    |row| row.get(0),
                )
                .optional()
                .map_err(storage_error)?;
            if stored_kind.as_deref() != Some(parent_kind) {
                return Err(CoreError::InvalidHierarchy(format!(
                    "{kind_name} parent must be an existing {parent_kind}"
                )));
            }
            parent_id.to_owned()
        } else {
            transaction
                .query_row(default_parent_query, [], |row| row.get::<_, String>(0))
                .map_err(storage_error)?
        };
        let prefix_len = id_prefix.len() + 1;
        let next_id: u32 = transaction
            .query_row(
                &format!(
                    "SELECT COALESCE(MAX(CASE WHEN node_id GLOB '{id_prefix}[0-9]*' THEN CAST(SUBSTR(node_id,{prefix_len}) AS INTEGER) END),0)+1 FROM story_nodes WHERE kind=?1"
                ),
                [kind_name],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let ordinal: u32 = transaction
            .query_row(
                "SELECT COALESCE(MAX(ordinal),0)+1 FROM story_nodes WHERE parent_id=?1 AND kind=?2",
                params![parent_id, kind_name],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let node_id = format!("{id_prefix}{next_id:03}");
        let request_fingerprint =
            story_container_request_fingerprint(project_id, kind_name, &parent_id, title)?;
        transaction
            .execute(
                "INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title,metadata_json) VALUES(?1,?2,?3,?4,?5,'{}')",
                params![node_id, parent_id, kind_name, ordinal, title],
            )
            .map_err(storage_error)?;
        let payload = serde_json::to_string(&serde_json::json!({
            "schema":"quillframe_story_container_create_receipt_v1",
            "project_id":project_id,
            "kind":kind_name,
            "node_id":node_id,
            "parent_id":parent_id,
            "ordinal":ordinal,
            "title":title,
            "request_fingerprint":request_fingerprint,
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?1,'story_container_created',?2,?3,?4)",
                params![format!("receipt-{}", uuid::Uuid::new_v4()), idempotency_key, payload, created_at],
            )
            .map_err(storage_error)?;
        validate_novel_topology(&transaction)?;
        transaction.commit().map_err(storage_error)?;
        Ok(StoryNodeCreationReceipt {
            node_id,
            parent_id,
            kind,
            ordinal,
            title: title.into(),
            request_fingerprint,
            replayed: false,
        })
    }

    pub fn connection_mut(&mut self) -> &mut Connection {
        &mut self.connection
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn save_tracking_state(
        &mut self,
        state: &TrackingState,
        expected_version: Option<u64>,
        updated_at: &str,
    ) -> CoreResult<()> {
        state.validate()?;
        require_timestamp(updated_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let current = transaction
            .query_row(
                "SELECT version FROM story_tracking_authority WHERE project_id=?1",
                [&state.project_id],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?;
        if current != expected_version {
            return Err(CoreError::AuthorityConflict(
                "tracking persistence compare-and-swap conflict".into(),
            ));
        }
        let payload = serde_json::to_string(state)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO story_tracking_authority( \
                 project_id,version,payload_json,content_fingerprint,updated_at \
                 ) VALUES(?1,?2,?3,?4,?5) \
                 ON CONFLICT(project_id) DO UPDATE SET \
                 version=excluded.version,payload_json=excluded.payload_json, \
                 content_fingerprint=excluded.content_fingerprint,updated_at=excluded.updated_at",
                params![
                    state.project_id,
                    state.version,
                    payload,
                    state.fingerprint,
                    updated_at
                ],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)
    }

    pub fn save_plan_proposal(
        &mut self,
        proposal: &PlanProposal,
        created_at: &str,
    ) -> CoreResult<()> {
        proposal.validate_fingerprint()?;
        require_timestamp(created_at)?;
        let payload = serde_json::to_string(proposal)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let plan_id = proposal.id.to_string();
        let mode = match proposal.mode {
            crate::PlanMode::DesignBook => "DESIGN-BOOK",
            crate::PlanMode::DesignVolume => "DESIGN-VOLUME",
            crate::PlanMode::PlanUnit => "PLAN-UNIT",
            crate::PlanMode::PlanChapter => "PLAN-CHAPTER",
        };
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO plans( \
                 plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at \
                 ) VALUES(?1,?2,?3,'proposal',?4,?5,?6,?6)",
                params![plan_id, mode, proposal.target.node_id, payload, proposal.fingerprint, created_at],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO plan_versions(plan_id,version,payload_json,content_fingerprint,created_at) \
                 VALUES(?1,1,?2,?3,?4)",
                params![plan_id, payload, proposal.fingerprint, created_at],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)
    }

    pub fn active_ancestor_fingerprints(
        &self,
        node_id: &str,
    ) -> CoreResult<BTreeMap<String, String>> {
        let graph = self.load_story_graph()?;
        let mut bindings = BTreeMap::new();
        for ancestor in graph.ancestors(node_id)? {
            if ancestor.kind == StoryKind::Scene {
                continue;
            }
            let target_ref = graph.canonical_target(&ancestor.id)?;
            let fingerprint = self
                .connection
                .query_row(
                    "SELECT proposal_fingerprint FROM plan_activations \
                     WHERE target_ref=?1 AND status='active'",
                    [&target_ref],
                    |row| row.get::<_, String>(0),
                )
                .optional()
                .map_err(storage_error)?
                .ok_or_else(|| {
                    CoreError::AuthorityConflict(format!(
                        "active ancestor plan {target_ref} is required"
                    ))
                })?;
            bindings.insert(target_ref, fingerprint);
        }
        Ok(bindings)
    }

    pub fn activate_plan(&mut self, authorization: &AuthorActivation) -> CoreResult<u64> {
        authorization.validate()?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let plan_id = authorization.proposal_id.to_string();
        let proposal_json = transaction
            .query_row(
                "SELECT plan_json FROM plans WHERE plan_id=?1",
                [&plan_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| CoreError::AuthorityConflict("plan proposal is unavailable".into()))?;
        let proposal: PlanProposal = serde_json::from_str(&proposal_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        proposal.validate_fingerprint()?;
        validate_plan_dependencies_in_transaction(&transaction, &proposal)?;
        if proposal.fingerprint != authorization.proposal_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "authorization does not bind the persisted proposal".into(),
            ));
        }
        if let Some(version) = transaction
            .query_row(
                "SELECT active_version FROM plan_activations WHERE authorization_fingerprint=?1",
                [&authorization.fingerprint],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            return Ok(version);
        }
        let current_version = transaction
            .query_row(
                "SELECT active_version FROM plan_activations \
                 WHERE target_ref=?1 AND status='active'",
                [&proposal.target.reference],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
            .unwrap_or(0);
        if current_version != authorization.expected_active_version {
            return Err(CoreError::AuthorityConflict(
                "persisted active plan version changed".into(),
            ));
        }
        transaction
            .execute(
                "UPDATE plan_activations SET status='superseded' \
                 WHERE target_ref=?1 AND status='active'",
                [&proposal.target.reference],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE plans SET status='superseded',updated_at=?2 \
                 WHERE target_id=?1 AND status='active'",
                params![proposal.target.node_id, authorization.decided_at],
            )
            .map_err(storage_error)?;
        let active_version = current_version + 1;
        let authorization_json = serde_json::to_string(authorization)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO plan_activations( \
                 activation_id,proposal_id,target_ref,active_version,proposal_fingerprint, \
                 authorization_fingerprint,authorization_json,status,created_at \
                 ) VALUES(?1,?2,?3,?4,?5,?6,?7,'active',?8)",
                params![
                    authorization.decision_id.to_string(),
                    plan_id,
                    proposal.target.reference,
                    active_version,
                    proposal.fingerprint,
                    authorization.fingerprint,
                    authorization_json,
                    authorization.decided_at
                ],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE plans SET status='active',updated_at=?2 WHERE plan_id=?1",
                params![plan_id, authorization.decided_at],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(active_version)
    }

    pub fn save_and_activate_editor_plan(
        &mut self,
        proposal: &PlanProposal,
        authorization: &AuthorActivation,
        title: &str,
        content: &str,
        reader_intent: &serde_json::Value,
        expectation_refs: &[String],
    ) -> CoreResult<u64> {
        proposal.validate_fingerprint()?;
        authorization.validate()?;
        if authorization.proposal_id != proposal.id
            || authorization.proposal_fingerprint != proposal.fingerprint
            || title.trim().is_empty()
            || !reader_intent.is_object()
            || expectation_refs.iter().any(|value| value.trim().is_empty())
        {
            return Err(CoreError::AuthorityConflict(
                "editor plan activation binding is incomplete".into(),
            ));
        }
        let plan_id = proposal.id.to_string();
        let mode = match proposal.mode {
            crate::PlanMode::DesignBook => "DESIGN-BOOK",
            crate::PlanMode::DesignVolume => "DESIGN-VOLUME",
            crate::PlanMode::PlanUnit => "PLAN-UNIT",
            crate::PlanMode::PlanChapter => "PLAN-CHAPTER",
        };
        let plan_json = serde_json::to_string(proposal)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let authorization_json = serde_json::to_string(authorization)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let reader_intent_json = serde_json::to_string(reader_intent)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let expectation_refs_json = serde_json::to_string(expectation_refs)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        validate_plan_dependencies_in_transaction(&transaction, proposal)?;
        if let Some((version, existing_fingerprint)) = transaction
            .query_row(
                "SELECT active_version,proposal_fingerprint FROM plan_activations \
                 WHERE authorization_fingerprint=?1",
                [&authorization.fingerprint],
                |row| Ok((row.get::<_, u64>(0)?, row.get::<_, String>(1)?)),
            )
            .optional()
            .map_err(storage_error)?
        {
            if existing_fingerprint == proposal.fingerprint {
                return Ok(version);
            }
            return Err(CoreError::AuthorityConflict(
                "plan activation idempotency binding changed".into(),
            ));
        }
        let current_version = transaction
            .query_row(
                "SELECT active_version FROM plan_activations WHERE target_ref=?1 AND status='active'",
                [&proposal.target.reference],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
            .unwrap_or(0);
        if current_version != proposal.expected_active_version
            || current_version != authorization.expected_active_version
        {
            return Err(CoreError::AuthorityConflict(
                "active plan version changed".into(),
            ));
        }
        transaction.execute(
            "INSERT INTO plans(plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at) \
             VALUES(?1,?2,?3,'proposal',?4,?5,?6,?6)",
            params![plan_id,mode,proposal.target.node_id,plan_json,proposal.fingerprint,authorization.decided_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO plan_versions(plan_id,version,payload_json,content_fingerprint,created_at) VALUES(?1,1,?2,?3,?4)",
            params![plan_id,plan_json,proposal.fingerprint,authorization.decided_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO plan_editor_views(proposal_id,target_ref,title,content,reader_intent_json,expectation_refs_json,created_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7)",
            params![plan_id,proposal.target.reference,title,content,reader_intent_json,expectation_refs_json,authorization.decided_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE plan_activations SET status='superseded' WHERE target_ref=?1 AND status='active'",
            [&proposal.target.reference],
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE plans SET status='superseded',updated_at=?2 WHERE target_id=?1 AND status='active'",
            params![proposal.target.node_id,authorization.decided_at],
        ).map_err(storage_error)?;
        let active_version = current_version + 1;
        transaction.execute(
            "INSERT INTO plan_activations(activation_id,proposal_id,target_ref,active_version,proposal_fingerprint,authorization_fingerprint,authorization_json,status,created_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,'active',?8)",
            params![authorization.decision_id.to_string(),plan_id,proposal.target.reference,active_version,proposal.fingerprint,
                authorization.fingerprint,authorization_json,authorization.decided_at],
        ).map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE plans SET status='active',updated_at=?2 WHERE plan_id=?1",
                params![plan_id, authorization.decided_at],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(active_version)
    }

    pub fn propose_book_setup(
        &mut self,
        artifact: &BookSetupArtifact,
        expected_setup_version: u64,
        idempotency_key: &str,
        created_at: &str,
    ) -> CoreResult<BookSetupProposalReceipt> {
        artifact.validate()?;
        require_timestamp(created_at)?;
        require_idempotency_key(idempotency_key)?;
        let request_fingerprint = crate::fingerprint::sha256_fingerprint(
            serde_json::to_vec(&serde_json::json!({
                "project_id": artifact.project_id,
                "expected_setup_version": expected_setup_version,
                "setup_fingerprint": artifact.fingerprint
            }))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let setup_json = serde_json::to_string(artifact)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let stored_project: String = transaction
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        if stored_project != artifact.project_id {
            return Err(CoreError::AuthorityConflict(
                "book setup project binding does not match the database".into(),
            ));
        }
        if let Some((setup_id, stored_request, setup_fingerprint, expected_book_plan_version)) =
            transaction
                .query_row(
                    "SELECT setup_id,request_fingerprint,setup_fingerprint,expected_book_plan_version \
                     FROM book_setup_proposals WHERE idempotency_key=?1",
                    [idempotency_key],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, String>(1)?,
                            row.get::<_, String>(2)?,
                            row.get::<_, u64>(3)?,
                        ))
                    },
                )
                .optional()
                .map_err(storage_error)?
        {
            if stored_request != request_fingerprint || setup_fingerprint != artifact.fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "book setup idempotency key binds different input".into(),
                ));
            }
            return Ok(BookSetupProposalReceipt {
                setup_id,
                expected_setup_version,
                expected_book_plan_version,
                setup_fingerprint,
                request_fingerprint,
                replayed: true,
            });
        }
        let current_setup_version = transaction
            .query_row(
                "SELECT version FROM book_setup_heads WHERE project_id=?1",
                [&artifact.project_id],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
            .unwrap_or(0);
        if current_setup_version != expected_setup_version {
            return Err(CoreError::AuthorityConflict(
                "book setup version changed".into(),
            ));
        }
        let expected_book_plan_version = transaction
            .query_row(
                "SELECT active_version FROM plan_activations \
                 WHERE target_ref='book:BOOK' AND status='active'",
                [],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
            .unwrap_or(0);
        let setup_id = format!("setup-{}", uuid::Uuid::new_v4().simple());
        transaction
            .execute(
                "INSERT INTO book_setup_proposals( \
                 setup_id,project_id,expected_setup_version,expected_book_plan_version,status, \
                 setup_json,setup_fingerprint,request_fingerprint,idempotency_key,created_at \
                 ) VALUES(?1,?2,?3,?4,'proposal_ready',?5,?6,?7,?8,?9)",
                params![
                    setup_id,
                    artifact.project_id,
                    expected_setup_version,
                    expected_book_plan_version,
                    setup_json,
                    artifact.fingerprint,
                    request_fingerprint,
                    idempotency_key,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(BookSetupProposalReceipt {
            setup_id,
            expected_setup_version,
            expected_book_plan_version,
            setup_fingerprint: artifact.fingerprint.clone(),
            request_fingerprint,
            replayed: false,
        })
    }

    pub fn load_book_setup_proposal(
        &self,
        setup_id: &str,
    ) -> CoreResult<(BookSetupArtifact, u64, u64, String, String)> {
        let (payload, expected_setup_version, expected_book_plan_version, status, created_at): (
            String,
            u64,
            u64,
            String,
            String,
        ) = self
            .connection
            .query_row(
                "SELECT setup_json,expected_setup_version,expected_book_plan_version,status,created_at \
                 FROM book_setup_proposals WHERE setup_id=?1",
                [setup_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .map_err(storage_error)?;
        let artifact: BookSetupArtifact = serde_json::from_str(&payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        artifact.validate()?;
        Ok((
            artifact,
            expected_setup_version,
            expected_book_plan_version,
            status,
            created_at,
        ))
    }

    #[allow(clippy::too_many_arguments)]
    pub fn approve_book_setup(
        &mut self,
        setup_id: &str,
        expected_setup_version: u64,
        book_plan_id: &str,
        book_plan_fingerprint: &str,
        authorized_by: &str,
        idempotency_key: &str,
        created_at: &str,
    ) -> CoreResult<BookSetupApprovalReceipt> {
        require_timestamp(created_at)?;
        require_idempotency_key(idempotency_key)?;
        if authorized_by.trim().is_empty() || authorized_by != authorized_by.trim() {
            return Err(CoreError::AuthorityConflict(
                "book setup approver must be non-empty and trimmed".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((stored_setup_id, version, setup_fingerprint, stored_plan_id, stored_plan_fingerprint, approval_fingerprint, stored_author)) = transaction
            .query_row(
                "SELECT a.setup_id,h.version,h.setup_fingerprint,a.book_plan_id,a.book_plan_fingerprint,a.approval_fingerprint,a.authorized_by \
                 FROM book_setup_approvals a JOIN book_setup_heads h ON h.setup_id=a.setup_id \
                 WHERE a.idempotency_key=?1",
                [idempotency_key],
                |row| Ok((row.get::<_,String>(0)?,row.get::<_,u64>(1)?,row.get::<_,String>(2)?,
                    row.get::<_,String>(3)?,row.get::<_,String>(4)?,row.get::<_,String>(5)?,row.get::<_,String>(6)?)),
            )
            .optional()
            .map_err(storage_error)?
        {
            if stored_setup_id != setup_id
                || stored_plan_id != book_plan_id
                || stored_plan_fingerprint != book_plan_fingerprint
                || stored_author != authorized_by
                || version != expected_setup_version + 1
            {
                return Err(CoreError::AuthorityConflict(
                    "book setup approval idempotency key binds different input".into(),
                ));
            }
            return Ok(BookSetupApprovalReceipt {
                setup_id: stored_setup_id,
                version,
                setup_fingerprint,
                book_plan_id: stored_plan_id,
                book_plan_fingerprint: stored_plan_fingerprint,
                approval_fingerprint,
                replayed: true,
            });
        }
        let (project_id, proposal_version, setup_json, setup_fingerprint, status): (
            String,
            u64,
            String,
            String,
            String,
        ) = transaction
            .query_row(
                "SELECT project_id,expected_setup_version,setup_json,setup_fingerprint,status \
                 FROM book_setup_proposals WHERE setup_id=?1",
                [setup_id],
                |row| {
                    Ok((
                        row.get(0)?,
                        row.get(1)?,
                        row.get(2)?,
                        row.get(3)?,
                        row.get(4)?,
                    ))
                },
            )
            .map_err(storage_error)?;
        if proposal_version != expected_setup_version || status != "proposal_ready" {
            return Err(CoreError::AuthorityConflict(
                "book setup proposal is stale or no longer approvable".into(),
            ));
        }
        let current_setup_version = transaction
            .query_row(
                "SELECT version FROM book_setup_heads WHERE project_id=?1",
                [&project_id],
                |row| row.get::<_, u64>(0),
            )
            .optional()
            .map_err(storage_error)?
            .unwrap_or(0);
        if current_setup_version != expected_setup_version {
            return Err(CoreError::AuthorityConflict(
                "book setup head changed before approval".into(),
            ));
        }
        let (active_plan_id, active_plan_fingerprint): (String, String) = transaction
            .query_row(
                "SELECT proposal_id,proposal_fingerprint FROM plan_activations \
                 WHERE target_ref='book:BOOK' AND status='active'",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(storage_error)?;
        if active_plan_id != book_plan_id || active_plan_fingerprint != book_plan_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "book setup approval must bind the current active book plan".into(),
            ));
        }
        let artifact: BookSetupArtifact = serde_json::from_str(&setup_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        artifact.validate()?;
        let version = expected_setup_version
            .checked_add(1)
            .ok_or_else(|| CoreError::AuthorityConflict("book setup version overflowed".into()))?;
        let approval_json = serde_json::json!({
            "schema":"quillframe_book_setup_approval_v1",
            "setup_id":setup_id,
            "project_id":project_id,
            "expected_setup_version":expected_setup_version,
            "setup_fingerprint":setup_fingerprint,
            "book_plan_id":book_plan_id,
            "book_plan_fingerprint":book_plan_fingerprint,
            "authorized_by":authorized_by,
            "idempotency_key":idempotency_key,
            "created_at":created_at
        });
        let approval_fingerprint = crate::fingerprint::sha256_fingerprint(
            serde_json::to_vec(&approval_json)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let approval_id = format!("setup-approval-{}", uuid::Uuid::new_v4().simple());
        transaction
            .execute(
                "UPDATE book_setup_proposals SET status='superseded' \
                 WHERE project_id=?1 AND status='approved'",
                [&project_id],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE book_setup_proposals SET status='approved' WHERE setup_id=?1",
                [setup_id],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO book_setup_approvals( \
                 approval_id,setup_id,project_id,expected_setup_version,book_plan_id, \
                 book_plan_fingerprint,authorized_by,approval_json,approval_fingerprint, \
                 idempotency_key,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",
                params![
                    approval_id,
                    setup_id,
                    project_id,
                    expected_setup_version,
                    book_plan_id,
                    book_plan_fingerprint,
                    authorized_by,
                    serde_json::to_string(&approval_json)
                        .map_err(|error| CoreError::Serialization(error.to_string()))?,
                    approval_fingerprint,
                    idempotency_key,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO book_setup_heads( \
                 project_id,setup_id,version,status,setup_fingerprint,book_plan_id, \
                 book_plan_fingerprint,approval_fingerprint,updated_at \
                 ) VALUES(?1,?2,?3,'ready',?4,?5,?6,?7,?8) \
                 ON CONFLICT(project_id) DO UPDATE SET setup_id=excluded.setup_id,version=excluded.version, \
                 status='ready',setup_fingerprint=excluded.setup_fingerprint,book_plan_id=excluded.book_plan_id, \
                 book_plan_fingerprint=excluded.book_plan_fingerprint,approval_fingerprint=excluded.approval_fingerprint, \
                 updated_at=excluded.updated_at",
                params![
                    project_id,
                    setup_id,
                    version,
                    setup_fingerprint,
                    book_plan_id,
                    book_plan_fingerprint,
                    approval_fingerprint,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        for (node_id, title) in [
            ("VOL001", artifact.structure.first_volume_title.as_str()),
            ("UNIT001", artifact.structure.first_unit_title.as_str()),
            ("CH001", artifact.structure.first_chapter_title.as_str()),
        ] {
            transaction
                .execute(
                    "UPDATE story_nodes SET title=?2 WHERE node_id=?1",
                    params![node_id, title],
                )
                .map_err(storage_error)?;
        }
        transaction
            .execute(
                "UPDATE documents SET title=?1 WHERE document_id='DOC-CH001'",
                [&artifact.structure.first_chapter_title],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE search_index SET title=?1 WHERE entity_type='document' AND entity_id='DOC-CH001'",
                [&artifact.structure.first_chapter_title],
            )
            .map_err(storage_error)?;
        validate_novel_topology(&transaction)?;
        transaction.commit().map_err(storage_error)?;
        Ok(BookSetupApprovalReceipt {
            setup_id: setup_id.into(),
            version,
            setup_fingerprint,
            book_plan_id: book_plan_id.into(),
            book_plan_fingerprint: book_plan_fingerprint.into(),
            approval_fingerprint,
            replayed: false,
        })
    }

    pub fn require_book_setup_ready(&self, project_id: &str) -> CoreResult<()> {
        let binding = self
            .connection
            .query_row(
                "SELECT h.setup_fingerprint,h.book_plan_id,h.book_plan_fingerprint, \
                        p.setup_fingerprint,a.proposal_id,a.proposal_fingerprint \
                 FROM book_setup_heads h \
                 JOIN book_setup_proposals p ON p.setup_id=h.setup_id AND p.status='approved' \
                 JOIN plan_activations a ON a.target_ref='book:BOOK' AND a.status='active' \
                 WHERE h.project_id=?1 AND h.status='ready'",
                [project_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, String>(5)?,
                    ))
                },
            )
            .optional()
            .map_err(storage_error)?;
        match binding {
            Some((setup_fp, plan_id, plan_fp, proposal_setup_fp, active_id, active_fp))
                if setup_fp == proposal_setup_fp
                    && plan_id == active_id
                    && plan_fp == active_fp =>
            {
                Ok(())
            }
            _ => Err(CoreError::AuthorityConflict(
                "book setup is not author-approved and bound to the active book plan".into(),
            )),
        }
    }

    pub fn load_ready_book_setup_for_plan(
        &self,
        project_id: &str,
        book_plan_fingerprint: &str,
    ) -> CoreResult<BookSetupArtifact> {
        let setup_fingerprint = self
            .connection
            .query_row(
                "SELECT h.setup_fingerprint FROM book_setup_heads h \
                 JOIN book_setup_proposals p ON p.setup_id=h.setup_id AND p.status='approved' \
                 JOIN plan_activations a ON a.target_ref='book:BOOK' AND a.status='active' \
                 WHERE h.project_id=?1 AND h.status='ready' \
                   AND h.book_plan_fingerprint=?2 \
                   AND h.book_plan_id=a.proposal_id \
                   AND h.book_plan_fingerprint=a.proposal_fingerprint \
                   AND h.setup_fingerprint=p.setup_fingerprint",
                params![project_id, book_plan_fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "book setup is not ready for the frozen active book plan".into(),
                )
            })?;
        self.load_approved_book_setup_snapshot(
            project_id,
            &setup_fingerprint,
            book_plan_fingerprint,
        )
    }

    pub fn load_approved_book_setup_snapshot(
        &self,
        project_id: &str,
        setup_fingerprint: &str,
        book_plan_fingerprint: &str,
    ) -> CoreResult<BookSetupArtifact> {
        let payload = self
            .connection
            .query_row(
                "SELECT p.setup_json FROM book_setup_proposals p \
                 JOIN book_setup_approvals a ON a.setup_id=p.setup_id \
                 WHERE p.project_id=?1 AND p.setup_fingerprint=?2 \
                   AND a.book_plan_fingerprint=?3 \
                 ORDER BY a.created_at DESC LIMIT 1",
                params![project_id, setup_fingerprint, book_plan_fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "frozen Writer Pack references an unapproved Book Setup snapshot".into(),
                )
            })?;
        let artifact: BookSetupArtifact = serde_json::from_str(&payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        artifact.validate()?;
        if artifact.project_id != project_id || artifact.fingerprint != setup_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "Book Setup snapshot identity differs from its approval binding".into(),
            ));
        }
        Ok(artifact)
    }

    pub fn load_tracking_state(&self, project_id: &str) -> CoreResult<Option<TrackingState>> {
        let payload = self
            .connection
            .query_row(
                "SELECT payload_json FROM story_tracking_authority WHERE project_id=?1",
                [project_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?;
        payload
            .map(|json| {
                let state: TrackingState = serde_json::from_str(&json)
                    .map_err(|error| CoreError::Storage(error.to_string()))?;
                state.validate()?;
                Ok(state)
            })
            .transpose()
    }

    pub fn save_corpus_progress(
        &mut self,
        progress: &CorpusProgress,
        updated_at: &str,
    ) -> CoreResult<()> {
        progress.validate_checkpoint()?;
        require_timestamp(updated_at)?;
        let payload = serde_json::to_string(progress)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        self.connection
            .execute(
                "INSERT INTO corpus_analysis_states( \
                 source_id,source_fingerprint,stage,paused_after_golden_three,progress_json, \
                 checkpoint_fingerprint,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7) \
                 ON CONFLICT(source_id) DO UPDATE SET \
                 source_fingerprint=excluded.source_fingerprint,stage=excluded.stage, \
                 paused_after_golden_three=excluded.paused_after_golden_three, \
                 progress_json=excluded.progress_json, \
                 checkpoint_fingerprint=excluded.checkpoint_fingerprint,updated_at=excluded.updated_at",
                params![
                    progress.source_id,
                    progress.source_fingerprint,
                    stage_name(progress.current_stage),
                    progress.paused_after_golden_three,
                    payload,
                    progress.checkpoint_fingerprint,
                    updated_at
                ],
            )
            .map_err(storage_error)?;
        Ok(())
    }

    pub fn save_source_free_corpus_pack(
        &mut self,
        pack: &SourceFreeCorpusPack,
        created_at: &str,
    ) -> CoreResult<()> {
        pack.validate()?;
        require_timestamp(created_at)?;
        let payload = serde_json::to_string(pack)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if let Some(existing) = self
            .connection
            .query_row(
                "SELECT payload_json FROM corpus_source_free_packs WHERE pack_fingerprint=?1",
                [&pack.fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let frozen: SourceFreeCorpusPack = serde_json::from_str(&existing)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            frozen.validate()?;
            if frozen.fingerprint == pack.fingerprint {
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "corpus pack fingerprint binds different frozen material".into(),
            ));
        }
        self.connection
            .execute(
                "INSERT INTO corpus_source_free_packs( \
                 pack_fingerprint,genre,payload_json,source_identities_removed,created_at \
                 ) VALUES(?1,?2,?3,1,?4)",
                params![pack.fingerprint, pack.genre, payload, created_at],
            )
            .map_err(storage_error)?;
        Ok(())
    }

    pub fn save_writer_pack(&mut self, pack: &WriterPack, created_at: &str) -> CoreResult<()> {
        pack.validate()?;
        require_timestamp(created_at)?;
        let payload = serde_json::to_string(pack)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if let Some(existing) = self
            .connection
            .query_row(
                "SELECT payload_json FROM writer_pack_freezes WHERE writer_pack_fingerprint=?1",
                [&pack.fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let frozen: WriterPack = serde_json::from_str(&existing)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            frozen.validate()?;
            if frozen.fingerprint == pack.fingerprint {
                self.validate_writer_pack_bindings(pack)?;
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "Writer Pack fingerprint binds different frozen material".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO writer_pack_freezes( \
                 writer_pack_fingerprint,chapter_id,active_plan_fingerprint, \
                 context_freeze_fingerprint,tracking_fingerprint,payload_json,created_at \
                 ) VALUES(?1,?2,?3,?4,?5,?6,?7)",
                params![
                    pack.fingerprint,
                    pack.chapter_id,
                    pack.active_plan_fingerprint,
                    pack.context_freeze_fingerprint,
                    pack.tracking_fingerprint,
                    payload,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        for (index, layer) in pack.plan_lock.layers.iter().enumerate() {
            transaction
                .execute(
                    "INSERT INTO writer_pack_plan_bindings( \
                     writer_pack_fingerprint,layer_ordinal,target_ref,proposal_id,active_version,proposal_fingerprint \
                     ) VALUES(?1,?2,?3,?4,?5,?6)",
                    params![
                        pack.fingerprint,
                        index as u32 + 1,
                        layer.target.reference,
                        layer.proposal_id.to_string(),
                        layer.active_version,
                        layer.proposal_fingerprint
                    ],
                )
                .map_err(storage_error)?;
        }
        transaction.commit().map_err(storage_error)
    }

    pub fn apply_feedback_interpretation(
        &mut self,
        event_id: &str,
        interpretation: &crate::FeedbackInterpretation,
        result_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<Option<String>> {
        interpretation.validate()?;
        require_sha256(result_fingerprint)?;
        require_timestamp(created_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((existing,hypothesis_id))=transaction.query_row(
            "SELECT result_fingerprint,(SELECT hypothesis_id FROM learning_feedback_events WHERE event_id=?1) FROM learning_feedback_interpretations WHERE event_id=?1",
            [event_id],|row|Ok((row.get::<_,String>(0)?,row.get::<_,Option<String>>(1)?))
        ).optional().map_err(storage_error)? {
            if existing==result_fingerprint{return Ok(hypothesis_id);}
            return Err(CoreError::AuthorityConflict("feedback interpretation changed".into()));
        }
        let (status,feedback_text,evidence_kind,payload_fingerprint):(String,String,String,String)=transaction.query_row(
            "SELECT status,feedback_text,evidence_kind,payload_fingerprint FROM learning_feedback_events WHERE event_id=?1",
            [event_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?))
        ).map_err(storage_error)?;
        if status != "captured" {
            return Err(CoreError::AuthorityConflict(
                "only captured feedback may be interpreted".into(),
            ));
        }
        let interpretation_json = serde_json::to_string(interpretation)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let hypothesis_id = match interpretation.capture_decision {
            crate::FeedbackCaptureDecision::Skip => None,
            crate::FeedbackCaptureDecision::Capture => {
                let id = format!(
                    "preference-{}",
                    &crate::fingerprint::sha256_fingerprint(
                        format!("{event_id}:{result_fingerprint}").as_bytes()
                    )[7..23]
                );
                transaction.execute(
                    "INSERT INTO project_preference_hypotheses(hypothesis_id,scope,statement,status,evidence_json,provenance_json,created_at,updated_at) \
                     VALUES(?1,?2,?3,'candidate',?4,?5,?6,?6)",
                    params![id,interpretation.scope.as_deref().unwrap(),interpretation.statement.as_deref().unwrap(),
                        serde_json::to_string(&serde_json::json!({"event_id":event_id,"feedback_text":feedback_text,"evidence_kind":evidence_kind}))
                            .map_err(|error|CoreError::Serialization(error.to_string()))?,
                        serde_json::to_string(&serde_json::json!({"feedback_payload_fingerprint":payload_fingerprint,"interpretation_result_fingerprint":result_fingerprint}))
                            .map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]
                ).map_err(storage_error)?;
                transaction.execute(
                    "INSERT INTO preference_review_heads(hypothesis_id,version,decision,updated_at) VALUES(?1,1,'candidate',?2)",
                    params![id,created_at]
                ).map_err(storage_error)?;
                Some(id)
            }
        };
        transaction.execute(
            "INSERT INTO learning_feedback_interpretations(event_id,result_fingerprint,interpretation_json,created_at) VALUES(?1,?2,?3,?4)",
            params![event_id,result_fingerprint,interpretation_json,created_at]
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE learning_feedback_events SET status=?2,hypothesis_id=?3,version=version+1,updated_at=?4 WHERE event_id=?1 AND status='captured'",
            params![event_id,if hypothesis_id.is_some(){"interpreted"}else{"skipped"},hypothesis_id,created_at]
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE learning_evidence SET state=?2,interpreted_scope=?3,promotion_eligible=?4 WHERE evidence_id=?1",
            params![format!("learning-evidence-{event_id}"),if hypothesis_id.is_some(){"validated"}else{"rejected"},
                interpretation.scope,if hypothesis_id.is_some(){1}else{0}]
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(hypothesis_id)
    }

    pub fn apply_preference_review(
        &mut self,
        hypothesis_id: &str,
        expected_version: u64,
        result: &crate::PreferenceReviewResult,
        result_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<(u64, String)> {
        result.validate()?;
        require_sha256(result_fingerprint)?;
        require_timestamp(created_at)?;
        let decision = match result.decision {
            crate::PreferenceReviewDecision::Validated => "validated",
            crate::PreferenceReviewDecision::Contested => "contested",
        };
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let current: u64 = transaction
            .query_row(
                "SELECT version FROM preference_review_heads WHERE hypothesis_id=?1",
                [hypothesis_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if current != expected_version {
            return Err(CoreError::AuthorityConflict(
                "preference review version changed".into(),
            ));
        }
        let next = current.checked_add(1).ok_or_else(|| {
            CoreError::AuthorityConflict("preference review version overflowed".into())
        })?;
        let changed=transaction.execute(
            "UPDATE preference_review_heads SET version=?2,decision=?3,review_fingerprint=?4,updated_at=?5 WHERE hypothesis_id=?1 AND version=?6",
            params![hypothesis_id,next,decision,result_fingerprint,created_at,expected_version]
        ).map_err(storage_error)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "preference review CAS failed".into(),
            ));
        }
        transaction.execute(
            "UPDATE project_preference_hypotheses SET status=?2,updated_at=?3 WHERE hypothesis_id=?1",
            params![hypothesis_id,decision,created_at]
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok((next, decision.into()))
    }

    pub fn begin_learning_semantic_call(
        &mut self,
        aggregate_id: &str,
        stage_key: &str,
        request: &crate::ModelRequest,
        input_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<Option<ModelResult>> {
        require_sha256(input_fingerprint)?;
        require_timestamp(created_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((existing_input,state,result_json))=transaction.query_row(
            "SELECT input_fingerprint,state,result_json FROM learning_semantic_calls WHERE aggregate_id=?1 AND stage_key=?2",
            params![aggregate_id,stage_key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,Option<String>>(2)?))
        ).optional().map_err(storage_error)?{
            if existing_input!=input_fingerprint{return Err(CoreError::AuthorityConflict(
                "learning semantic input changed after dispatch".into()));}
            return match (state.as_str(),result_json){
                ("confirmed",Some(payload))=>{
                    let result:ModelResult=serde_json::from_str(&payload)
                        .map_err(|error|CoreError::Storage(error.to_string()))?;
                    result.validate()?;
                    Ok(Some(result))
                }
                ("dispatched"|"unconfirmed",_)=>Err(CoreError::ModelRuntime(
                    "unconfirmed_model_outcome: learning call will not be sent twice".into())),
                _=>Err(CoreError::AuthorityConflict("learning semantic call is invalid".into()))
            };
        }
        transaction.execute(
            "INSERT INTO learning_semantic_calls(call_id,aggregate_id,stage_key,request_id,input_fingerprint,request_json,state,created_at,updated_at) \
             VALUES(?1,?2,?3,?4,?5,?6,'dispatched',?7,?7)",
            params![format!("learning-call-{}",uuid::Uuid::new_v4()),aggregate_id,stage_key,request.request_id,
                input_fingerprint,serde_json::to_string(request).map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(None)
    }

    pub fn finish_learning_semantic_call(
        &mut self,
        aggregate_id: &str,
        stage_key: &str,
        result: Option<&ModelResult>,
        updated_at: &str,
    ) -> CoreResult<()> {
        require_timestamp(updated_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let changed = if let Some(result) = result {
            result.validate()?;
            transaction.execute(
                "UPDATE learning_semantic_calls SET state='confirmed',result_json=?3,result_fingerprint=?4,updated_at=?5 \
                 WHERE aggregate_id=?1 AND stage_key=?2 AND request_id=?6 AND state='dispatched'",
                params![aggregate_id,stage_key,serde_json::to_string(result).map_err(|error|CoreError::Serialization(error.to_string()))?,
                    result.fingerprint,updated_at,result.request_id]
            ).map_err(storage_error)?
        } else {
            transaction.execute(
                "UPDATE learning_semantic_calls SET state='unconfirmed',updated_at=?3 WHERE aggregate_id=?1 AND stage_key=?2 AND state='dispatched'",
                params![aggregate_id,stage_key,updated_at]
            ).map_err(storage_error)?
        };
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "learning semantic outcome changed".into(),
            ));
        }
        transaction.commit().map_err(storage_error)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn activate_source_free_corpus_pack(
        &mut self,
        pack: &SourceFreeCorpusPack,
        applicability: &serde_json::Value,
        expected_version: u64,
        authorization: &serde_json::Value,
        idempotency_key: &str,
        created_at: &str,
    ) -> CoreResult<(String, u64)> {
        pack.validate()?;
        require_timestamp(created_at)?;
        if idempotency_key.trim().is_empty()
            || !applicability.is_object()
            || !authorization.is_object()
        {
            return Err(CoreError::AuthorityConflict(
                "corpus activation requires applicability, authorization and idempotency".into(),
            ));
        }
        let pack_json = serde_json::to_string(pack)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let applicability_json = serde_json::to_string(applicability)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let authorization_json = serde_json::to_string(authorization)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let authorization_fingerprint =
            crate::fingerprint::sha256_fingerprint(authorization_json.as_bytes());
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((activation_id,version,prior_authorization))=transaction.query_row(
            "SELECT activation_id,version,authorization_fingerprint FROM project_corpus_pack_activations WHERE idempotency_key=?1",
            [idempotency_key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,u64>(1)?,row.get::<_,String>(2)?))
        ).optional().map_err(storage_error)? {
            if prior_authorization==authorization_fingerprint{return Ok((activation_id,version));}
            return Err(CoreError::AuthorityConflict("corpus activation idempotency key changed".into()));
        }
        let project_id: String = transaction
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        let current:u64=transaction.query_row(
            "SELECT COALESCE(MAX(version),0) FROM project_corpus_pack_activations WHERE project_id=?1 AND pack_fingerprint=?2",
            params![project_id,pack.fingerprint],|row|row.get(0)
        ).map_err(storage_error)?;
        if current != expected_version {
            return Err(CoreError::AuthorityConflict(
                "corpus activation version changed".into(),
            ));
        }
        if let Some(existing) = transaction
            .query_row(
                "SELECT payload_json FROM corpus_source_free_packs WHERE pack_fingerprint=?1",
                [&pack.fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let frozen: SourceFreeCorpusPack = serde_json::from_str(&existing)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            frozen.validate()?;
            if frozen.fingerprint != pack.fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "corpus pack snapshot changed".into(),
                ));
            }
        } else {
            transaction.execute(
                "INSERT INTO corpus_source_free_packs(pack_fingerprint,genre,payload_json,source_identities_removed,created_at) VALUES(?1,?2,?3,1,?4)",
                params![pack.fingerprint,pack.genre,pack_json,created_at]
            ).map_err(storage_error)?;
        }
        transaction.execute(
            "UPDATE project_corpus_pack_activations SET state='inactive',updated_at=?3 WHERE project_id=?1 AND pack_fingerprint=?2 AND state='active'",
            params![project_id,pack.fingerprint,created_at]
        ).map_err(storage_error)?;
        let version = current + 1;
        let activation_id = format!("corpus-activation-{}", uuid::Uuid::new_v4());
        transaction.execute(
            "INSERT INTO project_corpus_pack_activations(activation_id,project_id,pack_fingerprint,version,applicability_json, \
             authorization_json,authorization_fingerprint,idempotency_key,state,created_at,updated_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,?8,'active',?9,?9)",
            params![activation_id,project_id,pack.fingerprint,version,applicability_json,authorization_json,
                authorization_fingerprint,idempotency_key,created_at]
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok((activation_id, version))
    }

    pub fn load_writer_pack(&self, fingerprint: &str) -> CoreResult<WriterPack> {
        let payload = self
            .connection
            .query_row(
                "SELECT payload_json FROM writer_pack_freezes WHERE writer_pack_fingerprint=?1",
                [fingerprint],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict("frozen Writer Pack is unavailable".into())
            })?;
        let pack: WriterPack = serde_json::from_str(&payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        pack.validate()?;
        self.validate_writer_pack_bindings(&pack)?;
        if pack.fingerprint != fingerprint {
            return Err(CoreError::AuthorityConflict(
                "Writer Pack lookup fingerprint changed".into(),
            ));
        }
        Ok(pack)
    }

    fn validate_writer_pack_bindings(&self, pack: &WriterPack) -> CoreResult<()> {
        let mut statement = self
            .connection
            .prepare(
                "SELECT layer_ordinal,target_ref,proposal_id,active_version,proposal_fingerprint \
                 FROM writer_pack_plan_bindings WHERE writer_pack_fingerprint=?1 ORDER BY layer_ordinal",
            )
            .map_err(storage_error)?;
        let rows = statement
            .query_map([&pack.fingerprint], |row| {
                Ok((
                    row.get::<_, u32>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, u64>(3)?,
                    row.get::<_, String>(4)?,
                ))
            })
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        if rows.len() != pack.plan_lock.layers.len()
            || rows
                .iter()
                .zip(&pack.plan_lock.layers)
                .enumerate()
                .any(|(index, (row, layer))| {
                    row.0 as usize != index + 1
                        || row.1 != layer.target.reference
                        || row.2 != layer.proposal_id.to_string()
                        || row.3 != layer.active_version
                        || row.4 != layer.proposal_fingerprint
                })
        {
            return Err(CoreError::AuthorityConflict(
                "Writer Pack plan bindings are missing or changed".into(),
            ));
        }
        Ok(())
    }

    fn active_plan_chain_for_chapter(&self, chapter_id: &str) -> CoreResult<HierarchicalPlanLock> {
        let graph = self.load_story_graph()?;
        let chapter = graph
            .node(chapter_id)
            .ok_or_else(|| CoreError::InvalidPlan("chapter target does not exist".into()))?;
        if chapter.kind != StoryKind::Chapter {
            return Err(CoreError::InvalidPlan(
                "Writer Pack target must be a chapter".into(),
            ));
        }
        let mut nodes = graph.ancestors(chapter_id)?;
        nodes.push(chapter);
        let expected = [
            StoryKind::Book,
            StoryKind::Volume,
            StoryKind::Unit,
            StoryKind::Chapter,
        ];
        if nodes.len() != expected.len()
            || nodes
                .iter()
                .zip(expected)
                .any(|(node, kind)| node.kind != kind)
        {
            return Err(CoreError::InvalidPlan(
                "chapter does not have a complete book-volume-unit lineage".into(),
            ));
        }
        let mut layers: Vec<FrozenPlanLayer> = Vec::with_capacity(4);
        for node in nodes {
            let target_ref = graph.canonical_target(&node.id)?;
            let (plan_json, active_version, persisted_fingerprint) = self
                .connection
                .query_row(
                    "SELECT p.plan_json,a.active_version,a.proposal_fingerprint \
                     FROM plan_activations a JOIN plans p ON p.plan_id=a.proposal_id \
                     WHERE a.target_ref=?1 AND a.status='active' AND p.status='active'",
                    [&target_ref],
                    |row| {
                        Ok((
                            row.get::<_, String>(0)?,
                            row.get::<_, u64>(1)?,
                            row.get::<_, String>(2)?,
                        ))
                    },
                )
                .optional()
                .map_err(storage_error)?
                .ok_or_else(|| {
                    CoreError::AuthorityConflict(format!(
                        "active {target_ref} plan is required before chapter production"
                    ))
                })?;
            let proposal: PlanProposal = serde_json::from_str(&plan_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            proposal.validate_fingerprint()?;
            if proposal.target.reference != target_ref
                || proposal.fingerprint != persisted_fingerprint
            {
                return Err(CoreError::AuthorityConflict(
                    "active plan identity differs from its persisted activation".into(),
                ));
            }
            for ancestor in &layers {
                if proposal
                    .dependency_fingerprints
                    .get(&ancestor.target.reference)
                    != Some(&ancestor.proposal_fingerprint)
                {
                    return Err(CoreError::AuthorityConflict(format!(
                        "{target_ref} plan is stale or lacks an active ancestor binding"
                    )));
                }
            }
            layers.push(FrozenPlanLayer::from_active(&proposal, active_version)?);
        }
        HierarchicalPlanLock::freeze(layers)
    }

    pub fn freeze_writer_pack_for_chapter(
        &mut self,
        chapter_id: &str,
        created_at: &str,
    ) -> CoreResult<WriterPack> {
        require_timestamp(created_at)?;
        let plan_lock = self.active_plan_chain_for_chapter(chapter_id)?;
        let chapter_plan = plan_lock.chapter_plan(chapter_id)?;
        let plan_json = serde_json::to_string(&plan_lock)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let project_id: String = self
            .connection
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        let book_plan_fingerprint = plan_lock
            .layers
            .first()
            .map(|layer| layer.proposal_fingerprint.as_str())
            .ok_or_else(|| CoreError::InvalidPlan("Writer Pack plan lock is empty".into()))?;
        let approved_setup =
            self.load_ready_book_setup_for_plan(&project_id, book_plan_fingerprint)?;
        let tracking = self.load_tracking_state(&project_id)?.ok_or_else(|| {
            CoreError::AuthorityConflict("tracking authority is unavailable".into())
        })?;
        tracking.validate()?;
        let mut context = ContextManifest::default();
        context.select(ContextEntry {
            reference: format!("active-plan-chain:{chapter_id}"),
            tier: ContextTier::SettledLedger,
            fingerprint: plan_lock.fingerprint.clone(),
            summary: plan_json.clone(),
            byte_size: plan_json.len(),
            source_chapter_id: None,
            source_head_fingerprint: None,
            allowed_stages: BTreeSet::from([ContextStage::Writer]),
            contains_manuscript_body: false,
            contains_private_state: false,
            contains_corpus_identity: false,
        })?;
        let mut records = tracking.chapters.values().collect::<Vec<_>>();
        records.sort_by_key(|record| std::cmp::Reverse(record.reading_order));
        let mut continuity_context = Vec::new();
        for record in records.into_iter().take(12) {
            if tracking.invalidated_chapters.contains(&record.chapter_id) {
                return Err(CoreError::AuthorityConflict(format!(
                    "settled continuity for {} is invalidated",
                    record.chapter_id
                )));
            }
            let (canon_json, canon_head): (String, String) = self
                .connection
                .query_row(
                    "SELECT value_json,content_fingerprint FROM canon_state WHERE state_key=?1",
                    [format!("chapter:{}", record.chapter_id)],
                    |row| Ok((row.get(0)?, row.get(1)?)),
                )
                .map_err(storage_error)?;
            let canon_value: serde_json::Value = serde_json::from_str(&canon_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            if canon_value
                .get("content_fingerprint")
                .and_then(serde_json::Value::as_str)
                != Some(record.source_candidate_fingerprint.as_str())
            {
                return Err(CoreError::AuthorityConflict(
                    "tracking record does not match settled Canon".into(),
                ));
            }
            let summary = serde_json::to_string(record)
                .map_err(|error| CoreError::Serialization(error.to_string()))?;
            context.select(ContextEntry {
                reference: format!("tracking:{}", record.chapter_id),
                tier: ContextTier::SettledLedger,
                fingerprint: record.source_candidate_fingerprint.clone(),
                byte_size: summary.len(),
                summary,
                source_chapter_id: Some(record.chapter_id.clone()),
                source_head_fingerprint: Some(canon_head.clone()),
                allowed_stages: BTreeSet::from([ContextStage::Writer]),
                contains_manuscript_body: false,
                contains_private_state: false,
                contains_corpus_identity: false,
            })?;
            continuity_context.push(WriterContinuityEntry {
                record: record.clone(),
                canon_head_fingerprint: canon_head,
            });
        }
        let freeze = context.freeze(ContextStage::Writer, 16, 12 * 1024)?;
        let corpus_packs = Vec::new();
        let pressure = format!(
            "读者问题：{}；可见回报：{}；选择：{}；代价：{}；净变化：{}；章末拉力：{}",
            chapter_plan.contract.reader_contract.reader_question,
            chapter_plan.contract.reader_contract.visible_reward,
            chapter_plan.contract.reader_contract.character_choice,
            chapter_plan.contract.reader_contract.cost,
            chapter_plan.contract.reader_contract.net_change,
            chapter_plan.contract.reader_contract.next_pull
        );
        let pack = WriterPack::freeze(
            chapter_id,
            plan_lock,
            approved_setup.fingerprint,
            freeze.fingerprint,
            tracking.fingerprint,
            pressure,
            continuity_context,
            corpus_packs,
        )?;
        self.save_writer_pack(&pack, created_at)?;
        Ok(pack)
    }

    pub fn active_writer_corpus_candidates(
        &self,
    ) -> CoreResult<Vec<crate::WriterCorpusProjection>> {
        let project_id: String = self
            .connection
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        let mut statement = self
            .connection
            .prepare(
                "SELECT p.payload_json FROM corpus_source_free_packs p \
             JOIN project_corpus_pack_activations a ON a.pack_fingerprint=p.pack_fingerprint \
             WHERE a.project_id=?1 AND a.state='active' \
             ORDER BY a.updated_at DESC,a.activation_id DESC LIMIT 16",
            )
            .map_err(storage_error)?;
        let candidates = statement
            .query_map([project_id], |row| row.get::<_, String>(0))
            .map_err(storage_error)?
            .map(|row| {
                let payload = row.map_err(storage_error)?;
                let pack: SourceFreeCorpusPack = serde_json::from_str(&payload)
                    .map_err(|error| CoreError::Storage(error.to_string()))?;
                pack.writer_projection()
            })
            .collect();
        candidates
    }

    pub fn learning_preferences(&self) -> CoreResult<Vec<serde_json::Value>> {
        let mut statement = self.connection.prepare(
            "SELECT h.hypothesis_id,h.scope,h.statement,h.status,h.evidence_json,h.provenance_json, \
             COALESCE(a.version,0),COALESCE(a.state,'inactive'),h.created_at,h.updated_at \
             FROM project_preference_hypotheses h LEFT JOIN project_preference_activations a USING(hypothesis_id) \
             ORDER BY h.updated_at DESC,h.hypothesis_id",
        ).map_err(storage_error)?;
        let rows = statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, u64>(6)?,
                    row.get::<_, String>(7)?,
                    row.get::<_, String>(8)?,
                    row.get::<_, String>(9)?,
                ))
            })
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        rows.into_iter()
            .map(
                |(
                    id,
                    scope,
                    statement,
                    review_status,
                    evidence,
                    provenance,
                    version,
                    activation_state,
                    created_at,
                    updated_at,
                )| {
                    let evidence: serde_json::Value =
                        serde_json::from_str(&evidence).map_err(|error| {
                            CoreError::Storage(format!(
                                "preference evidence JSON is invalid: {error}"
                            ))
                        })?;
                    let provenance: serde_json::Value =
                        serde_json::from_str(&provenance).map_err(|error| {
                            CoreError::Storage(format!(
                                "preference provenance JSON is invalid: {error}"
                            ))
                        })?;
                    Ok(
                        serde_json::json!({"hypothesis_id":id,"scope":scope,"statement":statement,
                "review_status":review_status,"evidence":evidence,"provenance":provenance,
                "version":version,"activation_state":activation_state,"created_at":created_at,
                "updated_at":updated_at,"authority":false}),
                    )
                },
            )
            .collect()
    }

    pub fn capture_learning_feedback(
        &mut self,
        event: &serde_json::Value,
        created_at: &str,
    ) -> CoreResult<(String, bool)> {
        require_timestamp(created_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let result = insert_learning_feedback(&transaction, event, created_at)?;
        transaction.commit().map_err(storage_error)?;
        Ok(result)
    }

    pub fn learning_feedback(&self, event_id: Option<&str>) -> CoreResult<Vec<serde_json::Value>> {
        let sql = if event_id.is_some() {
            "SELECT event_id,feedback_text,evidence_kind,candidate_id,candidate_fingerprint,document_id,run_id,source_type,source_id,payload_fingerprint,status,hypothesis_id,version,created_at,updated_at FROM learning_feedback_events WHERE event_id=?1"
        } else {
            "SELECT event_id,feedback_text,evidence_kind,candidate_id,candidate_fingerprint,document_id,run_id,source_type,source_id,payload_fingerprint,status,hypothesis_id,version,created_at,updated_at FROM learning_feedback_events ORDER BY updated_at DESC,event_id"
        };
        let mut statement = self.connection.prepare(sql).map_err(storage_error)?;
        let mapper = |row: &rusqlite::Row<'_>| {
            Ok(serde_json::json!({
                "event_id":row.get::<_,String>(0)?,"feedback_text":row.get::<_,String>(1)?,
                "evidence_kind":row.get::<_,String>(2)?,"candidate_id":row.get::<_,Option<String>>(3)?,
                "candidate_fingerprint":row.get::<_,Option<String>>(4)?,"document_id":row.get::<_,Option<String>>(5)?,
                "run_id":row.get::<_,Option<String>>(6)?,"source_type":row.get::<_,String>(7)?,
                "source_id":row.get::<_,String>(8)?,"payload_fingerprint":row.get::<_,String>(9)?,
                "status":row.get::<_,String>(10)?,"hypothesis_id":row.get::<_,Option<String>>(11)?,
                "version":row.get::<_,u64>(12)?,"created_at":row.get::<_,String>(13)?,
                "updated_at":row.get::<_,String>(14)?,"authority":false
            }))
        };
        if let Some(event_id) = event_id {
            statement
                .query_map([event_id], mapper)
                .map_err(storage_error)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)
        } else {
            statement
                .query_map([], mapper)
                .map_err(storage_error)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)
        }
    }

    pub fn active_writer_preference_candidates(
        &self,
    ) -> CoreResult<Vec<crate::WriterPreferenceProjection>> {
        let mut statement = self.connection.prepare(
            "SELECT h.hypothesis_id,h.scope,h.statement,a.version \
             FROM project_preference_hypotheses h JOIN project_preference_activations a USING(hypothesis_id) \
             WHERE h.status='validated' AND a.state='active' \
             ORDER BY a.updated_at DESC,h.hypothesis_id LIMIT 64",
        ).map_err(storage_error)?;
        let candidates = statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, u64>(3)?,
                ))
            })
            .map_err(storage_error)?
            .map(|row| {
                let (id, scope, statement, version) = row.map_err(storage_error)?;
                crate::WriterPreferenceProjection::freeze(id, scope, statement, version)
            })
            .collect();
        candidates
    }

    #[allow(clippy::too_many_arguments)]
    pub fn set_preference_activation(
        &mut self,
        hypothesis_id: &str,
        expected_version: u64,
        activate: bool,
        authorized_by: &str,
        idempotency_key: &str,
        user_authorized: bool,
        created_at: &str,
    ) -> CoreResult<(u64, String, bool)> {
        require_timestamp(created_at)?;
        if hypothesis_id.trim().is_empty()
            || authorized_by.trim().is_empty()
            || idempotency_key.trim().is_empty()
            || !user_authorized
        {
            return Err(CoreError::AuthorityConflict(
                "preference activation requires explicit user authorization and stable identity"
                    .into(),
            ));
        }
        let target_state = if activate { "active" } else { "inactive" };
        let authorization = serde_json::json!({
            "hypothesis_id":hypothesis_id,"expected_version":expected_version,
            "resulting_state":target_state,"authorized_by":authorized_by,
            "user_authorized":user_authorized,"idempotency_key":idempotency_key
        });
        let authorization_json = serde_json::to_string(&authorization)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let authorization_fingerprint =
            crate::fingerprint::sha256_fingerprint(authorization_json.as_bytes());
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((resulting_version,resulting_state,prior_fingerprint)) = transaction.query_row(
            "SELECT resulting_version,resulting_state,authorization_fingerprint FROM preference_activation_receipts WHERE idempotency_key=?1",
            [idempotency_key],|row|Ok((row.get::<_,u64>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?))
        ).optional().map_err(storage_error)? {
            if prior_fingerprint==authorization_fingerprint {
                return Ok((resulting_version,resulting_state,true));
            }
            return Err(CoreError::AuthorityConflict(
                "preference idempotency key binds different authorization".into(),
            ));
        }
        let hypothesis_status: String = transaction
            .query_row(
                "SELECT status FROM project_preference_hypotheses WHERE hypothesis_id=?1",
                [hypothesis_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if activate && hypothesis_status != "validated" {
            return Err(CoreError::AuthorityConflict(
                "only a semantically validated preference may become active".into(),
            ));
        }
        let current_version: u64 = transaction.query_row(
            "SELECT COALESCE((SELECT version FROM project_preference_activations WHERE hypothesis_id=?1),0)",
            [hypothesis_id],|row|row.get(0)
        ).map_err(storage_error)?;
        if current_version != expected_version {
            return Err(CoreError::AuthorityConflict(
                "preference activation version changed".into(),
            ));
        }
        let resulting_version = current_version.checked_add(1).ok_or_else(|| {
            CoreError::AuthorityConflict("preference activation version overflowed".into())
        })?;
        transaction.execute(
            "INSERT INTO project_preference_activations(hypothesis_id,version,state,authorized_by,authorization_fingerprint,created_at,updated_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?6) ON CONFLICT(hypothesis_id) DO UPDATE SET \
             version=excluded.version,state=excluded.state,authorized_by=excluded.authorized_by, \
             authorization_fingerprint=excluded.authorization_fingerprint,updated_at=excluded.updated_at",
            params![hypothesis_id,resulting_version,target_state,authorized_by,authorization_fingerprint,created_at]
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO preference_activation_receipts(receipt_id,hypothesis_id,expected_version,resulting_version,resulting_state,idempotency_key,authorization_json,authorization_fingerprint,created_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9)",
            params![format!("preference-receipt-{}",uuid::Uuid::new_v4()),hypothesis_id,expected_version,
                resulting_version,target_state,idempotency_key,authorization_json,authorization_fingerprint,created_at]
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok((resulting_version, target_state.into(), false))
    }

    pub fn writer_context_candidate_pool(
        &self,
        chapter_id: &str,
        query_plan: &ContextQueryPlan,
    ) -> CoreResult<Vec<ContextEntry>> {
        query_plan.validate()?;
        let project_id: String = self
            .connection
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        let tracking = self.load_tracking_state(&project_id)?.ok_or_else(|| {
            CoreError::AuthorityConflict("tracking authority is unavailable".into())
        })?;
        tracking.validate()?;
        let mut manifest = ContextManifest::default();
        self.active_plan_chain_for_chapter(chapter_id)?.validate()?;

        let mut records = tracking.chapters.values().collect::<Vec<_>>();
        records.sort_by_key(|record| std::cmp::Reverse(record.reading_order));
        for record in records.iter().take(4) {
            if tracking.invalidated_chapters.contains(&record.chapter_id) {
                continue;
            }
            if let Some(entry) = self.manuscript_context_entry(
                &record.chapter_id,
                ContextTier::RecentManuscript,
                None,
            )? {
                manifest.select(entry)?;
            }
        }

        for (reference, summary) in self.active_ledger_context_rows()? {
            manifest.select(ContextEntry {
                reference,
                tier: ContextTier::SettledLedger,
                fingerprint: crate::fingerprint::sha256_fingerprint(summary.as_bytes()),
                byte_size: summary.len(),
                summary,
                source_chapter_id: None,
                source_head_fingerprint: None,
                allowed_stages: writer_context_stages(),
                contains_manuscript_body: false,
                contains_private_state: false,
                contains_corpus_identity: false,
            })?;
        }

        for query in &query_plan.queries {
            let mut statement = self
                .connection
                .prepare(
                    "SELECT d.story_node_id,r.content FROM document_revisions r \
                 JOIN documents d ON d.document_id=r.document_id \
                 WHERE r.authority_class='accepted' AND instr(r.content,?1)>0 \
                 ORDER BY r.created_at DESC,r.revision_id DESC LIMIT 4",
                )
                .map_err(storage_error)?;
            let matches = statement
                .query_map([query], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
                })
                .map_err(storage_error)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)?;
            drop(statement);
            for (source_chapter_id, content) in matches {
                let reference = format!(
                    "archive-evidence:{source_chapter_id}:{}",
                    crate::fingerprint::sha256_fingerprint(query.as_bytes())
                );
                if manifest
                    .entries()
                    .iter()
                    .any(|entry| entry.reference == reference)
                {
                    continue;
                }
                let (_, head_fingerprint) = self.chapter_canon_head(&source_chapter_id)?;
                let excerpt = evidence_window(&content, query, 2_400);
                manifest.select(ContextEntry {
                    reference,
                    tier: ContextTier::ArchiveEvidence,
                    fingerprint: crate::fingerprint::sha256_fingerprint(excerpt.as_bytes()),
                    byte_size: excerpt.len(),
                    summary: excerpt,
                    source_chapter_id: Some(source_chapter_id),
                    source_head_fingerprint: Some(head_fingerprint),
                    allowed_stages: writer_context_stages(),
                    contains_manuscript_body: true,
                    contains_private_state: false,
                    contains_corpus_identity: false,
                })?;
            }
        }
        Ok(manifest.entries().iter().take(128).cloned().collect())
    }

    #[allow(clippy::too_many_arguments)]
    pub fn persist_writer_context_freeze(
        &mut self,
        run_id: &str,
        task_mode: ProductionTaskMode,
        query_plan: &ContextQueryPlan,
        candidates: &[ContextEntry],
        proposal: &ContextSelectionProposal,
        freeze: &ContextFreeze,
        created_at: &str,
    ) -> CoreResult<String> {
        query_plan.validate()?;
        proposal.validate_against(candidates)?;
        require_timestamp(created_at)?;
        let universe_fingerprint = crate::fingerprint::sha256_fingerprint(
            serde_json::to_vec(candidates)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let selection_fingerprint = crate::fingerprint::sha256_fingerprint(
            serde_json::to_vec(&serde_json::json!({
                "run_id":run_id,"stage":"writer","query_plan":query_plan,
                "candidate_universe_fingerprint":universe_fingerprint,"proposal":proposal
            }))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let scoped_freeze_fingerprint = crate::fingerprint::sha256_fingerprint(
            format!("{run_id}:{}", freeze.fingerprint).as_bytes(),
        );
        let pool_json = serde_json::to_string(candidates)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let greenlight_json = serde_json::to_string(proposal)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let snapshot_json = serde_json::to_string(freeze)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let request: ProductionRequest = serde_json::from_str(
            &transaction.query_row(
                "SELECT request_json FROM production_executions WHERE run_id=?1 AND cancel_requested=0",
                [run_id],
                |row| row.get::<_, String>(0),
            ).map_err(storage_error)?,
        ).map_err(|error| CoreError::Storage(error.to_string()))?;
        request.validate()?;
        if request.task_mode != task_mode {
            return Err(CoreError::AuthorityConflict(
                "context freeze task mode changed".into(),
            ));
        }
        if let Some(existing) = transaction.query_row(
            "SELECT freeze_fingerprint FROM context_freezes WHERE run_id=?1 AND status='frozen'",
            [run_id],|row|row.get::<_,String>(0)
        ).optional().map_err(storage_error)? {
            if existing == scoped_freeze_fingerprint {
                return Ok(scoped_freeze_fingerprint);
            }
            return Err(CoreError::AuthorityConflict(
                "run already binds a different context freeze".into(),
            ));
        }
        transaction.execute(
            "INSERT INTO context_stage_selections(selection_id,run_id,stage_id,candidate_universe_fingerprint,selection_fingerprint,pool_json,greenlight_json,status,created_at) \
             VALUES(?1,?2,'writer',?3,?4,?5,?6,'greenlit',?7)",
            params![format!("context-selection-{}",uuid::Uuid::new_v4()),run_id,universe_fingerprint,
                selection_fingerprint,pool_json,greenlight_json,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO context_freezes(freeze_id,run_id,task_mode,freeze_fingerprint,snapshot_json,status,created_at) \
             VALUES(?1,?2,?3,?4,?5,'frozen',?6)",
            params![format!("context-freeze-{}",uuid::Uuid::new_v4()),run_id,
                production_task_mode(task_mode),scoped_freeze_fingerprint,snapshot_json,created_at],
        ).map_err(storage_error)?;
        let target_chapter: String = transaction.query_row(
            "SELECT d.story_node_id FROM production_executions e JOIN runs r ON r.run_id=e.run_id \
             JOIN documents d ON d.document_id=r.target_ref WHERE e.run_id=?1",
            [run_id],|row|row.get(0)
        ).map_err(storage_error)?;
        for entry in &freeze.entries {
            if let (Some(source_chapter_id), Some(source_head_fingerprint)) =
                (&entry.source_chapter_id, &entry.source_head_fingerprint)
            {
                if source_chapter_id == &target_chapter {
                    continue;
                }
                let (_, current_head) =
                    chapter_canon_head_transaction(&transaction, source_chapter_id)?;
                if &current_head != source_head_fingerprint {
                    return Err(CoreError::AuthorityConflict(
                        "selected context changed before freeze commit".into(),
                    ));
                }
                transaction.execute(
                    "INSERT INTO chapter_dependencies(chapter_id,source_chapter_id,source_fingerprint,run_id,status,created_at,updated_at) \
                     VALUES(?1,?2,?3,?4,'current',?5,?5) \
                     ON CONFLICT(chapter_id,source_chapter_id,run_id) DO UPDATE SET \
                     source_fingerprint=excluded.source_fingerprint,status='current',updated_at=excluded.updated_at",
                    params![target_chapter,source_chapter_id,source_head_fingerprint,run_id,created_at],
                ).map_err(storage_error)?;
            }
        }
        transaction.commit().map_err(storage_error)?;
        Ok(scoped_freeze_fingerprint)
    }

    fn manuscript_context_entry(
        &self,
        chapter_id: &str,
        tier: ContextTier,
        query: Option<&str>,
    ) -> CoreResult<Option<ContextEntry>> {
        let content = self.connection.query_row(
            "SELECT r.content FROM document_revisions r JOIN documents d ON d.document_id=r.document_id \
             WHERE d.story_node_id=?1 AND r.authority_class='accepted' \
             ORDER BY r.created_at DESC,r.revision_id DESC LIMIT 1",
            [chapter_id],|row|row.get::<_,String>(0)
        ).optional().map_err(storage_error)?;
        let Some(content) = content else {
            return Ok(None);
        };
        let (_, head_fingerprint) = self.chapter_canon_head(chapter_id)?;
        let summary = query
            .map(|query| evidence_window(&content, query, 2_400))
            .unwrap_or_else(|| last_utf8_chars(&content, 6_000));
        Ok(Some(ContextEntry {
            reference: format!("recent-manuscript:{chapter_id}"),
            tier,
            fingerprint: crate::fingerprint::sha256_fingerprint(summary.as_bytes()),
            byte_size: summary.len(),
            summary,
            source_chapter_id: Some(chapter_id.into()),
            source_head_fingerprint: Some(head_fingerprint),
            allowed_stages: writer_context_stages(),
            contains_manuscript_body: true,
            contains_private_state: false,
            contains_corpus_identity: false,
        }))
    }

    fn chapter_canon_head(&self, chapter_id: &str) -> CoreResult<(String, String)> {
        chapter_canon_head_connection(&self.connection, chapter_id)
    }

    fn active_ledger_context_rows(&self) -> CoreResult<Vec<(String, String)>> {
        let mut rows = Vec::new();
        let mut statement = self.connection.prepare(
            "SELECT c.character_id,c.name,c.state_json FROM characters c \
             LEFT JOIN narrative_state_sources s ON s.entity_type='character' AND s.entity_id=c.character_id \
             WHERE s.entity_id IS NULL OR s.state='current' \
             ORDER BY c.updated_at DESC,c.character_id LIMIT 12",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, name, state) = row.map_err(storage_error)?;
            rows.push((format!("ledger:character:{id}"), format!("{name}: {state}")));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT e.expectation_id,e.kind,e.description,e.status FROM expectations e \
             LEFT JOIN narrative_state_sources s ON s.entity_type='expectation' AND s.entity_id=e.expectation_id \
             WHERE e.status IN ('open','partial') AND (s.entity_id IS NULL OR s.state='current') \
             ORDER BY e.last_touched_order DESC,e.expectation_id LIMIT 16",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, kind, description, status) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:expectation:{id}"),
                format!("{kind}/{status}: {description}"),
            ));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT t.event_id,t.title,t.description FROM timeline_events t \
             LEFT JOIN narrative_state_sources s ON s.entity_type='timeline' AND s.entity_id=t.event_id \
             WHERE t.authority_class='accepted' AND (s.entity_id IS NULL OR s.state='current') \
             ORDER BY t.story_order DESC,t.event_id LIMIT 12",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, Option<String>>(2)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, title, description) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:timeline:{id}"),
                format!("{title}: {}", description.unwrap_or_default()),
            ));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT r.relationship_id,r.participant_a,r.participant_b,r.relationship_type,r.state_json \
             FROM relationships r LEFT JOIN narrative_state_sources s \
             ON s.entity_type='relationship' AND s.entity_id=r.relationship_id \
             WHERE s.entity_id IS NULL OR s.state='current' \
             ORDER BY r.updated_at DESC,r.relationship_id LIMIT 16",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, a, b, kind, state) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:relationship:{id}"),
                format!("{a}<->{b}/{kind}: {state}"),
            ));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT w.entity_id,w.entity_type,w.name,w.truth_json FROM world_entities w \
             LEFT JOIN narrative_state_sources s ON s.entity_type='world' AND s.entity_id=w.entity_id \
             WHERE s.entity_id IS NULL OR s.state='current' \
             ORDER BY w.updated_at DESC,w.entity_id LIMIT 16",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, kind, name, state) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:world:{id}"),
                format!("{kind}/{name}: {state}"),
            ));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT k.knowledge_id,k.character_id,k.fact_json,k.available_from_story_order,k.confidence \
             FROM character_knowledge k LEFT JOIN narrative_state_sources s \
             ON s.entity_type='knowledge' AND s.entity_id=k.knowledge_id \
             WHERE s.entity_id IS NULL OR s.state='current' \
             ORDER BY k.available_from_story_order DESC,k.knowledge_id LIMIT 24",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, u32>(3)?,
                    row.get::<_, String>(4)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (id, character, fact, order, confidence) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:knowledge:{id}"),
                format!("{character}@{order}/{confidence}: {fact}"),
            ));
        }
        drop(statement);
        let mut statement = self.connection.prepare(
            "SELECT state_key,value_json,authority_class,evidence_ref FROM canon_state ORDER BY updated_at DESC,state_key LIMIT 24",
        ).map_err(storage_error)?;
        for row in statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(storage_error)?
        {
            let (key, value, authority, evidence) = row.map_err(storage_error)?;
            rows.push((
                format!("ledger:canon:{key}"),
                format!("{authority}/{evidence}: {value}"),
            ));
        }
        Ok(rows)
    }

    pub fn save_review_report(
        &mut self,
        report: &ReviewReport,
        created_at: &str,
    ) -> CoreResult<()> {
        report.validate(&report.candidate_fingerprint)?;
        require_timestamp(created_at)?;
        let payload = serde_json::to_string(report)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        self.connection
            .execute(
                "INSERT INTO structured_review_reports( \
                 report_fingerprint,candidate_fingerprint,mode,decision, \
                 independent_context,payload_json,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7)",
                params![
                    report.fingerprint,
                    report.candidate_fingerprint,
                    review_mode_name(report.mode),
                    review_decision_name(report.decision),
                    report.independent_context,
                    payload,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        Ok(())
    }

    pub fn save_production_release(&mut self, release: &ProductionRelease) -> CoreResult<()> {
        release.validate()?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let (status, candidate_fingerprint, document_id, revision_id) = transaction
            .query_row(
                "SELECT status,content_fingerprint,document_id,revision_id FROM candidates WHERE candidate_id=?1",
                [&release.candidate_id],
                |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?,row.get::<_,String>(3)?)),
            )
            .map_err(storage_error)?;
        if status != "review_draft" || candidate_fingerprint != release.candidate_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "production release candidate is stale or not reviewable".into(),
            ));
        }
        let (revision_document, content, revision_fingerprint) = transaction
            .query_row(
                "SELECT document_id,content,content_fingerprint FROM document_revisions WHERE revision_id=?1",
                [&revision_id],
                |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?)),
            )
            .map_err(storage_error)?;
        if revision_document != document_id
            || revision_fingerprint != release.candidate_fingerprint
            || crate::fingerprint::sha256_fingerprint(content.as_bytes()) != revision_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "production release bytes are not bound to the candidate".into(),
            ));
        }
        let review_count: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM structured_review_reports WHERE report_fingerprint=?1 \
                 AND candidate_fingerprint=?2 AND decision='accept' AND independent_context=1",
                params![
                    release.review_report_fingerprint,
                    release.candidate_fingerprint
                ],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if review_count != 1 {
            return Err(CoreError::AuthorityConflict(
                "production release requires its exact independent accept report".into(),
            ));
        }
        let writer_pack_count: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM writer_pack_freezes WHERE writer_pack_fingerprint=?1 \
                 AND tracking_fingerprint=?2",
                params![
                    release.writer_pack_fingerprint,
                    release.tracking_fingerprint
                ],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if writer_pack_count != 1 {
            return Err(CoreError::AuthorityConflict(
                "production release requires its exact Writer Pack and tracking freeze".into(),
            ));
        }
        let payload = serde_json::to_string(release)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let stage_receipts = serde_json::to_string(&release.stage_receipt_fingerprints)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO production_releases(release_id,candidate_id,candidate_fingerprint,writer_pack_fingerprint, \
             tracking_fingerprint,review_report_fingerprint,stage_receipt_fingerprints_json,payload_json,release_fingerprint,user_visible,released_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,1,?10)",
            params![release.release_id,release.candidate_id,release.candidate_fingerprint,release.writer_pack_fingerprint,
                release.tracking_fingerprint,release.review_report_fingerprint,stage_receipts,payload,release.fingerprint,release.released_at],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn commit_released_candidate(
        &mut self,
        run_id: &str,
        document_id: &str,
        task_mode: ProductionTaskMode,
        candidate: &CandidateArtifact,
        report: &ReviewReport,
        release: &ProductionRelease,
        created_at: &str,
    ) -> CoreResult<(String, String)> {
        require_timestamp(created_at)?;
        candidate.validate()?;
        report.validate(&candidate.fingerprint)?;
        release.validate()?;
        if report.decision != crate::ReviewDecision::Accept
            || release.candidate_id != candidate.candidate_id
            || release.candidate_fingerprint != candidate.fingerprint
            || release.writer_pack_fingerprint != candidate.writer_pack_fingerprint
            || release.review_report_fingerprint != report.fingerprint
            || release.task_mode != task_mode
        {
            return Err(CoreError::AuthorityConflict(
                "candidate, review and production release are not exactly bound".into(),
            ));
        }
        let preflight_request = self.load_production_request(run_id)?;
        let bounded_evidence = if release
            .stage_receipt_fingerprints
            .contains_key("bounded_repair_surface")
        {
            Some(self.resolve_bounded_repair_evidence(&preflight_request)?)
        } else {
            None
        };
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let chapter_id = transaction
            .query_row(
                "SELECT story_node_id FROM documents WHERE document_id=?1 AND document_kind='manuscript'",
                [document_id],
                |row| row.get::<_, String>(0),
            )
            .map_err(storage_error)?;
        if chapter_id != candidate.chapter_id {
            return Err(CoreError::AuthorityConflict(
                "candidate chapter does not match its manuscript document".into(),
            ));
        }
        let (request_json, status): (String, String) = transaction
            .query_row(
                "SELECT request_json,r.status FROM production_executions e JOIN runs r ON r.run_id=e.run_id WHERE e.run_id=?1",
                [run_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(storage_error)?;
        let request: ProductionRequest = serde_json::from_str(&request_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        request.validate()?;
        if request.fingerprint != preflight_request.fingerprint
            || !matches!(status.as_str(), "executing" | "awaiting_release")
            || request.target_ref != document_id
            || request.writer_pack_fingerprint != candidate.writer_pack_fingerprint
            || request.task_mode != task_mode
        {
            return Err(CoreError::AuthorityConflict(
                "production run changed before candidate release".into(),
            ));
        }
        let tracking_fingerprint: String = transaction
            .query_row(
                "SELECT tracking_fingerprint FROM writer_pack_freezes WHERE writer_pack_fingerprint=?1",
                [&candidate.writer_pack_fingerprint],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if tracking_fingerprint != release.tracking_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "release tracking freeze changed".into(),
            ));
        }
        if let Some((_, evidence_receipts)) = &bounded_evidence {
            let released_inherited_evidence = release
                .stage_receipt_fingerprints
                .iter()
                .filter(|(stage_key, _)| {
                    matches!(
                        stage_key.as_str(),
                        "character_simulation" | "scene_resolution"
                    ) || stage_key.starts_with("surface_scene_")
                })
                .map(|(stage_key, fingerprint)| (stage_key.clone(), fingerprint.clone()))
                .collect::<BTreeMap<_, _>>();
            if &released_inherited_evidence != evidence_receipts {
                return Err(CoreError::AuthorityConflict(
                    "bounded release inherited evidence changed".into(),
                ));
            }
        }
        for (release_key, stage_key) in [
            ("context_query_plan", "context_query_plan"),
            ("context_greenlight", "context_greenlight"),
            ("corpus_greenlight", "corpus_greenlight"),
            ("preference_greenlight", "preference_greenlight"),
            ("character_simulation", "character_simulation"),
            ("scene_resolution", "scene_resolution"),
            ("surface_realization", "surface_realization"),
            ("surface_hard_rule_audit", "surface_hard_rule_audit"),
            ("reader_engagement", "reader_engagement"),
            ("continuity", "continuity_rule_audit"),
            ("candidate_self_audit", "candidate_self_audit"),
            ("independent_semantic_gate", "independent_semantic_gate"),
            (
                "settlement_tracking_projection",
                "settlement_tracking_projection",
            ),
            ("settlement_tracking_audit", "settlement_tracking_audit"),
        ] {
            let expected = release
                .stage_receipt_fingerprints
                .get(release_key)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("release stage receipt is missing".into())
                })?;
            let receipt_count: u32 = if matches!(
                release_key,
                "character_simulation" | "scene_resolution"
            ) && bounded_evidence.is_some()
            {
                let (evidence_run_id, evidence_receipts) = bounded_evidence.as_ref().unwrap();
                if evidence_receipts.get(release_key) != Some(expected) {
                    0
                } else {
                    transaction
                        .query_row(
                        "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2 \
                         AND state='confirmed' AND result_fingerprint=?3",
                        params![evidence_run_id, stage_key, expected],
                        |row| row.get(0),
                    )
                    .map_err(storage_error)?
                }
            } else if release_key == "settlement_tracking_projection" {
                transaction
                    .query_row(
                        "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND state='confirmed' \
                         AND result_fingerprint=?2 AND stage_key IN ('settlement_tracking_projection', \
                         'settlement_tracking_projection_schema_repair','settlement_tracking_projection_semantic_repair', \
                         'settlement_tracking_projection_audit_repair','settlement_tracking_projection_audit_repair_2', \
                         'settlement_tracking_projection_audit_repair_3')",
                        params![run_id, expected],
                        |row| row.get(0),
                    )
                    .map_err(storage_error)?
            } else if release_key == "settlement_tracking_audit" {
                transaction
                    .query_row(
                         "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND state='confirmed' \
                          AND result_fingerprint=?2 AND stage_key IN ('settlement_tracking_audit','settlement_tracking_audit_repair', \
                          'settlement_tracking_audit_repair_2','settlement_tracking_audit_repair_3')",
                        params![run_id, expected],
                        |row| row.get(0),
                    )
                    .map_err(storage_error)?
            } else {
                transaction
                    .query_row(
                        "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2 \
                         AND state='confirmed' AND result_fingerprint=?3",
                        params![run_id, stage_key, expected],
                        |row| row.get(0),
                    )
                    .map_err(storage_error)?
            };
            if receipt_count != 1 {
                return Err(CoreError::AuthorityConflict(format!(
                    "release {release_key} receipt does not belong to this run"
                )));
            }
        }
        let context_freeze = release
            .stage_receipt_fingerprints
            .get("context_freeze")
            .ok_or_else(|| {
                CoreError::AuthorityConflict("release context freeze is missing".into())
            })?;
        let persisted_context_freeze: String = transaction.query_row(
            "SELECT freeze_fingerprint FROM context_freezes WHERE run_id=?1 AND status='frozen'",
            [run_id],|row|row.get(0)
        ).map_err(storage_error)?;
        if &persisted_context_freeze != context_freeze {
            return Err(CoreError::AuthorityConflict(
                "release context freeze does not belong to this run".into(),
            ));
        }
        let scene_receipts = release
            .stage_receipt_fingerprints
            .iter()
            .filter(|(stage_key, _)| stage_key.starts_with("surface_scene_"))
            .collect::<Vec<_>>();
        if scene_receipts.is_empty() {
            return Err(CoreError::AuthorityConflict(
                "release has no scene-level surface receipts".into(),
            ));
        }
        for (stage_key, expected) in scene_receipts {
            let evidence_run_id = bounded_evidence
                .as_ref()
                .map(|(origin_run_id, _)| origin_run_id.as_str())
                .unwrap_or(run_id);
            let receipt_count: u32 = if bounded_evidence
                .as_ref()
                .is_some_and(|(_, receipts)| receipts.get(stage_key) != Some(expected))
            {
                0
            } else {
                transaction
                    .query_row(
                        "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2 \
                         AND state='confirmed' AND result_fingerprint=?3",
                        params![evidence_run_id, stage_key, expected],
                        |row| row.get(0),
                    )
                    .map_err(storage_error)?
            };
            if receipt_count != 1 {
                return Err(CoreError::AuthorityConflict(format!(
                    "release {stage_key} receipt does not belong to this run"
                )));
            }
        }
        if task_mode == ProductionTaskMode::Revise {
            for stage_key in ["repair_editor", "repair_comparison"] {
                let expected = release
                    .stage_receipt_fingerprints
                    .get(stage_key)
                    .ok_or_else(|| {
                        CoreError::AuthorityConflict(
                            "REVISE release stage receipt is missing".into(),
                        )
                    })?;
                let actual=transaction.query_row(
                    "SELECT result_fingerprint FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2 AND state='confirmed'",
                    params![run_id,stage_key],|row|row.get::<_,String>(0)
                ).map_err(storage_error)?;
                if &actual != expected {
                    return Err(CoreError::AuthorityConflict(format!(
                        "REVISE {stage_key} receipt is not bound to this run"
                    )));
                }
            }
            let repair_source = release
                .stage_receipt_fingerprints
                .get("repair_source")
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("REVISE repair source receipt is missing".into())
                })?;
            let binding = request.intent.repair_source.as_ref().ok_or_else(|| {
                CoreError::AuthorityConflict("REVISE request lost its repair binding".into())
            })?;
            if repair_source != &binding.expected_candidate_fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "REVISE release repair source changed".into(),
                ));
            }
        }
        let user_visible_receipt = release
            .stage_receipt_fingerprints
            .get("user_visible_gate")
            .ok_or_else(|| {
                CoreError::AuthorityConflict("user-visible receipt is missing".into())
            })?;
        let revision_id = format!("revision-{}", uuid::Uuid::new_v4());
        let parent_revision_id = transaction
            .query_row(
                "SELECT revision_id FROM document_revisions WHERE document_id=?1 \
                 ORDER BY created_at DESC,revision_id DESC LIMIT 1",
                [document_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?;
        let provenance = serde_json::to_string(&serde_json::json!({
            "run_id":run_id,"writer_pack_fingerprint":candidate.writer_pack_fingerprint,
            "candidate_id":candidate.candidate_id,"production_release_id":release.release_id
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO document_revisions(revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json) \
             VALUES(?1,?2,?3,?4,?5,?6,'production_candidate','review',?7)",
            params![revision_id,document_id,parent_revision_id,candidate.manuscript,candidate.fingerprint,created_at,provenance],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) \
             VALUES(?1,?2,?3,?4,?5,?6,'review_draft',?7,?8,?9)",
            params![candidate.candidate_id,document_id,revision_id,run_id,production_task_mode(task_mode),
                if task_mode == ProductionTaskMode::Draft {"draft"} else {"repair"},candidate.fingerprint,"PASS",created_at],
        ).map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO candidate_lineage(candidate_id,lineage_json) VALUES(?1,?2)",
                params![
                    candidate.candidate_id,
                    serde_json::to_string(candidate)
                        .map_err(|error| CoreError::Serialization(error.to_string()))?
                ],
            )
            .map_err(storage_error)?;
        let report_json = serde_json::to_string(report)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO structured_review_reports(report_fingerprint,candidate_fingerprint,mode,decision,independent_context,payload_json,created_at) \
             VALUES(?1,?2,?3,'accept',1,?4,?5)",
            params![report.fingerprint,candidate.fingerprint,review_mode_name(report.mode),report_json,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,?2,'user_visible_gate',?3,?4,?5)",
            params![format!("checkpoint-{}",uuid::Uuid::new_v4()),run_id,
                serde_json::to_string(&serde_json::json!({"candidate_fingerprint":candidate.fingerprint,"release_id":release.release_id})).map_err(|error|CoreError::Serialization(error.to_string()))?,user_visible_receipt,created_at],
        ).map_err(storage_error)?;
        let release_json = serde_json::to_string(release)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let stage_receipts = serde_json::to_string(&release.stage_receipt_fingerprints)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO production_releases(release_id,candidate_id,candidate_fingerprint,writer_pack_fingerprint,tracking_fingerprint,review_report_fingerprint,stage_receipt_fingerprints_json,payload_json,release_fingerprint,user_visible,released_at) \
             VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,1,?10)",
            params![release.release_id,candidate.candidate_id,candidate.fingerprint,candidate.writer_pack_fingerprint,
                release.tracking_fingerprint,report.fingerprint,stage_receipts,release_json,release.fingerprint,release.released_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE runs SET status='review',result_fingerprint=?2,updated_at=?3 WHERE run_id=?1",
            params![run_id,release.fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) \
             VALUES(?1,?2,'production_released',?3,?4)",
            params![format!("event-{}",uuid::Uuid::new_v4()),run_id,
                serde_json::to_string(&serde_json::json!({"candidate_id":candidate.candidate_id,"candidate_fingerprint":candidate.fingerprint,"release_fingerprint":release.fingerprint})).map_err(|error|CoreError::Serialization(error.to_string()))?,created_at],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok((revision_id, release.release_id.clone()))
    }

    pub fn start_production(
        &mut self,
        request: &ProductionRequest,
        created_at: &str,
    ) -> CoreResult<()> {
        request.validate()?;
        require_timestamp(created_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some(existing) = transaction
            .query_row(
                "SELECT request_fingerprint FROM production_executions WHERE run_id=?1",
                [&request.run_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            if existing == request.fingerprint {
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "run id binds a different production request".into(),
            ));
        }
        let writer_pack_payload: Option<String> = transaction
            .query_row(
                "SELECT payload_json FROM writer_pack_freezes WHERE writer_pack_fingerprint=?1",
                [&request.writer_pack_fingerprint],
                |row| row.get(0),
            )
            .optional()
            .map_err(storage_error)?;
        let writer_pack: WriterPack =
            serde_json::from_str(writer_pack_payload.as_deref().ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "production requires its exact frozen Writer Pack".into(),
                )
            })?)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        writer_pack.validate()?;
        let target_chapter: String = transaction
            .query_row(
                "SELECT story_node_id FROM documents WHERE document_id=?1 AND document_kind='manuscript'",
                [&request.target_ref],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if target_chapter != writer_pack.chapter_id {
            return Err(CoreError::AuthorityConflict(
                "production target and Writer Pack chapter differ".into(),
            ));
        }
        let payload = serde_json::to_string(request)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute("INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) VALUES(?1,?2,?3,'ready',?4,?5,?5)",params![request.run_id,production_task_mode(request.task_mode),request.target_ref,request.fingerprint,created_at]).map_err(storage_error)?;
        transaction.execute("INSERT INTO production_executions(run_id,request_fingerprint,request_json,created_at,updated_at) VALUES(?1,?2,?3,?4,?4)",params![request.run_id,request.fingerprint,payload,created_at]).map_err(storage_error)?;
        transaction.execute("INSERT INTO production_execution_request_versions(run_id,version,request_fingerprint,request_json,framework_build_fingerprint,run_status_at_activation,activation_kind,created_at) VALUES(?1,1,?2,?3,?4,'ready','initial',?5)",params![request.run_id,request.fingerprint,payload,request.framework_build_fingerprint,created_at]).map_err(storage_error)?;
        for dependency in &writer_pack.continuity_context {
            let current_head: Option<String> = transaction
                .query_row(
                    "SELECT content_fingerprint FROM canon_state WHERE state_key=?1",
                    [format!("chapter:{}", dependency.record.chapter_id)],
                    |row| row.get(0),
                )
                .optional()
                .map_err(storage_error)?;
            if current_head.as_deref() != Some(dependency.canon_head_fingerprint.as_str()) {
                return Err(CoreError::AuthorityConflict(
                    "settled continuity changed before production activation".into(),
                ));
            }
            transaction.execute(
                "INSERT INTO chapter_dependencies(chapter_id,source_chapter_id,source_fingerprint,run_id,status,created_at,updated_at) \
                 VALUES(?1,?2,?3,?4,'current',?5,?5)",
                params![
                    target_chapter,
                    dependency.record.chapter_id,
                    dependency.canon_head_fingerprint,
                    request.run_id,
                    created_at
                ],
            ).map_err(storage_error)?;
        }
        transaction.commit().map_err(storage_error)
    }

    pub fn load_production_request(&self, run_id: &str) -> CoreResult<ProductionRequest> {
        let payload = self
            .connection
            .query_row(
                "SELECT request_json FROM production_executions WHERE run_id=?1",
                [run_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| CoreError::AuthorityConflict("production run is unavailable".into()))?;
        let request: ProductionRequest = serde_json::from_str(&payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        request.validate()?;
        Ok(request)
    }

    pub fn dispatch_stage(
        &mut self,
        run_id: &str,
        job: &StageJob,
        owner_token: &str,
        deadline_at_ms: u64,
        created_at: &str,
    ) -> CoreResult<String> {
        job.validate()?;
        require_timestamp(created_at)?;
        if owner_token.trim().is_empty() || deadline_at_ms == 0 || deadline_at_ms > i64::MAX as u64
        {
            return Err(CoreError::AuthorityConflict(
                "stage dispatch lease is incomplete".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let (request_json, cancel_requested): (String, bool) = transaction
            .query_row(
                "SELECT request_json,cancel_requested FROM production_executions WHERE run_id=?1",
                [run_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(storage_error)?;
        if cancel_requested {
            return Err(CoreError::AuthorityConflict(
                "production run is cancelled".into(),
            ));
        }
        let request: ProductionRequest = serde_json::from_str(&request_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        request.validate()?;
        let dispatched: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1",
                [run_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if request
            .model_call_budget
            .is_some_and(|budget| dispatched >= budget)
        {
            return Err(CoreError::AuthorityConflict(
                "production model call budget is exhausted".into(),
            ));
        }
        if let Some((call_id,input_fingerprint))=transaction.query_row("SELECT call_id,input_fingerprint FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2",params![run_id,job.stage_key],|row|Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?))).optional().map_err(storage_error)? {if input_fingerprint==job.input_fingerprint{return Ok(call_id);}return Err(CoreError::AuthorityConflict("stage key already binds different input".into()));}
        let call_id = format!("call-{}", uuid::Uuid::new_v4());
        let job_json = serde_json::to_string(job)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute("INSERT INTO production_stage_calls(call_id,run_id,stage_key,runtime_role,input_fingerprint,job_json,owner_token,state,deadline_at_ms,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,'dispatched',?8,?9,?9)",params![call_id,run_id,job.stage_key,job.runtime_role,job.input_fingerprint,job_json,owner_token,deadline_at_ms,created_at]).map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE runs SET status='executing',updated_at=?2 WHERE run_id=?1",
                params![run_id, created_at],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(call_id)
    }

    pub fn confirm_stage(
        &mut self,
        call_id: &str,
        result: &ModelResult,
        updated_at: &str,
    ) -> CoreResult<()> {
        result.validate()?;
        require_timestamp(updated_at)?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let (run_id, state, job_json, error_code): (String, String, String, Option<String>) = transaction
            .query_row(
                "SELECT run_id,state,job_json,error_code FROM production_stage_calls WHERE call_id=?1",
                [call_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .map_err(storage_error)?;
        if state == "confirmed" {
            let existing: String = transaction
                .query_row(
                    "SELECT result_fingerprint FROM production_stage_calls WHERE call_id=?1",
                    [call_id],
                    |row| row.get(0),
                )
                .map_err(storage_error)?;
            if existing == result.fingerprint {
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "confirmed stage result changed".into(),
            ));
        }
        if state != "dispatched"
            && !(state == "unconfirmed"
                && error_code.as_deref() == Some("model_transport_unconfirmed"))
        {
            return Err(CoreError::AuthorityConflict(
                "only dispatched stages can be confirmed".into(),
            ));
        }
        let job: StageJob = serde_json::from_str(&job_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        job.validate()?;
        if result.request_id != job.model_request.request_id {
            return Err(CoreError::AuthorityConflict(
                "model result does not bind the stage request".into(),
            ));
        }
        let result_json = serde_json::to_string(result)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute("UPDATE production_stage_calls SET state='confirmed',result_json=?2,result_fingerprint=?3,error_code=NULL,updated_at=?4 WHERE call_id=?1",params![call_id,result_json,result.fingerprint,updated_at]).map_err(storage_error)?;
        if let Some(cost_micros) = result.usage.cost_micros {
            let receipt_fingerprint = crate::fingerprint::sha256_fingerprint(
                format!("{call_id}:{}:{cost_micros}", result.fingerprint).as_bytes(),
            );
            transaction.execute("INSERT INTO production_billing_receipts(call_id,run_id,result_fingerprint,cost_micros,receipt_source,evidence_ref,evidence_fingerprint,receipt_fingerprint,created_at) VALUES(?1,?2,?3,?4,'provider_result','model_result',?3,?5,?6)",params![call_id,run_id,result.fingerprint,cost_micros,receipt_fingerprint,updated_at]).map_err(storage_error)?;
        }
        transaction.commit().map_err(storage_error)
    }

    #[allow(clippy::too_many_arguments)]
    pub fn confirm_derived_stage(
        &mut self,
        run_id: &str,
        job: &StageJob,
        result: &ModelResult,
        checkpoint_kind: &str,
        checkpoint_state: &serde_json::Value,
        artifact_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<()> {
        job.validate()?;
        result.validate()?;
        require_timestamp(created_at)?;
        require_sha256(artifact_fingerprint)?;
        if checkpoint_kind.trim().is_empty()
            || result.request_id != job.model_request.request_id
            || result.service_id != "quillframe-deterministic"
        {
            return Err(CoreError::AuthorityConflict(
                "derived stage binding is incomplete".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let request_exists: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM production_executions WHERE run_id=?1 AND cancel_requested=0",
                [run_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if request_exists != 1 {
            return Err(CoreError::AuthorityConflict(
                "derived stage run is unavailable or cancelled".into(),
            ));
        }
        if let Some((input_fingerprint, result_fingerprint)) = transaction
            .query_row(
                "SELECT input_fingerprint,result_fingerprint FROM production_stage_calls \
                 WHERE run_id=?1 AND stage_key=?2 AND state='confirmed'",
                params![run_id, job.stage_key],
                |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
            )
            .optional()
            .map_err(storage_error)?
        {
            if input_fingerprint == job.input_fingerprint
                && result_fingerprint == result.fingerprint
            {
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "derived stage changed after confirmation".into(),
            ));
        }
        let job_json = serde_json::to_string(job)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let result_json = serde_json::to_string(result)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let checkpoint_json = serde_json::to_string(checkpoint_state)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let call_id = format!("call-derived-{}", uuid::Uuid::new_v4());
        transaction.execute(
            "INSERT INTO production_stage_calls(call_id,run_id,stage_key,runtime_role,input_fingerprint,job_json,owner_token,state,deadline_at_ms,result_json,result_fingerprint,error_code,created_at,updated_at) \
             VALUES(?1,?2,?3,?4,?5,?6,'quillframe-core','confirmed',1,?7,?8,NULL,?9,?9)",
            params![call_id,run_id,job.stage_key,job.runtime_role,job.input_fingerprint,job_json,result_json,result.fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,?2,?3,?4,?5,?6)",
            params![format!("checkpoint-derived-{run_id}-{}",job.stage_key),run_id,checkpoint_kind,checkpoint_json,artifact_fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) \
             VALUES(?1,?2,'production_derived_stage_confirmed',?3,?4)",
            params![format!("event-{}",uuid::Uuid::new_v4()),run_id,
                serde_json::to_string(&serde_json::json!({"stage_key":job.stage_key,"result_fingerprint":result.fingerprint,"artifact_fingerprint":artifact_fingerprint}))
                    .map_err(|error|CoreError::Serialization(error.to_string()))?,created_at],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)
    }

    pub fn record_scene_checkpoint(
        &mut self,
        run_id: &str,
        stage_key: &str,
        scene_id: &str,
        stage_result_fingerprint: &str,
        manuscript_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<()> {
        require_sha256(stage_result_fingerprint)?;
        require_sha256(manuscript_fingerprint)?;
        require_timestamp(created_at)?;
        if stage_key.trim().is_empty() || scene_id.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "scene checkpoint identity is incomplete".into(),
            ));
        }
        let checkpoint_id = format!("checkpoint-scene-{run_id}-{stage_key}");
        let state = serde_json::to_string(&serde_json::json!({
            "schema":"quillframe_scene_checkpoint_v1",
            "scene_id":scene_id,
            "stage_key":stage_key,
            "stage_result_fingerprint":stage_result_fingerprint,
            "manuscript_fingerprint":manuscript_fingerprint
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((existing_state, existing_artifact)) = transaction
            .query_row(
                "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE checkpoint_id=?1",
                [&checkpoint_id],
                |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
            )
            .optional()
            .map_err(storage_error)?
        {
            if existing_state == state && existing_artifact == manuscript_fingerprint {
                return Ok(());
            }
            return Err(CoreError::AuthorityConflict(
                "scene checkpoint changed after confirmation".into(),
            ));
        }
        let confirmed: u32 = transaction.query_row(
            "SELECT COUNT(*) FROM production_stage_calls WHERE run_id=?1 AND stage_key=?2 AND state='confirmed' AND result_fingerprint=?3",
            params![run_id,stage_key,stage_result_fingerprint],|row|row.get(0)
        ).map_err(storage_error)?;
        if confirmed != 1 {
            return Err(CoreError::AuthorityConflict(
                "scene checkpoint requires its exact confirmed stage".into(),
            ));
        }
        transaction.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,?2,'scene_surface_confirmed',?3,?4,?5)",
            params![checkpoint_id,run_id,state,manuscript_fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)
    }

    pub fn mark_stage_unconfirmed(
        &mut self,
        call_id: &str,
        error_code: &str,
        updated_at: &str,
    ) -> CoreResult<()> {
        require_timestamp(updated_at)?;
        if error_code.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "unconfirmed stage requires an error code".into(),
            ));
        }
        let changed=self.connection.execute(
            "UPDATE production_stage_calls SET state='unconfirmed',error_code=?2,updated_at=?3 \
             WHERE call_id=?1 AND (state='dispatched' OR (state='unconfirmed' AND error_code=?2))",
            params![call_id,error_code,updated_at]
        ).map_err(storage_error)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "stage is not dispatch-pending".into(),
            ));
        }
        Ok(())
    }

    pub fn cancel_production(
        &mut self,
        run_id: &str,
        expected_cursor: u64,
        idempotency_key: &str,
        updated_at: &str,
    ) -> CoreResult<(u32, bool)> {
        require_timestamp(updated_at)?;
        if run_id.trim().is_empty() || idempotency_key.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "production cancellation identity is incomplete".into(),
            ));
        }
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some(payload) = transaction
            .query_row(
                "SELECT payload_json FROM receipts WHERE idempotency_key=?1 AND receipt_kind='production_cancelled'",
                [idempotency_key],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let value: serde_json::Value = serde_json::from_str(&payload)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            if value.get("run_id").and_then(serde_json::Value::as_str) == Some(run_id)
                && value.get("expected_cursor").and_then(serde_json::Value::as_u64)
                    == Some(expected_cursor)
            {
                return Ok((
                    value
                        .get("abandoned_call_count")
                        .and_then(serde_json::Value::as_u64)
                        .and_then(|value| u32::try_from(value).ok())
                        .unwrap_or(0),
                    true,
                ));
            }
            return Err(CoreError::AuthorityConflict(
                "production cancellation idempotency key binds different input".into(),
            ));
        }
        let cursor: u64 = transaction
            .query_row(
                "SELECT COUNT(*) FROM runtime_events WHERE run_id=?1",
                [run_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if cursor != expected_cursor {
            return Err(CoreError::AuthorityConflict(
                "production cancellation cursor changed".into(),
            ));
        }
        let released: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM candidates WHERE run_id=?1",
                [run_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if released != 0 {
            return Err(CoreError::AuthorityConflict(
                "a released candidate cannot be abandoned as an unknown model outcome".into(),
            ));
        }
        let abandoned = transaction
            .execute(
                "UPDATE production_stage_calls SET state='cancelled',error_code='author_abandoned_unknown_outcome',updated_at=?2 \
                 WHERE run_id=?1 AND state IN ('dispatched','unconfirmed')",
                params![run_id, updated_at],
            )
            .map_err(storage_error)?;
        let changed = transaction
            .execute(
                "UPDATE runs SET status='cancelled',updated_at=?2 WHERE run_id=?1 AND status!='cancelled'",
                params![run_id, updated_at],
            )
            .map_err(storage_error)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "production run is unavailable or already cancelled".into(),
            ));
        }
        transaction
            .execute(
                "UPDATE production_executions SET cancel_requested=1,updated_at=?2 WHERE run_id=?1",
                params![run_id, updated_at],
            )
            .map_err(storage_error)?;
        let abandoned = u32::try_from(abandoned)
            .map_err(|_| CoreError::ContextBoundary("abandoned call count exceeds u32".into()))?;
        let payload = serde_json::to_string(&serde_json::json!({
            "run_id":run_id,"expected_cursor":expected_cursor,"abandoned_call_count":abandoned
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) \
             VALUES(?1,?2,'production_abandoned',?3,?4)",
                params![
                    format!("event-{}", uuid::Uuid::new_v4()),
                    run_id,
                    payload,
                    updated_at
                ],
            )
            .map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) \
             VALUES(?1,'production_cancelled',?2,?3,?4)",
            params![format!("receipt-{}",uuid::Uuid::new_v4()),idempotency_key,payload,updated_at],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok((abandoned, false))
    }

    pub fn production_stage_calls(&self, run_id: &str) -> CoreResult<Vec<StageCall>> {
        let mut statement=self.connection.prepare("SELECT call_id,job_json,owner_token,state,deadline_at_ms,result_json,result_fingerprint,error_code FROM production_stage_calls WHERE run_id=?1 ORDER BY created_at,call_id").map_err(storage_error)?;
        let rows = statement
            .query_map([run_id], |row| {
                let job_json: String = row.get(1)?;
                let result_json: Option<String> = row.get(5)?;
                Ok((
                    row.get::<_, String>(0)?,
                    job_json,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, u64>(4)?,
                    result_json,
                    row.get::<_, Option<String>>(6)?,
                    row.get::<_, Option<String>>(7)?,
                ))
            })
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        rows.into_iter()
            .map(
                |(
                    call_id,
                    job_json,
                    owner_token,
                    state,
                    deadline_at_ms,
                    result_json,
                    result_fingerprint,
                    error_code,
                )| {
                    let job: StageJob = serde_json::from_str(&job_json)
                        .map_err(|error| CoreError::Storage(error.to_string()))?;
                    job.validate()?;
                    let result: Option<ModelResult> = result_json
                        .map(|json| {
                            serde_json::from_str(&json)
                                .map_err(|error| CoreError::Storage(error.to_string()))
                        })
                        .transpose()?;
                    if let Some(result) = &result {
                        result.validate()?;
                        if result_fingerprint.as_deref() != Some(result.fingerprint.as_str())
                            || result.request_id != job.model_request.request_id
                        {
                            return Err(CoreError::AuthorityConflict(
                                "persisted stage result binding changed".into(),
                            ));
                        }
                    } else if result_fingerprint.is_some() {
                        return Err(CoreError::AuthorityConflict(
                            "persisted stage result fingerprint has no artifact".into(),
                        ));
                    }
                    Ok(StageCall {
                        call_id,
                        run_id: run_id.into(),
                        job,
                        owner_token,
                        state: match state.as_str() {
                            "confirmed" => StageCallState::Confirmed,
                            "unconfirmed" => StageCallState::Unconfirmed,
                            "cancelled" => StageCallState::Cancelled,
                            _ => StageCallState::Dispatched,
                        },
                        deadline_at_ms,
                        result,
                        error_code,
                    })
                },
            )
            .collect()
    }

    pub fn production_stage_call(
        &self,
        run_id: &str,
        stage_key: &str,
    ) -> CoreResult<Option<StageCall>> {
        Ok(self
            .production_stage_calls(run_id)?
            .into_iter()
            .find(|call| call.job.stage_key == stage_key))
    }

    pub fn append_runtime_event(
        &mut self,
        run_id: &str,
        event_kind: &str,
        payload: &serde_json::Value,
        created_at: &str,
    ) -> CoreResult<String> {
        require_timestamp(created_at)?;
        if event_kind.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "runtime event kind is required".into(),
            ));
        }
        let event_id = format!("event-{}", uuid::Uuid::new_v4());
        let payload = serde_json::to_string(payload)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        self.connection
            .execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) \
                 VALUES(?1,?2,?3,?4,?5)",
                params![event_id, run_id, event_kind, payload, created_at],
            )
            .map_err(storage_error)?;
        Ok(event_id)
    }

    pub fn set_run_status(
        &mut self,
        run_id: &str,
        status: &str,
        result_fingerprint: Option<&str>,
        updated_at: &str,
    ) -> CoreResult<()> {
        require_timestamp(updated_at)?;
        if status.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "run status is required".into(),
            ));
        }
        if let Some(fingerprint) = result_fingerprint {
            require_sha256(fingerprint)?;
        }
        let changed = self
            .connection
            .execute(
                "UPDATE runs SET status=?2,result_fingerprint=?3,updated_at=?4 WHERE run_id=?1",
                params![run_id, status, result_fingerprint, updated_at],
            )
            .map_err(storage_error)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "production run is unavailable".into(),
            ));
        }
        Ok(())
    }

    pub fn runtime_events(&self, run_id: &str) -> CoreResult<Vec<serde_json::Value>> {
        let mut statement = self
            .connection
            .prepare(
                "SELECT event_kind,payload_json,created_at FROM runtime_events \
                 WHERE run_id=?1 ORDER BY created_at,event_id",
            )
            .map_err(storage_error)?;
        let rows = statement
            .query_map([run_id], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            })
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        rows.into_iter()
            .map(|(event_kind, payload, created_at)| {
                let payload: serde_json::Value = serde_json::from_str(&payload)
                    .map_err(|error| CoreError::Storage(error.to_string()))?;
                Ok(serde_json::json!({
                    "event_kind":event_kind,"payload":payload,"created_at":created_at
                }))
            })
            .collect()
    }

    pub fn record_failed_gate(
        &mut self,
        run_id: &str,
        candidate_fingerprint: &str,
        mechanism: &str,
        stage_result_fingerprint: &str,
        created_at: &str,
    ) -> CoreResult<String> {
        require_timestamp(created_at)?;
        require_sha256(candidate_fingerprint)?;
        require_sha256(stage_result_fingerprint)?;
        if mechanism.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "failed gate mechanism is required".into(),
            ));
        }
        let production = self.load_production_request(run_id)?;
        let revision = if production.task_mode == ProductionTaskMode::Draft {
            1_u64
        } else {
            let binding = production.intent.repair_source.as_ref().ok_or_else(|| {
                CoreError::AuthorityConflict("failed REVISE run lost its repair source".into())
            })?;
            let source_state:String=self.connection.query_row(
                "SELECT state_json FROM checkpoints WHERE checkpoint_id=?1 AND run_id=?2 \
                 AND checkpoint_kind IN ('failed_candidate_repair_source','author_revision_repair_source')",
                params![binding.source_checkpoint_id,binding.source_run_id],|row|row.get(0)
            ).map_err(storage_error)?;
            let value: serde_json::Value = serde_json::from_str(&source_state)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            value
                .get("revision")
                .and_then(serde_json::Value::as_u64)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("repair source has no revision ordinal".into())
                })?
                .checked_add(1)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("repair revision ordinal overflowed".into())
                })?
        };
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        let checkpoint_id = format!("checkpoint-{}", uuid::Uuid::new_v4());
        let payload = serde_json::to_string(&serde_json::json!({
            "candidate_fingerprint":candidate_fingerprint,
            "mechanism":mechanism,
            "revision":revision,
            "stage_result_fingerprint":stage_result_fingerprint
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,?2,'failed_candidate_repair_source',?3,?4,?5)",
            params![checkpoint_id,run_id,payload,candidate_fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction.execute(
            "UPDATE runs SET status='failed_gate',result_fingerprint=?2,updated_at=?3 WHERE run_id=?1",
            params![run_id,stage_result_fingerprint,created_at],
        ).map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) \
             VALUES(?1,?2,'production_gate_rejected',?3,?4)",
                params![
                    format!("event-{}", uuid::Uuid::new_v4()),
                    run_id,
                    payload,
                    created_at
                ],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(checkpoint_id)
    }

    pub fn validate_repair_source(
        &self,
        source_run_id: &str,
        checkpoint_id: &str,
        candidate_fingerprint: &str,
        target_document_id: &str,
    ) -> CoreResult<ProductionRequest> {
        require_sha256(candidate_fingerprint)?;
        let (artifact_fingerprint, checkpoint_kind, state_json): (String, String, String) = self
            .connection
            .query_row(
                "SELECT artifact_fingerprint,checkpoint_kind,state_json FROM checkpoints \
                 WHERE checkpoint_id=?1 AND run_id=?2",
                params![checkpoint_id, source_run_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .map_err(storage_error)?;
        if !matches!(
            checkpoint_kind.as_str(),
            "failed_candidate_repair_source" | "author_revision_repair_source"
        ) || artifact_fingerprint != candidate_fingerprint
        {
            return Err(CoreError::AuthorityConflict(
                "repair source checkpoint does not bind the failed candidate".into(),
            ));
        }
        let source = self.load_production_request(source_run_id)?;
        let status: String = self
            .connection
            .query_row(
                "SELECT status FROM runs WHERE run_id=?1",
                [source_run_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let status_valid = checkpoint_kind == "failed_candidate_repair_source"
            && status == "failed_gate"
            || checkpoint_kind == "author_revision_repair_source" && status == "review";
        if !status_valid || source.target_ref != target_document_id {
            return Err(CoreError::AuthorityConflict(
                "repair source is not the failed run for this document".into(),
            ));
        }
        if checkpoint_kind == "author_revision_repair_source" {
            let state: serde_json::Value = serde_json::from_str(&state_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let candidate_id = state
                .get("candidate_id")
                .and_then(serde_json::Value::as_str)
                .ok_or_else(|| {
                    CoreError::AuthorityConflict("author repair checkpoint has no candidate".into())
                })?;
            let valid:u64=self.connection.query_row(
                "SELECT COUNT(*) FROM candidates c JOIN document_revisions r ON r.revision_id=c.revision_id \
                 JOIN candidate_revision_requests q ON q.candidate_id=c.candidate_id \
                 WHERE c.candidate_id=?1 AND c.run_id=?2 AND c.document_id=?3 AND c.content_fingerprint=?4 \
                 AND r.content_fingerprint=?4 AND q.state='requested'",
                params![candidate_id,source_run_id,target_document_id,candidate_fingerprint],|row|row.get(0)
            ).map_err(storage_error)?;
            if valid != 1 {
                return Err(CoreError::AuthorityConflict(
                    "author repair checkpoint is stale".into(),
                ));
            }
        }
        Ok(source)
    }

    pub fn validated_repair_lineage_run_ids(
        &self,
        request: &ProductionRequest,
    ) -> CoreResult<Vec<String>> {
        request.validate()?;
        let mut lineage = Vec::new();
        let mut seen = BTreeSet::from([request.run_id.clone()]);
        let mut current = request.clone();
        while let Some(binding) = current.intent.repair_source.as_ref() {
            if !seen.insert(binding.source_run_id.clone()) {
                return Err(CoreError::AuthorityConflict(
                    "repair source lineage contains a cycle".into(),
                ));
            }
            let source = self.validate_repair_source(
                &binding.source_run_id,
                &binding.source_checkpoint_id,
                &binding.expected_candidate_fingerprint,
                &request.target_ref,
            )?;
            lineage.push(binding.source_run_id.clone());
            current = source;
        }
        Ok(lineage)
    }

    pub fn resolve_bounded_repair_evidence(
        &self,
        request: &ProductionRequest,
    ) -> CoreResult<(String, BTreeMap<String, String>)> {
        const MAX_REPAIR_LINEAGE_DEPTH: usize = 128;
        request.validate()?;
        let pack = self.load_writer_pack(&request.writer_pack_fingerprint)?;
        let expected_scene_keys = pack
            .scenes
            .iter()
            .map(|scene| format!("surface_scene_{:04}_{}", scene.ordinal, scene.scene_id))
            .collect::<Vec<_>>();
        let mut seen = BTreeSet::from([request.run_id.clone()]);
        let mut current = request.clone();
        for _ in 0..MAX_REPAIR_LINEAGE_DEPTH {
            let binding = current.intent.repair_source.as_ref().ok_or_else(|| {
                CoreError::AuthorityConflict(
                    "bounded repair lineage ended before a fresh realization".into(),
                )
            })?;
            if !seen.insert(binding.source_run_id.clone()) {
                return Err(CoreError::AuthorityConflict(
                    "repair source lineage contains a cycle".into(),
                ));
            }
            let source = self.validate_repair_source(
                &binding.source_run_id,
                &binding.source_checkpoint_id,
                &binding.expected_candidate_fingerprint,
                &request.target_ref,
            )?;
            if source.writer_pack_fingerprint != request.writer_pack_fingerprint {
                return Err(CoreError::AuthorityConflict(
                    "bounded repair lineage changed its Writer Pack".into(),
                ));
            }
            let calls = self.production_stage_calls(&source.run_id)?;
            let surface = confirmed_stage_result(&calls, "surface_realization")?;
            let surface_output: SurfaceRealization = serde_json::from_str(&surface.content)
                .map_err(|error| CoreError::Serialization(error.to_string()))?;
            surface_output.validate()?;
            if crate::fingerprint::sha256_fingerprint(surface_output.manuscript.as_bytes())
                != binding.expected_candidate_fingerprint
            {
                return Err(CoreError::AuthorityConflict(
                    "repair lineage surface does not bind its candidate".into(),
                ));
            }
            if let Some(bounded) = calls
                .iter()
                .find(|call| call.job.stage_key == "bounded_repair_surface")
            {
                if bounded.state != StageCallState::Confirmed || bounded.result.is_none() {
                    return Err(CoreError::AuthorityConflict(
                        "bounded repair lineage has unconfirmed repair evidence".into(),
                    ));
                }
                current = source;
                continue;
            }

            let actual_scene_keys = calls
                .iter()
                .filter(|call| call.job.stage_key.starts_with("surface_scene_"))
                .map(|call| call.job.stage_key.clone())
                .collect::<Vec<_>>();
            if actual_scene_keys != expected_scene_keys {
                return Err(CoreError::AuthorityConflict(
                    "fresh repair origin scene evidence does not match its Writer Pack".into(),
                ));
            }
            let mut receipts = BTreeMap::new();
            for stage_key in ["character_simulation", "scene_resolution"] {
                let result = confirmed_stage_result(&calls, stage_key)?;
                receipts.insert(stage_key.into(), result.fingerprint.clone());
            }
            let mut scene_manuscripts = Vec::with_capacity(expected_scene_keys.len());
            for (stage_key, scene_brief) in expected_scene_keys.iter().zip(&pack.scenes) {
                let result = confirmed_stage_result(&calls, stage_key)?;
                let value = serde_json::from_str(&result.content)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?;
                let scene = crate::semantic::parse_surface_realization_value(
                    value,
                    &pack.chapter_id,
                    &scene_brief.scene_id,
                )?;
                scene.validate()?;
                scene_manuscripts.push(scene.manuscript.trim().to_string());
                receipts.insert(stage_key.clone(), result.fingerprint.clone());
            }
            if scene_manuscripts.join("\n\n") != surface_output.manuscript {
                return Err(CoreError::AuthorityConflict(
                    "fresh repair origin surface assembly changed".into(),
                ));
            }
            let manifest: serde_json::Value = serde_json::from_str(
                &calls
                    .iter()
                    .find(|call| call.job.stage_key == "surface_realization")
                    .ok_or_else(|| {
                        CoreError::AuthorityConflict(
                            "fresh repair origin has no surface assembly".into(),
                        )
                    })?
                    .job
                    .model_request
                    .user,
            )
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
            let manifest_receipts: BTreeMap<String, String> = serde_json::from_value(
                manifest.get("scene_receipts").cloned().ok_or_else(|| {
                    CoreError::AuthorityConflict(
                        "fresh repair origin assembly lost scene receipts".into(),
                    )
                })?,
            )
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
            if manifest.get("schema").and_then(serde_json::Value::as_str)
                != Some("quillframe_surface_assembly_v1")
                || manifest
                    .get("separator")
                    .and_then(serde_json::Value::as_str)
                    != Some("\\n\\n")
            {
                return Err(CoreError::AuthorityConflict(
                    "fresh repair origin assembly manifest identity changed".into(),
                ));
            }
            if manifest
                .get("manuscript_fingerprint")
                .and_then(serde_json::Value::as_str)
                != Some(binding.expected_candidate_fingerprint.as_str())
            {
                return Err(CoreError::AuthorityConflict(
                    "fresh repair origin assembly manuscript fingerprint changed".into(),
                ));
            }
            if manifest_receipts != receipts {
                return Err(CoreError::AuthorityConflict(
                    "fresh repair origin assembly receipts changed".into(),
                ));
            }
            return Ok((source.run_id, receipts));
        }
        Err(CoreError::AuthorityConflict(
            "repair source lineage exceeds the supported depth".into(),
        ))
    }

    pub fn request_candidate_revision(
        &mut self,
        request: &RevisionRequest,
    ) -> CoreResult<(String, String, String, bool)> {
        request.validate()?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some((id,candidate_id,candidate_fingerprint,requested_by,reason)) = transaction
            .query_row(
                "SELECT request_id,candidate_id,candidate_fingerprint,requested_by,reason FROM candidate_revision_requests \
                 WHERE idempotency_key=?1",
                [&request.idempotency_key],
                |row| Ok((row.get::<_,String>(0)?,row.get::<_,String>(1)?,row.get::<_,String>(2)?,
                    row.get::<_,String>(3)?,row.get::<_,String>(4)?)),
            )
            .optional()
            .map_err(storage_error)?
        {
            if candidate_id == request.candidate_id
                && candidate_fingerprint == request.candidate_fingerprint
                && requested_by == request.requested_by
                && reason == request.reason
            {
                let (document_id,run_id):(String,String)=transaction.query_row(
                    "SELECT document_id,run_id FROM candidates WHERE candidate_id=?1 AND content_fingerprint=?2",
                    params![candidate_id,candidate_fingerprint],|row|Ok((row.get(0)?,row.get(1)?))
                ).map_err(storage_error)?;
                let event_id = format!("feedback-revision-{id}");
                let event = serde_json::json!({
                    "event_id":&event_id,"feedback_text":reason,"evidence_kind":"author_revision",
                    "candidate_id":candidate_id,"candidate_fingerprint":candidate_fingerprint,
                    "document_id":document_id,"run_id":run_id,
                    "source_type":"candidate_revision_request","source_id":&id
                });
                let (_, feedback_replayed) =
                    insert_learning_feedback(&transaction, &event, &request.created_at)?;
                transaction.commit().map_err(storage_error)?;
                return Ok((
                    id.clone(),
                    format!("checkpoint-author-revision-{id}"),
                    event_id,
                    feedback_replayed,
                ));
            }
            return Err(CoreError::AuthorityConflict(
                "revision idempotency key binds a different request".into(),
            ));
        }
        let (status, fingerprint, run_id, document_id, lineage_json) = transaction
            .query_row(
                "SELECT c.status,c.content_fingerprint,c.run_id,c.document_id,l.lineage_json FROM candidates c \
                 JOIN candidate_lineage l ON l.candidate_id=c.candidate_id WHERE c.candidate_id=?1",
                [&request.candidate_id],
                |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                    ))
                },
            )
            .map_err(storage_error)?;
        if status != "review_draft" || fingerprint != request.candidate_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "revision request candidate is stale or not reviewable".into(),
            ));
        }
        let accepted: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM acceptance_evidence WHERE candidate_id=?1",
                [&request.candidate_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if accepted != 0 {
            return Err(CoreError::AuthorityConflict(
                "accepted candidate cannot receive a revision request".into(),
            ));
        }
        let request_id = request.request_id.to_string();
        let lineage: CandidateArtifact = serde_json::from_str(&lineage_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        lineage.validate()?;
        let checkpoint_id = format!("checkpoint-author-revision-{request_id}");
        transaction
            .execute(
                "INSERT INTO candidate_revision_requests( \
                 request_id,candidate_id,candidate_fingerprint,request_fingerprint,idempotency_key, \
                 requested_by,reason,state,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,'requested',?8)",
                params![
                    request_id,
                    request.candidate_id,
                    request.candidate_fingerprint,
                    request.fingerprint,
                    request.idempotency_key,
                    request.requested_by,
                    request.reason,
                    request.created_at
                ],
            )
            .map_err(storage_error)?;
        let checkpoint_state=serde_json::to_string(&serde_json::json!({"source_kind":"author_revision_request",
            "candidate_id":request.candidate_id,"revision_request_id":request_id,"revision":lineage.revision,
            "mechanism":"author_revision_request","instruction":request.reason}))
            .map_err(|error|CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,?2,'author_revision_repair_source',?3,?4,?5)",
            params![checkpoint_id,run_id,checkpoint_state,request.candidate_fingerprint,request.created_at]
        ).map_err(storage_error)?;
        let feedback_event_id = format!("feedback-revision-{request_id}");
        let feedback_event = serde_json::json!({
            "event_id":&feedback_event_id,"feedback_text":request.reason,
            "evidence_kind":"author_revision","candidate_id":request.candidate_id,
            "candidate_fingerprint":request.candidate_fingerprint,"document_id":document_id,
            "run_id":run_id,"source_type":"candidate_revision_request","source_id":&request_id
        });
        let (_, feedback_replayed) =
            insert_learning_feedback(&transaction, &feedback_event, &request.created_at)?;
        transaction.commit().map_err(storage_error)?;
        Ok((
            request_id,
            checkpoint_id,
            feedback_event_id,
            feedback_replayed,
        ))
    }

    pub fn accept_candidate(&mut self, decision: &AcceptanceDecision) -> CoreResult<String> {
        decision.validate()?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some(payload) = transaction
            .query_row(
                "SELECT payload_json FROM receipts WHERE idempotency_key=?1",
                [&decision.idempotency_key],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let prior: AcceptanceDecision = serde_json::from_str(&payload)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            if prior.fingerprint == decision.fingerprint {
                return Ok(prior.acceptance_id.to_string());
            }
            return Err(CoreError::AuthorityConflict(
                "acceptance idempotency key binds a different decision".into(),
            ));
        }
        let (status, fingerprint) = transaction
            .query_row(
                "SELECT status,content_fingerprint FROM candidates WHERE candidate_id=?1",
                [&decision.candidate_id],
                |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
            )
            .map_err(storage_error)?;
        if status != "review_draft" || fingerprint != decision.candidate_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "candidate is stale or not reviewable".into(),
            ));
        }
        let revisions: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM candidate_revision_requests \
                 WHERE candidate_id=?1 AND state='requested'",
                [&decision.candidate_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if revisions != 0 {
            return Err(CoreError::AuthorityConflict(
                "candidate has an actionable revision request".into(),
            ));
        }
        let review_ok: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM structured_review_reports \
                 WHERE report_fingerprint=?1 AND candidate_fingerprint=?2 \
                 AND decision='accept' AND independent_context=1",
                params![
                    decision.review_report_fingerprint,
                    decision.candidate_fingerprint
                ],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if review_ok != 1 {
            return Err(CoreError::AuthorityConflict(
                "acceptance requires one fresh independent accept report".into(),
            ));
        }
        let release_ok: u32 = transaction
            .query_row(
                "SELECT COUNT(*) FROM production_releases WHERE candidate_id=?1 AND candidate_fingerprint=?2 \
                 AND review_report_fingerprint=?3 AND user_visible=1",
                params![decision.candidate_id,decision.candidate_fingerprint,decision.review_report_fingerprint],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        if release_ok != 1 {
            return Err(CoreError::AuthorityConflict(
                "acceptance requires one exact production release".into(),
            ));
        }
        let acceptance_id = decision.acceptance_id.to_string();
        let authorization_json = serde_json::to_string(decision)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO acceptance_evidence( \
                 acceptance_id,candidate_id,candidate_fingerprint,authorized_by,authorization_json,created_at \
                 ) VALUES(?1,?2,?3,?4,?5,?6)",
                params![
                    acceptance_id,
                    decision.candidate_id,
                    decision.candidate_fingerprint,
                    decision.authorized_by,
                    authorization_json,
                    decision.created_at
                ],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "UPDATE candidates SET status='accepted' WHERE candidate_id=?1",
                [&decision.candidate_id],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) \
                 VALUES(?1,'candidate_acceptance',?2,?3,?4)",
                params![
                    format!("receipt-{acceptance_id}"),
                    decision.idempotency_key,
                    authorization_json,
                    decision.created_at
                ],
            )
            .map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(acceptance_id)
    }

    pub fn settlement_preflight(
        &self,
        acceptance_id: &str,
        target_ref: &str,
        created_at: &str,
    ) -> CoreResult<SettlementPreflight> {
        require_timestamp(created_at)?;
        settlement_preflight_from_connection(
            &self.connection,
            acceptance_id,
            target_ref,
            created_at,
        )
    }

    pub fn apply_settlement(
        &mut self,
        authorization: &SettlementAuthorization,
    ) -> CoreResult<String> {
        authorization.validate()?;
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage_error)?;
        if let Some(payload) = transaction
            .query_row(
                "SELECT payload_json FROM receipts WHERE idempotency_key=?1",
                [&authorization.idempotency_key],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
        {
            let prior: SettlementAuthorization = serde_json::from_str(&payload)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            if prior.fingerprint == authorization.fingerprint {
                return Ok(prior.settlement_id.to_string());
            }
            return Err(CoreError::AuthorityConflict(
                "settlement idempotency key binds a different authorization".into(),
            ));
        }
        let preflight = settlement_preflight_from_connection(
            &transaction,
            &authorization.acceptance_id,
            &authorization.target_ref,
            &authorization.created_at,
        )?;
        if preflight.fingerprint != authorization.preflight_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "settlement authorization does not match the current preflight".into(),
            ));
        }
        if preflight.before_fingerprint != authorization.expected_before_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "Canon changed after settlement preflight".into(),
            ));
        }
        let (document_id, run_id, chapter_id): (String, Option<String>, String) = transaction
            .query_row(
                "SELECT c.document_id,c.run_id,d.story_node_id FROM candidates c \
                 JOIN documents d ON d.document_id=c.document_id WHERE c.candidate_id=?1",
                [&preflight.candidate_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .map_err(storage_error)?;
        if let Some(production_run_id) = run_id.as_deref() {
            let mut dependency_statement = transaction
                .prepare(
                    "SELECT source_chapter_id,source_fingerprint,status FROM chapter_dependencies \
                 WHERE run_id=?1",
                )
                .map_err(storage_error)?;
            let dependencies = dependency_statement
                .query_map([production_run_id], |row| {
                    Ok((
                        row.get::<_, String>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                    ))
                })
                .map_err(storage_error)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)?;
            drop(dependency_statement);
            for (source_chapter_id, expected_head, status) in dependencies {
                let current_head = transaction
                    .query_row(
                        "SELECT content_fingerprint FROM canon_state WHERE state_key=?1",
                        [format!("chapter:{source_chapter_id}")],
                        |row| row.get::<_, String>(0),
                    )
                    .optional()
                    .map_err(storage_error)?;
                if status != "current" || current_head.as_deref() != Some(expected_head.as_str()) {
                    return Err(CoreError::AuthorityConflict(
                        "production dependency changed before settlement".into(),
                    ));
                }
            }
        }
        let reading_order: u64 = transaction.query_row(
            "SELECT COUNT(*) FROM story_nodes c2 JOIN story_nodes u2 ON u2.node_id=c2.parent_id \
             JOIN story_nodes v2 ON v2.node_id=u2.parent_id JOIN story_nodes c ON c.node_id=?1 \
             JOIN story_nodes u ON u.node_id=c.parent_id JOIN story_nodes v ON v.node_id=u.parent_id \
             WHERE c2.kind='chapter' AND (v2.ordinal<v.ordinal OR (v2.ordinal=v.ordinal AND \
             (u2.ordinal<u.ordinal OR (u2.ordinal=u.ordinal AND (c2.ordinal<c.ordinal OR \
             (c2.ordinal=c.ordinal AND c2.node_id<=c.node_id))))))",
            [&chapter_id],|row|row.get(0)
        ).map_err(storage_error)?;
        let production_run_id = run_id.as_deref().ok_or_else(|| {
            CoreError::AuthorityConflict(
                "settlement requires a production run with tracking evidence".into(),
            )
        })?;
        let (tracking_result_json, tracking_result_fingerprint): (String, String) = transaction
            .query_row(
                "SELECT result_json,result_fingerprint FROM production_stage_calls \
                 WHERE run_id=?1 AND state='confirmed' AND stage_key IN \
                 ('settlement_tracking_projection','settlement_tracking_projection_schema_repair', \
                  'settlement_tracking_projection_semantic_repair','settlement_tracking_projection_audit_repair', \
                  'settlement_tracking_projection_audit_repair_2','settlement_tracking_projection_audit_repair_3') \
                  ORDER BY CASE stage_key WHEN 'settlement_tracking_projection_audit_repair_3' THEN 0 \
                  WHEN 'settlement_tracking_projection_audit_repair_2' THEN 1 \
                  WHEN 'settlement_tracking_projection_audit_repair' THEN 2 \
                  WHEN 'settlement_tracking_projection_semantic_repair' THEN 3 \
                  WHEN 'settlement_tracking_projection_schema_repair' THEN 4 ELSE 5 END LIMIT 1",
                [production_run_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(storage_error)?;
        let (release_tracking_fingerprint, stage_receipts_json): (String, String) = transaction
            .query_row(
                "SELECT tracking_fingerprint,stage_receipt_fingerprints_json FROM production_releases \
                 WHERE candidate_id=?1 AND candidate_fingerprint=?2 AND user_visible=1",
                params![preflight.candidate_id, preflight.candidate_fingerprint],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .map_err(storage_error)?;
        let stage_receipts: BTreeMap<String, String> =
            serde_json::from_str(&stage_receipts_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
        if stage_receipts.get("settlement_tracking_projection")
            != Some(&tracking_result_fingerprint)
        {
            return Err(CoreError::AuthorityConflict(
                "settlement tracking proposal is not bound to the released candidate".into(),
            ));
        }
        let tracking_result: ModelResult = serde_json::from_str(&tracking_result_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        tracking_result.validate()?;
        if tracking_result.fingerprint != tracking_result_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "settlement tracking result fingerprint changed".into(),
            ));
        }
        let tracking_proposal: crate::ChapterTrackingProposal =
            serde_json::from_str(&tracking_result.content)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
        tracking_proposal.validate()?;
        let manuscript: String = transaction
            .query_row(
                "SELECT content FROM document_revisions WHERE revision_id=?1",
                [&preflight.revision_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let evidence_excerpts = tracking_proposal
            .entity_deltas
            .iter()
            .map(|delta| delta.evidence_excerpt.as_str())
            .chain(
                tracking_proposal
                    .relationship_deltas
                    .iter()
                    .map(|delta| delta.evidence_excerpt.as_str()),
            )
            .chain(
                tracking_proposal
                    .knowledge_deltas
                    .iter()
                    .map(|delta| delta.evidence_excerpt.as_str()),
            )
            .chain(
                tracking_proposal
                    .timeline_deltas
                    .iter()
                    .map(|delta| delta.evidence_excerpt.as_str()),
            )
            .chain(
                tracking_proposal
                    .expectation_deltas
                    .iter()
                    .map(|delta| delta.evidence_excerpt.as_str()),
            );
        if evidence_excerpts
            .into_iter()
            .any(|excerpt| !manuscript.contains(excerpt))
        {
            return Err(CoreError::AuthorityConflict(
                "narrative state delta evidence is absent from the accepted manuscript".into(),
            ));
        }
        let project_id: String = transaction
            .query_row("SELECT project_id FROM project_identity", [], |row| {
                row.get(0)
            })
            .map_err(storage_error)?;
        let tracking_payload: String = transaction
            .query_row(
                "SELECT payload_json FROM story_tracking_authority WHERE project_id=?1",
                [&project_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        let tracking_state: TrackingState = serde_json::from_str(&tracking_payload)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        tracking_state.validate()?;
        if tracking_state.fingerprint != release_tracking_fingerprint {
            return Err(CoreError::AuthorityConflict(
                "tracking authority changed after candidate generation".into(),
            ));
        }
        let reading_order = u32::try_from(reading_order)
            .map_err(|_| CoreError::ContextBoundary("chapter reading order exceeds u32".into()))?;
        let tracking_record = crate::ChapterTrackingRecord {
            chapter_id: chapter_id.clone(),
            reading_order,
            net_change: tracking_proposal.net_change.clone(),
            open_expectations: tracking_proposal.open_expectations.clone(),
            paid_expectations: tracking_proposal.paid_expectations.clone(),
            relationship_changes: tracking_proposal.relationship_changes.clone(),
            state_changes: tracking_proposal.state_changes.clone(),
            next_pull: tracking_proposal.next_pull.clone(),
            source_candidate_fingerprint: preflight.candidate_fingerprint.clone(),
        };
        tracking_record.validate()?;
        let tracking_version = tracking_state.version;
        let tracking_before = tracking_state.fingerprint.clone();
        let mut tracking_ledger = crate::TrackingLedger::new(tracking_state)?;
        tracking_ledger.transact(tracking_version, &tracking_before, |next| {
            next.chapters
                .insert(chapter_id.clone(), tracking_record.clone());
            for (character, snapshot) in &tracking_proposal.character_snapshot_updates {
                next.character_snapshots
                    .insert(character.clone(), snapshot.clone());
            }
            next.invalidated_chapters.remove(&chapter_id);
            Ok(())
        })?;
        let mut next_tracking = tracking_ledger.current().clone();
        let mut newly_invalidated = BTreeSet::new();
        let prior_candidate_fingerprint = transaction
            .query_row(
                "SELECT value_json FROM canon_state WHERE state_key=?1",
                [&preflight.target_ref],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .map(|payload| {
                serde_json::from_str::<serde_json::Value>(&payload)
                    .map_err(|error| CoreError::Storage(error.to_string()))?
                    .get("content_fingerprint")
                    .and_then(serde_json::Value::as_str)
                    .map(str::to_owned)
                    .ok_or_else(|| {
                        CoreError::Storage(
                            "existing chapter Canon head lacks its candidate fingerprint".into(),
                        )
                    })
            })
            .transpose()?;
        let state_value = serde_json::json!({
            "acceptance_id": preflight.acceptance_id,
            "candidate_id": preflight.candidate_id,
            "chapter_id":chapter_id,
            "content_fingerprint":preflight.candidate_fingerprint,
            "document_id":document_id,
            "reading_order":reading_order,
            "revision_id": preflight.revision_id,
            "run_id":run_id,
        });
        let state_json = serde_json::to_string(&state_value)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let after_head_fingerprint = crate::fingerprint::sha256_fingerprint(state_json.as_bytes());
        apply_narrative_deltas(
            &transaction,
            &tracking_proposal,
            &chapter_id,
            &preflight.acceptance_id,
            &preflight.candidate_fingerprint,
            reading_order,
            &authorization.created_at,
        )?;
        transaction
            .execute(
                "INSERT INTO canon_state( \
                 state_key,value_json,authority_class,evidence_ref,content_fingerprint,updated_at \
                 ) VALUES(?1,?2,'accepted',?3,?4,?5) \
                 ON CONFLICT(state_key) DO UPDATE SET value_json=excluded.value_json, \
                 authority_class='accepted',evidence_ref=excluded.evidence_ref, \
                 content_fingerprint=excluded.content_fingerprint,updated_at=excluded.updated_at",
                params![
                    preflight.target_ref,
                    state_json,
                    preflight.acceptance_id,
                    after_head_fingerprint,
                    authorization.created_at
                ],
            )
            .map_err(storage_error)?;
        let settlement_id = authorization.settlement_id.to_string();
        let receipt_json = serde_json::to_string(authorization)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO settlements( \
                 settlement_id,acceptance_id,target_ref,before_fingerprint,after_fingerprint, \
                 state_delta_json,status,receipt_json,created_at,completed_at \
                 ) VALUES(?1,?2,?3,?4,?5,?6,'settled',?7,?8,?8)",
                params![
                    settlement_id,
                    preflight.acceptance_id,
                    preflight.target_ref,
                    preflight.before_fingerprint,
                    after_head_fingerprint,
                    state_json,
                    receipt_json,
                    authorization.created_at
                ],
            )
            .map_err(storage_error)?;
        transaction.execute(
            "UPDATE document_revisions SET authority_class='accepted' WHERE revision_id=?1 AND content_fingerprint=?2",
            params![preflight.revision_id,preflight.candidate_fingerprint],
        ).map_err(storage_error)?;
        let document_title: String = transaction
            .query_row(
                "SELECT title FROM documents WHERE document_id=?1",
                [&document_id],
                |row| row.get(0),
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "DELETE FROM search_index WHERE entity_type='document' AND entity_id=?1",
                [&document_id],
            )
            .map_err(storage_error)?;
        transaction.execute(
            "INSERT INTO search_index(entity_type,entity_id,title,body) VALUES('document',?1,?2,?3)",
            params![document_id,document_title,manuscript],
        ).map_err(storage_error)?;
        if preflight.before_fingerprint != crate::fingerprint::sha256_fingerprint([])
            && preflight.before_fingerprint != after_head_fingerprint
        {
            let mut affected_statement=transaction.prepare(
                "SELECT chapter_id,run_id FROM chapter_dependencies WHERE source_chapter_id=?1 \
                 AND source_fingerprint=?2 AND status='current'"
            ).map_err(storage_error)?;
            let affected = affected_statement
                .query_map(params![chapter_id, preflight.before_fingerprint], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
                })
                .map_err(storage_error)?
                .collect::<Result<Vec<_>, _>>()
                .map_err(storage_error)?;
            drop(affected_statement);
            transaction.execute(
                "UPDATE chapter_dependencies SET status='stale',updated_at=?3 WHERE source_chapter_id=?1 AND source_fingerprint=?2 AND status='current'",
                params![chapter_id,preflight.before_fingerprint,authorization.created_at],
            ).map_err(storage_error)?;
            for (affected_chapter_id, affected_run_id) in affected {
                newly_invalidated.insert(affected_chapter_id.clone());
                transaction.execute(
                    "UPDATE context_freezes SET status='stale_conflict' WHERE run_id=?1 AND status='frozen'",
                    [&affected_run_id],
                ).map_err(storage_error)?;
                transaction.execute(
                    "INSERT OR IGNORE INTO downstream_impacts(impact_id,source_chapter_id,old_fingerprint,new_fingerprint,affected_chapter_id,owner_layer,status,created_at,updated_at) \
                     VALUES(?1,?2,?3,?4,?5,'continuity','open',?6,?6)",
                    params![format!("impact-{}",uuid::Uuid::new_v4()),chapter_id,preflight.before_fingerprint,
                        after_head_fingerprint,affected_chapter_id,authorization.created_at],
                ).map_err(storage_error)?;
            }
            transaction.execute(
                "UPDATE reader_expectation_observations SET state='invalidated',updated_at=?3 WHERE observation_id IN ( \
                 SELECT observation_id FROM reader_observation_sources WHERE source_chapter_id=?1 AND source_fingerprint=?2) \
                 AND state IN ('proposed','applied')",
                params![chapter_id,preflight.before_fingerprint,authorization.created_at],
            ).map_err(storage_error)?;
            if let Some(prior_candidate_fingerprint) = prior_candidate_fingerprint.as_deref() {
                transaction.execute(
                    "UPDATE narrative_state_sources SET state='stale',updated_at=?3 WHERE chapter_id=?1 AND source_fingerprint=?2 AND state='current'",
                    params![chapter_id,prior_candidate_fingerprint,authorization.created_at],
                ).map_err(storage_error)?;
            }
        }
        if !newly_invalidated.is_empty() {
            let version = next_tracking.version;
            let fingerprint = next_tracking.fingerprint.clone();
            let mut ledger = crate::TrackingLedger::new(next_tracking)?;
            next_tracking = ledger
                .transact(version, &fingerprint, |state| {
                    state.invalidated_chapters.extend(newly_invalidated);
                    Ok(())
                })?
                .clone();
        }
        let tracking_json = serde_json::to_string(&next_tracking)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction.execute(
            "UPDATE story_tracking_authority SET version=?2,payload_json=?3,content_fingerprint=?4,updated_at=?5 \
             WHERE project_id=?1 AND version=?6 AND content_fingerprint=?7",
            params![
                project_id,
                next_tracking.version,
                tracking_json,
                next_tracking.fingerprint,
                authorization.created_at,
                tracking_version,
                tracking_before
            ],
        ).map_err(storage_error).and_then(|changed| {
            if changed == 1 { Ok(()) } else { Err(CoreError::AuthorityConflict("tracking settlement compare-and-swap conflict".into())) }
        })?;
        transaction
            .execute(
                "INSERT INTO receipts(receipt_id,receipt_kind,idempotency_key,payload_json,created_at) \
                 VALUES(?1,'settlement',?2,?3,?4)",
                params![
                    format!("receipt-{settlement_id}"),
                    authorization.idempotency_key,
                    receipt_json,
                    authorization.created_at
                ],
            )
            .map_err(storage_error)?;
        let event_seq = append_story_event(
            &transaction,
            &project_id,
            run_id.clone(),
            Some(chapter_id.clone()),
            "chapter",
            &chapter_id,
            "chapter_settled",
            serde_json::json!({
                "schema":"quillframe_chapter_settled_event_v3",
                "settlement_id": settlement_id,
                "acceptance_id": preflight.acceptance_id,
                "candidate_id": preflight.candidate_id,
                "candidate_fingerprint": preflight.candidate_fingerprint,
                "document_id":document_id,
                "revision_id":preflight.revision_id,
                "chapter_id":chapter_id,
                "reading_order":reading_order,
                "canon_before_fingerprint":preflight.before_fingerprint,
                "canon_after":state_value,
                "canon_head_fingerprint":after_head_fingerprint,
                "tracking_proposal":tracking_proposal,
            }),
            &authorization.created_at,
        )?;
        create_story_snapshot(
            &transaction,
            &project_id,
            event_seq,
            "chapter_settled",
            &authorization.created_at,
        )?;
        transaction.commit().map_err(storage_error)?;
        Ok(settlement_id)
    }
}

#[allow(clippy::too_many_arguments)]
fn apply_narrative_deltas(
    transaction: &Transaction<'_>,
    proposal: &crate::ChapterTrackingProposal,
    chapter_id: &str,
    acceptance_id: &str,
    source_fingerprint: &str,
    reading_order: u32,
    created_at: &str,
) -> CoreResult<()> {
    for delta in &proposal.entity_deltas {
        let state_json = serde_json::to_string(&delta.state)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let source_type = match delta.entity_kind {
            NarrativeEntityKind::Character => {
                transaction
                    .execute(
                        "INSERT INTO characters(character_id,name,state_json,updated_at) \
                         VALUES(?1,?2,?3,?4) ON CONFLICT(character_id) DO UPDATE SET \
                         name=excluded.name,state_json=excluded.state_json,updated_at=excluded.updated_at",
                        params![delta.entity_id, delta.display_name, state_json, created_at],
                    )
                    .map_err(storage_error)?;
                "character"
            }
            NarrativeEntityKind::World => {
                transaction
                    .execute(
                        "INSERT INTO world_entities(entity_id,entity_type,name,truth_json,updated_at) \
                         VALUES(?1,'narrative',?2,?3,?4) ON CONFLICT(entity_id) DO UPDATE SET \
                         name=excluded.name,truth_json=excluded.truth_json,updated_at=excluded.updated_at",
                        params![delta.entity_id, delta.display_name, state_json, created_at],
                    )
                    .map_err(storage_error)?;
                "world"
            }
        };
        upsert_narrative_source(
            transaction,
            source_type,
            &delta.entity_id,
            chapter_id,
            acceptance_id,
            source_fingerprint,
            created_at,
        )?;
    }

    for delta in &proposal.relationship_deltas {
        let existing = transaction
            .query_row(
                "SELECT participant_a,participant_b FROM relationships WHERE relationship_id=?1",
                [&delta.relationship_id],
                |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
            )
            .optional()
            .map_err(storage_error)?;
        if existing.as_ref().is_some_and(|participants| {
            participants.0 != delta.participant_a || participants.1 != delta.participant_b
        }) {
            return Err(CoreError::AuthorityConflict(
                "relationship identity cannot change participants".into(),
            ));
        }
        let state_json = serde_json::to_string(&delta.state)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        transaction
            .execute(
                "INSERT INTO relationships(relationship_id,participant_a,participant_b,relationship_type,state_json,updated_at) \
                 VALUES(?1,?2,?3,?4,?5,?6) ON CONFLICT(relationship_id) DO UPDATE SET \
                 relationship_type=excluded.relationship_type,state_json=excluded.state_json,updated_at=excluded.updated_at",
                params![delta.relationship_id,delta.participant_a,delta.participant_b,delta.relationship_type,state_json,created_at],
            )
            .map_err(storage_error)?;
        upsert_narrative_source(
            transaction,
            "relationship",
            &delta.relationship_id,
            chapter_id,
            acceptance_id,
            source_fingerprint,
            created_at,
        )?;
    }

    for delta in &proposal.knowledge_deltas {
        let fact_json = serde_json::to_string(&delta.fact)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let existing_character = transaction
            .query_row(
                "SELECT character_id FROM character_knowledge WHERE knowledge_id=?1",
                [&delta.knowledge_id],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?;
        if existing_character
            .as_ref()
            .is_some_and(|character| character != &delta.character_id)
        {
            return Err(CoreError::AuthorityConflict(
                "knowledge identity cannot change character ownership".into(),
            ));
        }
        transaction
            .execute(
                "INSERT INTO character_knowledge(knowledge_id,character_id,claim_ref,fact_json,available_from_story_order,evidence_ref,confidence) \
                 VALUES(?1,?2,NULL,?3,?4,?5,?6) ON CONFLICT(knowledge_id) DO UPDATE SET \
                 fact_json=excluded.fact_json,available_from_story_order=excluded.available_from_story_order, \
                 evidence_ref=excluded.evidence_ref,confidence=excluded.confidence",
                params![delta.knowledge_id,delta.character_id,fact_json,reading_order,acceptance_id,delta.confidence],
            )
            .map_err(storage_error)?;
        upsert_narrative_source(
            transaction,
            "knowledge",
            &delta.knowledge_id,
            chapter_id,
            acceptance_id,
            source_fingerprint,
            created_at,
        )?;
    }

    for delta in &proposal.timeline_deltas {
        transaction
            .execute(
                "INSERT INTO timeline_events(event_id,story_order,title,description,authority_class,source_ref) \
                 VALUES(?1,?2,?3,?4,'accepted',?5) ON CONFLICT(event_id) DO UPDATE SET \
                 story_order=excluded.story_order,title=excluded.title,description=excluded.description, \
                 authority_class='accepted',source_ref=excluded.source_ref",
                params![delta.event_id, reading_order, delta.title, delta.description, acceptance_id],
            )
            .map_err(storage_error)?;
        upsert_narrative_source(
            transaction,
            "timeline",
            &delta.event_id,
            chapter_id,
            acceptance_id,
            source_fingerprint,
            created_at,
        )?;
    }

    for delta in &proposal.expectation_deltas {
        let status = match delta.action {
            ExpectationDeltaAction::Open | ExpectationDeltaAction::Defer => "open",
            ExpectationDeltaAction::Advance => "partial",
            ExpectationDeltaAction::Payoff => "paid",
            ExpectationDeltaAction::Abandon => "abandoned",
        };
        transaction
            .execute(
                "INSERT INTO expectations(expectation_id,kind,scope,description,opened_order,due_by_order,last_touched_order,status,source_ref,source_fingerprint,version,created_at,updated_at) \
                 VALUES(?1,?2,'book',?3,?4,NULL,?4,?5,?6,?7,1,?8,?8) ON CONFLICT(expectation_id) DO UPDATE SET \
                 description=excluded.description,last_touched_order=excluded.last_touched_order,status=excluded.status, \
                 source_ref=excluded.source_ref,source_fingerprint=excluded.source_fingerprint,version=expectations.version+1,updated_at=excluded.updated_at",
                params![delta.expectation_id,delta.kind,delta.description,reading_order,status,
                    format!("chapter:{chapter_id}"),source_fingerprint,created_at],
            )
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO expectation_events(expectation_id,event_type,at_order,detail,evidence_ref,created_at) \
                 VALUES(?1,?2,?3,?4,?5,?6)",
                params![delta.expectation_id,format!("{:?}",delta.action).to_lowercase(),reading_order,
                    delta.description,acceptance_id,created_at],
            )
            .map_err(storage_error)?;
        upsert_narrative_source(
            transaction,
            "expectation",
            &delta.expectation_id,
            chapter_id,
            acceptance_id,
            source_fingerprint,
            created_at,
        )?;
    }
    Ok(())
}

fn upsert_narrative_source(
    transaction: &Transaction<'_>,
    entity_type: &str,
    entity_id: &str,
    chapter_id: &str,
    acceptance_id: &str,
    source_fingerprint: &str,
    created_at: &str,
) -> CoreResult<()> {
    transaction
        .execute(
            "INSERT INTO narrative_state_sources(entity_type,entity_id,chapter_id,acceptance_id,source_fingerprint,state,updated_at) \
             VALUES(?1,?2,?3,?4,?5,'current',?6) ON CONFLICT(entity_type,entity_id) DO UPDATE SET \
             chapter_id=excluded.chapter_id,acceptance_id=excluded.acceptance_id, \
             source_fingerprint=excluded.source_fingerprint,state='current',updated_at=excluded.updated_at",
            params![entity_type,entity_id,chapter_id,acceptance_id,source_fingerprint,created_at],
        )
        .map_err(storage_error)?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn append_story_event(
    transaction: &Transaction<'_>,
    project_id: &str,
    run_id: Option<String>,
    chapter_id: Option<String>,
    aggregate_kind: &str,
    aggregate_id: &str,
    event_kind: &str,
    payload: serde_json::Value,
    created_at: &str,
) -> CoreResult<i64> {
    let (base_revision, prior_state_fingerprint): (u64, String) = transaction
        .query_row(
            "SELECT revision,state_fingerprint FROM project_state_heads WHERE project_id=?1",
            [project_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .map_err(storage_error)?;
    let event = StoryEvent::create(
        project_id,
        run_id,
        chapter_id,
        aggregate_kind,
        aggregate_id,
        event_kind,
        base_revision,
        payload,
        created_at,
    )?;
    event.validate()?;
    let payload_json = serde_json::to_string(&event.payload)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    transaction
        .execute(
            "INSERT INTO story_events( \
             event_id,project_id,run_id,chapter_id,aggregate_kind,aggregate_id,event_kind, \
             base_revision,commit_revision,payload_json,payload_fingerprint,event_fingerprint,created_at \
             ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)",
            params![
                event.event_id.to_string(),
                event.project_id,
                event.run_id,
                event.chapter_id,
                event.aggregate_kind,
                event.aggregate_id,
                event.event_kind,
                event.base_revision,
                event.commit_revision,
                payload_json,
                event.payload_fingerprint,
                event.fingerprint,
                event.created_at
            ],
        )
        .map_err(storage_error)?;
    let event_seq = transaction.last_insert_rowid();
    let next_state_fingerprint = crate::fingerprint::sha256_fingerprint(
        format!("{}:{}", prior_state_fingerprint, event.fingerprint).as_bytes(),
    );
    let changed = transaction
        .execute(
            "UPDATE project_state_heads SET revision=?2,latest_event_seq=?3,state_fingerprint=?4,updated_at=?5 \
             WHERE project_id=?1 AND revision=?6 AND state_fingerprint=?7",
            params![
                project_id,
                event.commit_revision,
                event_seq,
                next_state_fingerprint,
                created_at,
                base_revision,
                prior_state_fingerprint
            ],
        )
        .map_err(storage_error)?;
    if changed != 1 {
        return Err(CoreError::AuthorityConflict(
            "project state head changed before story event commit".into(),
        ));
    }
    Ok(event_seq)
}

fn create_story_snapshot(
    transaction: &Transaction<'_>,
    project_id: &str,
    through_event_seq: i64,
    reason: &str,
    created_at: &str,
) -> CoreResult<String> {
    let (through_revision, through_event_fingerprint, event_chain_fingerprint): (
        u64,
        String,
        String,
    ) = transaction
        .query_row(
            "SELECT e.commit_revision,e.event_fingerprint,h.state_fingerprint \
             FROM story_events e JOIN project_state_heads h ON h.project_id=e.project_id \
             WHERE e.project_id=?1 AND e.event_seq=?2 AND h.latest_event_seq=e.event_seq",
            params![project_id, through_event_seq],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .map_err(storage_error)?;
    let projection = story_projection(transaction, project_id)?;
    let snapshot = StoryStateSnapshot::create(
        project_id,
        through_revision,
        through_event_seq,
        through_event_fingerprint,
        event_chain_fingerprint,
        projection,
        reason,
        created_at,
    )?;
    snapshot.validate()?;
    let snapshot_id = snapshot.snapshot_id.to_string();
    transaction.execute(
        "INSERT INTO story_state_snapshots(snapshot_id,project_id,through_event_seq,schema_version,state_fingerprint,payload_json,reason,created_at) \
         VALUES(?1,?2,?3,1,?4,?5,?6,?7)",
        params![snapshot_id,project_id,through_event_seq,snapshot.projection_fingerprint,
            serde_json::to_string(&snapshot).map_err(|error|CoreError::Serialization(error.to_string()))?,reason,created_at]
    ).map_err(storage_error)?;
    let changed = transaction
        .execute(
            "UPDATE project_state_heads SET latest_snapshot_id=?2,updated_at=?3 \
         WHERE project_id=?1 AND revision=?4 AND latest_event_seq=?5 AND state_fingerprint=?6",
            params![
                project_id,
                snapshot_id,
                created_at,
                through_revision,
                through_event_seq,
                snapshot.event_chain_fingerprint
            ],
        )
        .map_err(storage_error)?;
    if changed != 1 {
        return Err(CoreError::AuthorityConflict(
            "project head changed before snapshot attachment".into(),
        ));
    }
    transaction
        .execute(
            "DELETE FROM story_state_snapshots WHERE project_id=?1 AND snapshot_id NOT IN (\
             SELECT snapshot_id FROM story_state_snapshots WHERE project_id=?1 \
             ORDER BY through_event_seq DESC LIMIT 4)",
            [project_id],
        )
        .map_err(storage_error)?;
    Ok(snapshot_id)
}

fn story_projection(
    transaction: &Transaction<'_>,
    project_id: &str,
) -> CoreResult<serde_json::Value> {
    let tracking = collect_json_rows(transaction,
        "SELECT json_object('project_id',project_id,'version',version,'payload_json',json(payload_json),'content_fingerprint',content_fingerprint,'updated_at',updated_at) \
         FROM story_tracking_authority ORDER BY project_id")?;
    if tracking.len() != 1
        || tracking[0]
            .get("project_id")
            .and_then(serde_json::Value::as_str)
            != Some(project_id)
    {
        return Err(CoreError::AuthorityConflict(
            "snapshot tracking authority is missing".into(),
        ));
    }
    Ok(serde_json::json!({
        "schema":"quillframe_story_projection_v1",
        "project_id":project_id,
        "canon_state":collect_json_rows(transaction,"SELECT json_object('state_key',state_key,'value_json',json(value_json),'authority_class',authority_class,'evidence_ref',evidence_ref,'content_fingerprint',content_fingerprint,'updated_at',updated_at) FROM canon_state ORDER BY state_key")?,
        "tracking":tracking,
        "characters":collect_json_rows(transaction,"SELECT json_object('character_id',character_id,'name',name,'agenda',agenda,'voice_notes',voice_notes,'state_json',json(state_json),'updated_at',updated_at) FROM characters ORDER BY character_id")?,
        "relationships":collect_json_rows(transaction,"SELECT json_object('relationship_id',relationship_id,'participant_a',participant_a,'participant_b',participant_b,'relationship_type',relationship_type,'state_json',json(state_json),'updated_at',updated_at) FROM relationships ORDER BY relationship_id")?,
        "world_entities":collect_json_rows(transaction,"SELECT json_object('entity_id',entity_id,'entity_type',entity_type,'name',name,'truth_json',json(truth_json),'updated_at',updated_at) FROM world_entities ORDER BY entity_id")?,
        "timeline_events":collect_json_rows(transaction,"SELECT json_object('event_id',event_id,'story_order',story_order,'title',title,'description',description,'authority_class',authority_class,'source_ref',source_ref) FROM timeline_events ORDER BY story_order,event_id")?,
        "character_knowledge":collect_json_rows(transaction,"SELECT json_object('knowledge_id',knowledge_id,'character_id',character_id,'claim_ref',claim_ref,'fact_json',json(fact_json),'available_from_story_order',available_from_story_order,'evidence_ref',evidence_ref,'confidence',confidence) FROM character_knowledge ORDER BY knowledge_id")?,
        "expectations":collect_json_rows(transaction,"SELECT json_object('expectation_id',expectation_id,'kind',kind,'scope',scope,'description',description,'opened_order',opened_order,'due_by_order',due_by_order,'last_touched_order',last_touched_order,'status',status,'source_ref',source_ref,'source_fingerprint',source_fingerprint,'version',version,'created_at',created_at,'updated_at',updated_at) FROM expectations ORDER BY expectation_id")?,
        "expectation_events":collect_json_rows(transaction,"SELECT json_object('event_id',event_id,'expectation_id',expectation_id,'event_type',event_type,'at_order',at_order,'detail',detail,'evidence_ref',evidence_ref,'created_at',created_at) FROM expectation_events ORDER BY event_id")?,
        "narrative_state_sources":collect_json_rows(transaction,"SELECT json_object('entity_type',entity_type,'entity_id',entity_id,'chapter_id',chapter_id,'acceptance_id',acceptance_id,'source_fingerprint',source_fingerprint,'state',state,'updated_at',updated_at) FROM narrative_state_sources ORDER BY entity_type,entity_id")?,
        "accepted_revision_anchors":collect_json_rows(transaction,"SELECT json_object('document_id',d.document_id,'chapter_id',d.story_node_id,'revision_id',r.revision_id,'content_fingerprint',r.content_fingerprint) FROM document_revisions r JOIN documents d ON d.document_id=r.document_id WHERE r.authority_class='accepted' ORDER BY d.story_node_id,r.revision_id")?
    }))
}

fn collect_json_rows(
    transaction: &Transaction<'_>,
    sql: &str,
) -> CoreResult<Vec<serde_json::Value>> {
    let mut statement = transaction.prepare(sql).map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(storage_error)?
        .map(|row| {
            serde_json::from_str(&row.map_err(storage_error)?)
                .map_err(|error| CoreError::Storage(error.to_string()))
        })
        .collect();
    rows
}

fn materialize_story_projection(
    transaction: &Transaction<'_>,
    snapshot_payload: &str,
) -> CoreResult<()> {
    // Child/source ledgers are removed first; the immutable event log, snapshots, documents and
    // accepted revisions are deliberately untouched.
    for table in [
        "narrative_state_sources",
        "expectation_events",
        "expectations",
        "character_knowledge",
        "timeline_events",
        "relationships",
        "characters",
        "world_entities",
        "canon_state",
        "story_tracking_authority",
    ] {
        transaction
            .execute(&format!("DELETE FROM {table}"), [])
            .map_err(storage_error)?;
    }
    let statements = [
        "INSERT INTO canon_state(state_key,value_json,authority_class,evidence_ref,content_fingerprint,updated_at) SELECT json_extract(value,'$.state_key'),json_extract(value,'$.value_json'),json_extract(value,'$.authority_class'),json_extract(value,'$.evidence_ref'),json_extract(value,'$.content_fingerprint'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.canon_state'))",
        "INSERT INTO story_tracking_authority(project_id,version,payload_json,content_fingerprint,updated_at) SELECT json_extract(value,'$.project_id'),json_extract(value,'$.version'),json_extract(value,'$.payload_json'),json_extract(value,'$.content_fingerprint'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.tracking'))",
        "INSERT INTO characters(character_id,name,agenda,voice_notes,state_json,updated_at) SELECT json_extract(value,'$.character_id'),json_extract(value,'$.name'),json_extract(value,'$.agenda'),json_extract(value,'$.voice_notes'),json_extract(value,'$.state_json'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.characters'))",
        "INSERT INTO world_entities(entity_id,entity_type,name,truth_json,updated_at) SELECT json_extract(value,'$.entity_id'),json_extract(value,'$.entity_type'),json_extract(value,'$.name'),json_extract(value,'$.truth_json'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.world_entities'))",
        "INSERT INTO relationships(relationship_id,participant_a,participant_b,relationship_type,state_json,updated_at) SELECT json_extract(value,'$.relationship_id'),json_extract(value,'$.participant_a'),json_extract(value,'$.participant_b'),json_extract(value,'$.relationship_type'),json_extract(value,'$.state_json'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.relationships'))",
        "INSERT INTO timeline_events(event_id,story_order,title,description,authority_class,source_ref) SELECT json_extract(value,'$.event_id'),json_extract(value,'$.story_order'),json_extract(value,'$.title'),json_extract(value,'$.description'),json_extract(value,'$.authority_class'),json_extract(value,'$.source_ref') FROM json_each(json_extract(?1,'$.projection.timeline_events'))",
        "INSERT INTO character_knowledge(knowledge_id,character_id,claim_ref,fact_json,available_from_story_order,evidence_ref,confidence) SELECT json_extract(value,'$.knowledge_id'),json_extract(value,'$.character_id'),json_extract(value,'$.claim_ref'),json_extract(value,'$.fact_json'),json_extract(value,'$.available_from_story_order'),json_extract(value,'$.evidence_ref'),json_extract(value,'$.confidence') FROM json_each(json_extract(?1,'$.projection.character_knowledge'))",
        "INSERT INTO expectations(expectation_id,kind,scope,description,opened_order,due_by_order,last_touched_order,status,source_ref,source_fingerprint,version,created_at,updated_at) SELECT json_extract(value,'$.expectation_id'),json_extract(value,'$.kind'),json_extract(value,'$.scope'),json_extract(value,'$.description'),json_extract(value,'$.opened_order'),json_extract(value,'$.due_by_order'),json_extract(value,'$.last_touched_order'),json_extract(value,'$.status'),json_extract(value,'$.source_ref'),json_extract(value,'$.source_fingerprint'),json_extract(value,'$.version'),json_extract(value,'$.created_at'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.expectations'))",
        "INSERT INTO expectation_events(event_id,expectation_id,event_type,at_order,detail,evidence_ref,created_at) SELECT json_extract(value,'$.event_id'),json_extract(value,'$.expectation_id'),json_extract(value,'$.event_type'),json_extract(value,'$.at_order'),json_extract(value,'$.detail'),json_extract(value,'$.evidence_ref'),json_extract(value,'$.created_at') FROM json_each(json_extract(?1,'$.projection.expectation_events'))",
        "INSERT INTO narrative_state_sources(entity_type,entity_id,chapter_id,acceptance_id,source_fingerprint,state,updated_at) SELECT json_extract(value,'$.entity_type'),json_extract(value,'$.entity_id'),json_extract(value,'$.chapter_id'),json_extract(value,'$.acceptance_id'),json_extract(value,'$.source_fingerprint'),json_extract(value,'$.state'),json_extract(value,'$.updated_at') FROM json_each(json_extract(?1,'$.projection.narrative_state_sources'))",
    ];
    for statement in statements {
        transaction
            .execute(statement, [snapshot_payload])
            .map_err(storage_error)?;
    }
    Ok(())
}

fn verify_story_history(transaction: &Transaction<'_>) -> CoreResult<()> {
    let (project_id, revision, latest_event_seq, latest_snapshot_id, head_fingerprint):
        (String, u64, Option<i64>, Option<String>, String) = transaction.query_row(
            "SELECT project_id,revision,latest_event_seq,latest_snapshot_id,state_fingerprint FROM project_state_heads",
            [],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?))
        ).map_err(storage_error)?;
    let initial_tracking = TrackingState::empty(&project_id)?;
    let mut chain_fingerprint = crate::fingerprint::sha256_fingerprint(
        format!("{}:{}", project_id, initial_tracking.fingerprint).as_bytes(),
    );
    let mut expected_revision = 0_u64;
    let mut last_seq = None;
    let mut last_event_fingerprint = None;
    let mut statement=transaction.prepare(
        "SELECT event_seq,event_id,run_id,chapter_id,aggregate_kind,aggregate_id,event_kind,base_revision,commit_revision,payload_json,payload_fingerprint,event_fingerprint,created_at \
         FROM story_events WHERE project_id=?1 ORDER BY event_seq"
    ).map_err(storage_error)?;
    let rows = statement
        .query_map([&project_id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Option<String>>(2)?,
                row.get::<_, Option<String>>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, String>(5)?,
                row.get::<_, String>(6)?,
                row.get::<_, u64>(7)?,
                row.get::<_, u64>(8)?,
                row.get::<_, String>(9)?,
                row.get::<_, String>(10)?,
                row.get::<_, String>(11)?,
                row.get::<_, String>(12)?,
            ))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    drop(statement);
    for (
        seq,
        event_id,
        run_id,
        chapter_id,
        aggregate_kind,
        aggregate_id,
        event_kind,
        base_revision,
        commit_revision,
        payload_json,
        payload_fingerprint,
        event_fingerprint,
        created_at,
    ) in rows
    {
        let event = StoryEvent {
            schema: "quillframe_story_event_v1".into(),
            event_id: uuid::Uuid::parse_str(&event_id)
                .map_err(|error| CoreError::Storage(error.to_string()))?,
            project_id: project_id.clone(),
            run_id,
            chapter_id,
            aggregate_kind,
            aggregate_id,
            event_kind,
            base_revision,
            commit_revision,
            payload: serde_json::from_str(&payload_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?,
            payload_fingerprint,
            created_at,
            fingerprint: event_fingerprint.clone(),
        };
        event.validate()?;
        if event.base_revision != expected_revision
            || event.commit_revision != expected_revision + 1
        {
            return Err(CoreError::AuthorityConflict(
                "story event revision chain is broken".into(),
            ));
        }
        chain_fingerprint = crate::fingerprint::sha256_fingerprint(
            format!("{}:{}", chain_fingerprint, event.fingerprint).as_bytes(),
        );
        expected_revision = event.commit_revision;
        last_seq = Some(seq);
        last_event_fingerprint = Some(event.fingerprint);
    }
    if expected_revision != revision
        || last_seq != latest_event_seq
        || chain_fingerprint != head_fingerprint
    {
        return Err(CoreError::AuthorityConflict(
            "project state head does not match story history".into(),
        ));
    }
    match (revision, latest_snapshot_id) {
        (0, None) => Ok(()),
        (0, Some(_)) => Err(CoreError::AuthorityConflict(
            "genesis head must not have a snapshot".into(),
        )),
        (_, Some(snapshot_id)) => {
            let (payload,state_fingerprint,event_seq):(String,String,i64)=transaction.query_row(
                "SELECT payload_json,state_fingerprint,through_event_seq FROM story_state_snapshots WHERE snapshot_id=?1 AND project_id=?2",
                params![snapshot_id,project_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))
            ).map_err(storage_error)?;
            let snapshot: StoryStateSnapshot = serde_json::from_str(&payload)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            snapshot.validate()?;
            let current_projection = story_projection(transaction, &project_id)?;
            let current_projection_fingerprint = crate::fingerprint::sha256_fingerprint(
                serde_json::to_vec(&current_projection)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?,
            );
            if snapshot.project_id != project_id
                || snapshot.through_revision != revision
                || Some(event_seq) != latest_event_seq
                || snapshot.through_event_seq != event_seq
                || snapshot.through_event_fingerprint != last_event_fingerprint.unwrap_or_default()
                || snapshot.event_chain_fingerprint != head_fingerprint
                || snapshot.projection_fingerprint != state_fingerprint
                || snapshot.projection_fingerprint != current_projection_fingerprint
            {
                return Err(CoreError::AuthorityConflict(
                    "latest story snapshot does not match its head or projection".into(),
                ));
            }
            Ok(())
        }
        (_, None) => Err(CoreError::AuthorityConflict(
            "committed story head has no recovery snapshot".into(),
        )),
    }
}

fn settlement_preflight_from_connection(
    connection: &rusqlite::Connection,
    acceptance_id: &str,
    target_ref: &str,
    created_at: &str,
) -> CoreResult<SettlementPreflight> {
    let (candidate_id, candidate_fingerprint, revision_id, chapter_id, accepted_fingerprint) = connection
        .query_row(
            "SELECT c.candidate_id,c.content_fingerprint,c.revision_id,d.story_node_id,a.candidate_fingerprint \
             FROM acceptance_evidence a JOIN candidates c ON c.candidate_id=a.candidate_id \
             JOIN documents d ON d.document_id=c.document_id \
             WHERE a.acceptance_id=?1 AND c.status='accepted'",
            [acceptance_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                ))
            },
        )
        .map_err(storage_error)?;
    if accepted_fingerprint != candidate_fingerprint
        || target_ref != format!("chapter:{chapter_id}")
    {
        return Err(CoreError::AuthorityConflict(
            "settlement acceptance, candidate and chapter target are not exactly bound".into(),
        ));
    }
    let (revision_content, revision_fingerprint) = connection
        .query_row(
            "SELECT content,content_fingerprint FROM document_revisions WHERE revision_id=?1",
            [&revision_id],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        )
        .map_err(storage_error)?;
    if revision_fingerprint != candidate_fingerprint
        || crate::fingerprint::sha256_fingerprint(revision_content.as_bytes())
            != candidate_fingerprint
    {
        return Err(CoreError::AuthorityConflict(
            "settlement candidate bytes changed after release".into(),
        ));
    }
    let before_fingerprint = connection
        .query_row(
            "SELECT content_fingerprint FROM canon_state WHERE state_key=?1",
            [target_ref],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(storage_error)?
        .unwrap_or_else(|| crate::fingerprint::sha256_fingerprint([]));
    let mut preflight = SettlementPreflight {
        schema: "quillframe_settlement_preflight_v1".into(),
        preflight_id: uuid::Uuid::new_v4(),
        acceptance_id: acceptance_id.into(),
        candidate_id,
        candidate_fingerprint,
        revision_id,
        target_ref: target_ref.into(),
        before_fingerprint,
        created_at: created_at.into(),
        fingerprint: String::new(),
    };
    preflight.seal()?;
    Ok(preflight)
}

fn stage_name(stage: AnalyzeStage) -> &'static str {
    match stage {
        AnalyzeStage::BoundaryIndex => "boundary_index",
        AnalyzeStage::GoldenThree => "golden_three",
        AnalyzeStage::ChapterExtraction => "chapter_extraction",
        AnalyzeStage::AggregateMechanisms => "aggregate_mechanisms",
        AnalyzeStage::StoryEntities => "story_entities",
        AnalyzeStage::Report => "report",
        AnalyzeStage::StyleProfile => "style_profile",
    }
}

fn production_task_mode(mode: crate::ProductionTaskMode) -> &'static str {
    match mode {
        crate::ProductionTaskMode::Draft => "DRAFT",
        crate::ProductionTaskMode::Revise => "REVISE",
    }
}

fn review_mode_name(mode: crate::ReviewMode) -> &'static str {
    match mode {
        crate::ReviewMode::Full => "full",
        crate::ReviewMode::Lean => "lean",
        crate::ReviewMode::Solo => "solo",
    }
}

fn review_decision_name(decision: crate::ReviewDecision) -> &'static str {
    match decision {
        crate::ReviewDecision::Accept => "accept",
        crate::ReviewDecision::Revise => "revise",
        crate::ReviewDecision::InfrastructureFailed => "infrastructure_failed",
    }
}

fn open_connection(path: &Path) -> CoreResult<Connection> {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .map_err(storage_error)?;
    connection
        .busy_timeout(Duration::from_secs(5))
        .map_err(storage_error)?;
    connection
        .pragma_update(None, "foreign_keys", "ON")
        .map_err(storage_error)?;
    Ok(connection)
}

fn insert_initial_project(
    transaction: &Transaction<'_>,
    manifest: &ProjectManifest,
    created_at: &str,
) -> CoreResult<()> {
    transaction
        .execute(
            "INSERT INTO project_identity( \
             project_id,title,language,project_schema_version,created_at,updated_at \
             ) VALUES(?1,?2,?3,1,?4,?4)",
            params![manifest.id, manifest.title, manifest.language, created_at],
        )
        .map_err(storage_error)?;
    for (node_id, parent_id, kind, ordinal, title) in [
        ("BOOK", None, "book", 1_u32, manifest.title.as_str()),
        ("VOL001", Some("BOOK"), "volume", 1, "第一卷"),
        ("UNIT001", Some("VOL001"), "unit", 1, "第一单元"),
        (
            "CH001",
            Some("UNIT001"),
            "chapter",
            1,
            manifest.title.as_str(),
        ),
    ] {
        transaction
            .execute(
                "INSERT INTO story_nodes( \
                 node_id,parent_id,kind,ordinal,title,metadata_json \
                 ) VALUES(?1,?2,?3,?4,?5,'{}')",
                params![node_id, parent_id, kind, ordinal, title],
            )
            .map_err(storage_error)?;
    }
    transaction
        .execute(
            "INSERT INTO documents( \
             document_id,story_node_id,document_kind,title,created_at \
             ) VALUES('DOC-CH001','CH001','manuscript',?1,?2)",
            params![manifest.title, created_at],
        )
        .map_err(storage_error)?;
    transaction
        .execute(
            "INSERT INTO search_index(entity_type,entity_id,title,body) \
             VALUES('document','DOC-CH001',?1,'')",
            [manifest.title.as_str()],
        )
        .map_err(storage_error)?;
    let tracking = TrackingState::empty(&manifest.id)?;
    let tracking_json = serde_json::to_string(&tracking)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    transaction
        .execute(
            "INSERT INTO story_tracking_authority(project_id,version,payload_json,content_fingerprint,updated_at) \
             VALUES(?1,0,?2,?3,?4)",
            params![manifest.id, tracking_json, tracking.fingerprint, created_at],
        )
        .map_err(storage_error)?;
    let initial_state_fingerprint = crate::fingerprint::sha256_fingerprint(
        format!("{}:{}", manifest.id, tracking.fingerprint).as_bytes(),
    );
    transaction
        .execute(
            "INSERT INTO project_state_heads( \
             project_id,revision,latest_event_seq,latest_snapshot_id,state_fingerprint,updated_at \
             ) VALUES(?1,0,NULL,NULL,?2,?3)",
            params![manifest.id, initial_state_fingerprint, created_at],
        )
        .map_err(storage_error)?;
    Ok(())
}

fn validate_project_identity(
    connection: &Connection,
    manifest: &ProjectManifest,
) -> CoreResult<()> {
    let mut statement = connection
        .prepare(
            "SELECT project_id,title,language,project_schema_version \
             FROM project_identity",
        )
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, u32>(3)?,
            ))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    let expected = [(
        manifest.id.clone(),
        manifest.title.clone(),
        manifest.language.clone(),
        1,
    )];
    if rows != expected {
        return Err(CoreError::Storage(
            "SQLite Project identity does not match the exact manifest".into(),
        ));
    }
    Ok(())
}

fn validate_novel_topology(connection: &Connection) -> CoreResult<()> {
    let mut statement = connection
        .prepare(
            "SELECT node_id,parent_id,kind,ordinal,metadata_json \
             FROM story_nodes",
        )
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, Option<String>>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, u32>(3)?,
                row.get::<_, String>(4)?,
            ))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    let nodes = rows
        .iter()
        .map(|row| (row.0.clone(), row))
        .collect::<BTreeMap<_, _>>();
    if nodes.is_empty() {
        return Err(CoreError::Storage("novel topology is empty".into()));
    }
    let mut positions = BTreeSet::new();
    let mut books = 0_u32;
    let mut chapters = BTreeSet::new();
    for (node_id, parent_id, kind, ordinal, metadata_json) in &rows {
        if *ordinal == 0 || !positions.insert((parent_id.clone(), kind.clone(), *ordinal)) {
            return Err(CoreError::Storage(
                "story sibling positions must be positive and unique".into(),
            ));
        }
        let metadata: serde_json::Value = serde_json::from_str(metadata_json).map_err(|error| {
            CoreError::Storage(format!("story node metadata is invalid: {error}"))
        })?;
        let object = metadata
            .as_object()
            .ok_or_else(|| CoreError::Storage("story node metadata must be an object".into()))?;
        if object.contains_key("chapter_scope") {
            return Err(CoreError::Storage(
                "legacy chapter_scope metadata is forbidden".into(),
            ));
        }
        let expected_parent_kind = match kind.as_str() {
            "book" => {
                books += 1;
                None
            }
            "volume" => Some("book"),
            "unit" => Some("volume"),
            "chapter" => {
                chapters.insert(node_id.clone());
                Some("unit")
            }
            "scene" => Some("chapter"),
            _ => {
                return Err(CoreError::Storage(
                    "story topology contains an unsupported node kind".into(),
                ))
            }
        };
        match (parent_id, expected_parent_kind) {
            (None, None) => {}
            (Some(parent), Some(expected))
                if nodes.get(parent).is_some_and(|value| value.2 == expected) => {}
            _ => {
                return Err(CoreError::Storage(
                    "story topology violates book-volume-unit-chapter-scene ancestry".into(),
                ))
            }
        }
        let mut seen = BTreeSet::from([node_id.as_str()]);
        let mut cursor = parent_id.as_deref();
        while let Some(parent) = cursor {
            if !seen.insert(parent) {
                return Err(CoreError::Storage("story topology contains a cycle".into()));
            }
            cursor = nodes
                .get(parent)
                .ok_or_else(|| CoreError::Storage("story parent is missing".into()))?
                .1
                .as_deref();
        }
    }
    if books != 1 || chapters.is_empty() {
        return Err(CoreError::Storage(
            "native novel requires one book and at least one chapter".into(),
        ));
    }

    let mut documents = connection
        .prepare("SELECT story_node_id FROM documents WHERE document_kind='manuscript'")
        .map_err(storage_error)?;
    let manuscript_chapters = documents
        .query_map([], |row| row.get::<_, Option<String>>(0))
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?
        .into_iter()
        .collect::<Option<BTreeSet<_>>>()
        .ok_or_else(|| CoreError::Storage("manuscript is missing its chapter".into()))?;
    if manuscript_chapters != chapters {
        return Err(CoreError::Storage(
            "every chapter must own exactly one manuscript".into(),
        ));
    }
    Ok(())
}

fn validate_plan_dependencies_in_transaction(
    transaction: &Transaction<'_>,
    proposal: &PlanProposal,
) -> CoreResult<()> {
    let (mut parent_id, target_kind): (Option<String>, String) = transaction
        .query_row(
            "SELECT parent_id,kind FROM story_nodes WHERE node_id=?1",
            [&proposal.target.node_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .optional()
        .map_err(storage_error)?
        .ok_or_else(|| CoreError::InvalidPlan("plan target node is unavailable".into()))?;
    let target_kind = parse_story_kind(&target_kind)?;
    if target_kind != proposal.target.kind {
        return Err(CoreError::InvalidPlan(
            "plan target kind differs from the persisted story node".into(),
        ));
    }
    let mut lineage = Vec::new();
    while let Some(node_id) = parent_id {
        let (next_parent, kind): (Option<String>, String) = transaction
            .query_row(
                "SELECT parent_id,kind FROM story_nodes WHERE node_id=?1",
                [&node_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| CoreError::InvalidHierarchy("story lineage is broken".into()))?;
        lineage.push((node_id, parse_story_kind(&kind)?));
        parent_id = next_parent;
    }
    lineage.reverse();
    for (node_id, kind) in lineage {
        let prefix = match kind {
            StoryKind::Book => "book",
            StoryKind::Volume => "volume",
            StoryKind::Unit => "unit",
            StoryKind::Chapter => "chapter",
            StoryKind::Scene => "scene",
        };
        let target_ref = format!("{prefix}:{node_id}");
        let fingerprint = transaction
            .query_row(
                "SELECT proposal_fingerprint FROM plan_activations \
                 WHERE target_ref=?1 AND status='active'",
                [&target_ref],
                |row| row.get::<_, String>(0),
            )
            .optional()
            .map_err(storage_error)?
            .ok_or_else(|| {
                CoreError::AuthorityConflict(format!(
                    "active ancestor plan {target_ref} is required"
                ))
            })?;
        if proposal.dependency_fingerprints.get(&target_ref) != Some(&fingerprint) {
            return Err(CoreError::AuthorityConflict(format!(
                "plan dependency for {target_ref} is missing or stale"
            )));
        }
    }
    Ok(())
}

fn parse_story_kind(value: &str) -> CoreResult<StoryKind> {
    match value {
        "book" => Ok(StoryKind::Book),
        "volume" => Ok(StoryKind::Volume),
        "unit" => Ok(StoryKind::Unit),
        "chapter" => Ok(StoryKind::Chapter),
        "scene" => Ok(StoryKind::Scene),
        _ => Err(CoreError::InvalidHierarchy(format!(
            "unsupported persisted story kind: {value}"
        ))),
    }
}

fn insert_learning_feedback(
    transaction: &Transaction<'_>,
    event: &serde_json::Value,
    created_at: &str,
) -> CoreResult<(String, bool)> {
    let object = event
        .as_object()
        .ok_or_else(|| CoreError::InvalidProject("learning feedback must be an object".into()))?;
    let required = |name: &str| {
        object
            .get(name)
            .and_then(serde_json::Value::as_str)
            .filter(|value| !value.trim().is_empty())
            .ok_or_else(|| {
                CoreError::InvalidProject(format!("learning feedback {name} is required"))
            })
    };
    let event_id = required("event_id")?;
    let feedback_text = required("feedback_text")?;
    let evidence_kind = required("evidence_kind")?;
    let candidate_id = required("candidate_id")?;
    let candidate_fingerprint = required("candidate_fingerprint")?;
    let document_id = required("document_id")?;
    let run_id = required("run_id")?;
    let source_type = required("source_type")?;
    let source_id = required("source_id")?;
    require_sha256(candidate_fingerprint)?;
    let payload_fingerprint = crate::fingerprint::sha256_fingerprint(
        serde_json::to_vec(event).map_err(|error| CoreError::Serialization(error.to_string()))?,
    );
    if let Some(existing) = transaction
        .query_row(
            "SELECT payload_fingerprint FROM learning_feedback_events WHERE event_id=?1",
            [event_id],
            |row| row.get::<_, String>(0),
        )
        .optional()
        .map_err(storage_error)?
    {
        if existing == payload_fingerprint {
            return Ok((event_id.into(), true));
        }
        return Err(CoreError::AuthorityConflict(
            "learning feedback event id binds different evidence".into(),
        ));
    }
    let binding: u32 = transaction.query_row(
        "SELECT COUNT(*) FROM candidates WHERE candidate_id=?1 AND content_fingerprint=?2 AND document_id=?3 AND run_id=?4",
        params![candidate_id,candidate_fingerprint,document_id,run_id],|row|row.get(0)
    ).map_err(storage_error)?;
    if binding != 1 {
        return Err(CoreError::AuthorityConflict(
            "learning feedback does not bind an exact production candidate".into(),
        ));
    }
    transaction.execute(
        "INSERT INTO learning_feedback_events(event_id,feedback_text,evidence_kind,candidate_id,candidate_fingerprint,document_id,run_id,source_type,source_id,payload_fingerprint,status,version,created_at,updated_at) \
         VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,'captured',1,?11,?11)",
        params![event_id,feedback_text,evidence_kind,candidate_id,candidate_fingerprint,document_id,run_id,
            source_type,source_id,payload_fingerprint,created_at]
    ).map_err(storage_error)?;
    transaction.execute(
        "INSERT INTO learning_evidence(evidence_id,evidence_kind,source_ref,payload_json,state,promotion_eligible,created_at) \
         VALUES(?1,?2,?3,?4,'awaiting_semantic',0,?5)",
        params![format!("learning-evidence-{event_id}"),evidence_kind,format!("{source_type}:{source_id}"),
            serde_json::to_string(event).map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]
    ).map_err(storage_error)?;
    Ok((event_id.into(), false))
}

fn require_timestamp(value: &str) -> CoreResult<()> {
    if value.trim().is_empty() || value != value.trim() {
        return Err(CoreError::Storage(
            "creation timestamp must be non-empty and trimmed".into(),
        ));
    }
    Ok(())
}

fn require_idempotency_key(value: &str) -> CoreResult<()> {
    if value.trim().is_empty() || value != value.trim() {
        return Err(CoreError::AuthorityConflict(
            "idempotency key must be non-empty and trimmed".into(),
        ));
    }
    Ok(())
}

fn story_container_request_fingerprint(
    project_id: &str,
    kind: &str,
    parent_id: &str,
    title: &str,
) -> CoreResult<String> {
    serde_json::to_vec(&serde_json::json!({
        "project_id":project_id,
        "kind":kind,
        "parent_id":parent_id,
        "title":title,
    }))
    .map(crate::fingerprint::sha256_fingerprint)
    .map_err(|error| CoreError::Serialization(error.to_string()))
}

fn require_sha256(value: &str) -> CoreResult<()> {
    if value.len() != 71
        || !value.starts_with("sha256:")
        || !value[7..].bytes().all(|byte| byte.is_ascii_hexdigit())
    {
        return Err(CoreError::AuthorityConflict(
            "fingerprint must be canonical sha256".into(),
        ));
    }
    Ok(())
}

fn writer_context_stages() -> BTreeSet<ContextStage> {
    BTreeSet::from([
        ContextStage::Character,
        ContextStage::Scene,
        ContextStage::Writer,
        ContextStage::Continuity,
    ])
}

fn chapter_canon_head_connection(
    connection: &Connection,
    chapter_id: &str,
) -> CoreResult<(String, String)> {
    connection
        .query_row(
            "SELECT value_json,content_fingerprint FROM canon_state WHERE state_key=?1",
            [format!("chapter:{chapter_id}")],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        )
        .map_err(storage_error)
}

fn chapter_canon_head_transaction(
    transaction: &Transaction<'_>,
    chapter_id: &str,
) -> CoreResult<(String, String)> {
    transaction
        .query_row(
            "SELECT value_json,content_fingerprint FROM canon_state WHERE state_key=?1",
            [format!("chapter:{chapter_id}")],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        )
        .map_err(storage_error)
}

fn last_utf8_chars(value: &str, maximum: usize) -> String {
    if maximum == 0 {
        return String::new();
    }
    let start = value
        .char_indices()
        .rev()
        .nth(maximum.saturating_sub(1))
        .map(|(index, _)| index)
        .unwrap_or(0);
    value[start..].to_string()
}

fn evidence_window(content: &str, query: &str, maximum: usize) -> String {
    let content_chars = content.chars().collect::<Vec<_>>();
    if content_chars.len() <= maximum || maximum == 0 {
        return content.into();
    }
    let query_chars = query.chars().collect::<Vec<_>>();
    let position = if query_chars.is_empty() {
        content_chars.len().saturating_sub(maximum)
    } else {
        content_chars
            .windows(query_chars.len())
            .position(|window| window == query_chars.as_slice())
            .unwrap_or_else(|| content_chars.len().saturating_sub(maximum))
    };
    let start = position.saturating_sub(maximum / 3);
    let end = start.saturating_add(maximum).min(content_chars.len());
    content_chars[start..end].iter().collect()
}

fn confirmed_stage_result<'a>(
    calls: &'a [StageCall],
    stage_key: &str,
) -> CoreResult<&'a ModelResult> {
    let matching = calls
        .iter()
        .filter(|call| call.job.stage_key == stage_key)
        .collect::<Vec<_>>();
    if matching.len() != 1 || matching[0].state != StageCallState::Confirmed {
        return Err(CoreError::AuthorityConflict(format!(
            "repair evidence stage {stage_key} is not uniquely confirmed"
        )));
    }
    matching[0].result.as_ref().ok_or_else(|| {
        CoreError::AuthorityConflict(format!(
            "confirmed repair evidence stage {stage_key} has no result"
        ))
    })
}

fn storage_error(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

fn native_error(error: quillframe_native::NativeError) -> CoreError {
    CoreError::Storage(error.to_string())
}

#[cfg(any(windows, target_os = "linux"))]
fn require_handle_bound_sqlite() -> CoreResult<()> {
    Ok(())
}

#[cfg(not(any(windows, target_os = "linux")))]
fn require_handle_bound_sqlite() -> CoreResult<()> {
    Err(CoreError::Storage(
        "handle-bound SQLite opening is not implemented on this platform".into(),
    ))
}

#[cfg(all(test, any(windows, target_os = "linux")))]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use quillframe_native::guard_directory;

    use super::*;

    fn temp_root(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!(
            "qf-core-store-{label}-{}-{nonce}",
            std::process::id()
        ))
    }

    fn activate_plan_chain_prefix(
        store: &mut ProjectDatabase,
        graph: &StoryGraph,
    ) -> BTreeMap<String, String> {
        let fixture = crate::planning::fixture_hierarchical_plan_lock();
        let targets = [
            (crate::PlanMode::DesignBook, "BOOK"),
            (crate::PlanMode::DesignVolume, "VOL001"),
            (crate::PlanMode::PlanUnit, "UNIT001"),
        ];
        let mut dependencies = BTreeMap::new();
        for (index, (mode, node_id)) in targets.into_iter().enumerate() {
            let proposal = crate::PlanProposal::create(
                graph,
                crate::PlanProposalInput {
                    mode,
                    node_id: node_id.into(),
                    expected_active_version: 0,
                    body: fixture.layers[index].body.clone(),
                    assumptions: vec![],
                    open_questions: vec![],
                    dependency_fingerprints: dependencies.clone(),
                },
            )
            .unwrap();
            store.save_plan_proposal(&proposal, "T0").unwrap();
            let authorization = crate::AuthorActivation::authorize(
                &proposal,
                "author:test",
                "T0",
                format!("activate-prefix-{index}"),
            )
            .unwrap();
            store.activate_plan(&authorization).unwrap();
            if index == 0 {
                let book_plan = match &proposal.body {
                    crate::PlanBody::Book(book_plan) => book_plan.clone(),
                    _ => unreachable!(),
                };
                let mut setup = fixture_book_setup(book_plan);
                setup.seal().unwrap();
                let setup_receipt = store
                    .propose_book_setup(&setup, 0, "setup-prefix", "T0")
                    .unwrap();
                store
                    .approve_book_setup(
                        &setup_receipt.setup_id,
                        0,
                        &proposal.id.to_string(),
                        &proposal.fingerprint,
                        "author:test",
                        "approve-setup-prefix",
                        "T0",
                    )
                    .unwrap();
            }
            dependencies.insert(
                proposal.target.reference.clone(),
                proposal.fingerprint.clone(),
            );
        }
        dependencies
    }

    fn fixture_book_setup(book_plan: crate::BookPlan) -> crate::BookSetupArtifact {
        let character_bibles = book_plan
            .character_arcs
            .iter()
            .map(|arc| crate::CharacterBible {
                character_id: arc.character_id.clone(),
                display_name: arc.display_name.clone(),
                story_function: arc.narrative_role.clone(),
                external_want: arc.external_want.clone(),
                private_need: arc.internal_need.clone(),
                fear_or_shame: format!("害怕{}", arc.pressure),
                false_belief: "只要不依赖别人就不会付出代价".into(),
                values: vec!["选择权".into()],
                public_mask: "把担心藏在不耐烦后面".into(),
                default_strategy: "先试探，再决定是否合作".into(),
                pressure_leak: "越着急越会挑对方话里的漏洞".into(),
                defense_or_humor: "用挤兑躲开软话".into(),
                voice: crate::CharacterVoiceProfile {
                    baseline: "短句，先反问再给答案".into(),
                    with_intimates: "损人但会补一句实际安排".into(),
                    with_authority: "表面配合，暗中追问边界".into(),
                    under_pressure: "省略主语，命令和讥讽混在一起".into(),
                    avoids_saying: vec!["直接承认害怕".into()],
                },
                knowledge_boundaries: vec!["不知道幕后契约全貌".into()],
                non_negotiables: vec![arc.agency.clone()],
            })
            .collect();
        let relationship_bibles = book_plan
            .relationship_arcs
            .iter()
            .map(|arc| crate::RelationshipBible {
                relationship_id: arc.relationship_id.clone(),
                participant_ids: arc.participant_ids.clone(),
                shared_history: arc.initial_state.clone(),
                current_surface: "嘴上互不相让，行动上暂时合作".into(),
                hidden_debt: arc.pressure.clone(),
                power_balance: "线索与行动力分属两人".into(),
                forbidden_topic: "谁先抛弃过谁".into(),
                default_pattern: "一个挤兑，一个回避，然后用行动收场".into(),
                participant_tactics: arc
                    .participant_ids
                    .iter()
                    .map(|id| (id.clone(), "先试探对方会不会承担代价".into()))
                    .collect(),
            })
            .collect();
        crate::BookSetupArtifact {
            schema: crate::BOOK_SETUP_SCHEMA.into(),
            project_id: "BOOK".into(),
            book_id: "BOOK".into(),
            book_plan,
            character_bibles,
            relationship_bibles,
            world_seeds: vec![crate::WorldSeed {
                seed_id: "WORLD-BLOCKADE".into(),
                topic: "封锁区".into(),
                rule: "公开通道受追兵监控".into(),
                narrative_pressure: "角色必须在速度、隐蔽和互信之间取舍".into(),
                unknowns: vec!["维修井是否已被发现".into()],
            }],
            structure: crate::BookStructureSeed {
                first_volume_title: "封锁区".into(),
                first_unit_title: "穿过封锁".into(),
                first_chapter_title: "返身".into(),
                rolling_outline_chapters: 12,
                minimum_total_characters: Some(1_000_000),
                long_form: None,
            },
            source_evidence_refs: vec![crate::BookSetupSourceEvidence {
                source_id: "SOURCE-BRIEF".into(),
                source_kind: "author_brief".into(),
                source_uri: "project:briefs/opening.md".into(),
                source_revision: "commit:0123456789abcdef".into(),
                content_fingerprint:
                    "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef".into(),
                role: "Primary setup evidence".into(),
            }],
            fingerprint: String::new(),
        }
    }

    fn save_release(
        store: &mut ProjectDatabase,
        candidate_id: &str,
        candidate_fingerprint: &str,
        review_report_fingerprint: &str,
    ) {
        let writer_pack_fingerprint = format!("sha256:{}", "c".repeat(64));
        let tracking_fingerprint = format!("sha256:{}", "d".repeat(64));
        store.connection().execute(
            "INSERT INTO writer_pack_freezes(writer_pack_fingerprint,chapter_id,active_plan_fingerprint,context_freeze_fingerprint,tracking_fingerprint,payload_json,created_at) \
             VALUES(?1,'CH001',?2,?2,?3,'{}','T-release')",
            params![writer_pack_fingerprint,format!("sha256:{}","e".repeat(64)),tracking_fingerprint],
        ).unwrap();
        let receipt = format!("sha256:{}", "f".repeat(64));
        let stages = BTreeMap::from([
            ("context_query_plan".into(), receipt.clone()),
            ("context_greenlight".into(), receipt.clone()),
            ("context_freeze".into(), receipt.clone()),
            ("corpus_greenlight".into(), receipt.clone()),
            ("preference_greenlight".into(), receipt.clone()),
            ("reader_engagement".into(), receipt.clone()),
            ("character_simulation".into(), receipt.clone()),
            ("scene_resolution".into(), receipt.clone()),
            ("surface_scene_0001_SC001".into(), receipt.clone()),
            ("surface_realization".into(), receipt.clone()),
            ("surface_hard_rule_audit".into(), receipt.clone()),
            ("continuity".into(), receipt.clone()),
            ("candidate_self_audit".into(), receipt.clone()),
            ("independent_semantic_gate".into(), receipt.clone()),
            ("settlement_tracking_projection".into(), receipt.clone()),
            ("settlement_tracking_audit".into(), receipt.clone()),
            ("user_visible_gate".into(), receipt),
        ]);
        let release = ProductionRelease::create(
            candidate_id,
            candidate_fingerprint,
            writer_pack_fingerprint,
            tracking_fingerprint,
            review_report_fingerprint,
            stages,
            "T-release",
        )
        .unwrap();
        store.save_production_release(&release).unwrap();
    }

    #[test]
    fn create_and_strict_open_bind_identity_schema_and_hierarchy() {
        let root = temp_root("create");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let created =
            ProjectDatabase::create_reserved(&database, &manifest, "2026-08-31T00:00:00Z").unwrap();
        assert_eq!(created.path(), database);
        let count: u32 = created
            .connection()
            .query_row("SELECT COUNT(*) FROM story_nodes", [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 4);
        assert!(ProjectDatabase::open_strict(&database, &manifest).is_err());
        drop(created);

        let opened = ProjectDatabase::open_strict(&database, &manifest).unwrap();
        drop(opened);
        let wrong = ProjectManifest::new("BOOK", "别的书", "zh-CN").unwrap();
        assert!(ProjectDatabase::open_strict(&database, &wrong).is_err());
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn native_project_create_and_open_use_atomic_four_key_manifest() {
        let root = temp_root("native-project");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let project =
            NativeProject::create(&root, manifest.clone(), "2026-08-31T00:00:00Z").unwrap();
        assert_eq!(project.context.manifest, manifest);
        assert_eq!(
            project.context.data_root,
            root.join(".quillframe").join("data")
        );
        assert!(NativeProject::create(
            &root,
            ProjectManifest::new("OTHER", "覆盖", "zh-CN").unwrap(),
            "2026-08-31T00:00:01Z"
        )
        .is_err());
        drop(project);
        let reopened = NativeProject::open(&root).unwrap();
        assert_eq!(reopened.context.manifest.id, "BOOK");
        drop(reopened);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    #[ignore = "explicit ultralong metadata durability profile"]
    fn ultralong_hierarchy_survives_more_than_one_thousand_chapters() {
        let root = temp_root("ultralong-hierarchy");
        let manifest = ProjectManifest::new("BOOK", "超长篇", "zh-CN").unwrap();
        let mut project = NativeProject::create(&root, manifest, "2026-09-01T00:00:00Z").unwrap();
        for volume_index in 2..=31 {
            let volume = project
                .database
                .create_story_container(
                    "BOOK",
                    StoryKind::Volume,
                    Some("BOOK"),
                    &format!("第{volume_index}卷"),
                    &format!("durability-volume-{volume_index}"),
                    "2026-09-01T00:00:00Z",
                )
                .unwrap();
            for unit_index in 1..=6 {
                let unit = project
                    .database
                    .create_story_container(
                        "BOOK",
                        StoryKind::Unit,
                        Some(&volume.node_id),
                        &format!("第{volume_index}卷第{unit_index}单元"),
                        &format!("durability-unit-{volume_index}-{unit_index}"),
                        "2026-09-01T00:00:00Z",
                    )
                    .unwrap();
                for chapter_index in 1..=6 {
                    project
                        .database
                        .create_chapter(
                            "BOOK",
                            Some(&unit.node_id),
                            &format!("第{volume_index}-{unit_index}-{chapter_index}章"),
                            &format!(
                                "durability-chapter-{volume_index}-{unit_index}-{chapter_index}"
                            ),
                            "2026-09-01T00:00:00Z",
                        )
                        .unwrap();
                }
            }
        }
        let chapter_count: u32 = project
            .database
            .connection()
            .query_row(
                "SELECT COUNT(*) FROM story_nodes WHERE kind='chapter'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(chapter_count, 1_081);
        assert!(project.database.load_story_graph().is_ok());
        drop(project);

        let reopened = NativeProject::open(&root).unwrap();
        assert_eq!(reopened.database.load_story_graph().unwrap().len(), 1_294);
        drop(reopened);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn strict_open_never_repairs_schema_drift() {
        let root = temp_root("drift");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let created =
            ProjectDatabase::create_reserved(&database, &manifest, "2026-08-31T00:00:00Z").unwrap();
        created
            .connection()
            .execute("DELETE FROM schema_fragments WHERE version=25", [])
            .unwrap();
        drop(created);
        assert!(ProjectDatabase::open_strict(&database, &manifest).is_err());
        let rows: u32 = Connection::open(&database)
            .unwrap()
            .query_row("SELECT COUNT(*) FROM schema_fragments", [], |row| {
                row.get(0)
            })
            .unwrap();
        assert_eq!(rows, 24);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn plan_activation_and_tracking_state_survive_restart_with_exact_receipts() {
        let root = temp_root("story-skill-state");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let mut store =
            ProjectDatabase::create_reserved(&database, &manifest, "2026-08-31T00:00:00Z").unwrap();

        let graph = crate::StoryGraph::bootstrap("长篇").unwrap();
        let dependencies = activate_plan_chain_prefix(&mut store, &graph);
        let proposal = crate::PlanProposal::create(
            &graph,
            crate::PlanProposalInput {
                mode: crate::PlanMode::PlanChapter,
                node_id: "CH001".into(),
                expected_active_version: 0,
                body: crate::PlanBody::Chapter(crate::ChapterPlan {
                    contract: crate::ChapterContract {
                        chapter_function: "用有代价的选择建立人物与关系".into(),
                        viewpoint: "主角".into(),
                        entry_state: "与同伴失散".into(),
                        intended_exit_state: "同伴获救但身份暴露".into(),
                        reader_contract: crate::ReaderContract {
                            reader_question: "他会救人还是独自逃走？".into(),
                            visible_reward: "找到维修井".into(),
                            character_choice: "返身救人".into(),
                            cost: "身份暴露".into(),
                            net_change: "同伴获救，追兵锁定主角".into(),
                            next_pull: "出口已被封锁".into(),
                        },
                        constraint_lock: crate::ChapterConstraintLock {
                            length: crate::LengthBand {
                                min: 2800,
                                max: Some(3800),
                                unit: crate::LengthUnit::ChineseCharacters,
                            },
                            must_happen: vec![crate::ConstraintClause {
                                id: "rescue".into(),
                                statement: "主角返身救人".into(),
                            }],
                            must_not_happen: vec![],
                            exact_time_anchors: vec![],
                            stop_point: "出口已被封锁时停笔".into(),
                            end_debt: "出口已被封锁".into(),
                        },
                    },
                    scene_script: crate::SceneScript {
                        scenes: vec![crate::SceneObjective {
                            scene_id: "SC001".into(),
                            ordinal: 1,
                            viewpoint: "主角".into(),
                            location: "废弃车站".into(),
                            entry_state: "与同伴失散".into(),
                            objective: "找到同伴".into(),
                            opposition: "追兵封路".into(),
                            turn: "发现维修井".into(),
                            choice: "返身救人".into(),
                            consequence: "同伴获救但身份暴露".into(),
                            value_shift: "关系从猜疑转为初步互信".into(),
                            information_change: "确认维修井可通向出口".into(),
                            exit_state: "救人成功但身份暴露".into(),
                            emotion_target: "压迫转热血".into(),
                            reader_effect: "认可选择并担心代价".into(),
                        }],
                    },
                }),
                assumptions: vec![],
                open_questions: vec![],
                dependency_fingerprints: dependencies,
            },
        )
        .unwrap();
        store
            .save_plan_proposal(&proposal, "2026-08-31T00:00:01Z")
            .unwrap();
        let authorization = crate::AuthorActivation::authorize(
            &proposal,
            "author:local",
            "2026-08-31T00:00:02Z",
            "activate-ch001-v1",
        )
        .unwrap();
        assert_eq!(store.activate_plan(&authorization).unwrap(), 1);
        assert_eq!(store.activate_plan(&authorization).unwrap(), 1);

        let pack = store
            .freeze_writer_pack_for_chapter("CH001", "2026-08-31T00:00:02Z")
            .unwrap();
        let pack_fingerprint = pack.fingerprint.clone();
        pack.validate().unwrap();
        assert_eq!(pack.scenes.len(), 1);
        assert_eq!(pack.plan_lock.book_plan().unwrap().character_arcs.len(), 2);
        assert_eq!(
            pack.plan_lock.book_plan().unwrap().relationship_arcs.len(),
            1
        );
        assert_eq!(pack.scenes[0].choice, "返身救人");
        assert_eq!(pack.scenes[0].value_shift, "关系从猜疑转为初步互信");
        assert!(pack.reader_pressure.contains("章末"));

        let tracking = crate::TrackingState::empty("BOOK").unwrap();
        store
            .save_tracking_state(&tracking, Some(0), "2026-08-31T00:00:03Z")
            .unwrap();
        assert_eq!(
            store.load_tracking_state("BOOK").unwrap().unwrap(),
            tracking
        );
        drop(store);
        let mut reopened = ProjectDatabase::open_strict(&database, &manifest).unwrap();
        let reloaded_pack = reopened.load_writer_pack(&pack_fingerprint).unwrap();
        assert_eq!(reloaded_pack, pack);
        assert_eq!(
            reopened
                .load_tracking_state("BOOK")
                .unwrap()
                .unwrap()
                .fingerprint,
            tracking.fingerprint
        );
        let graph = reopened.load_story_graph().unwrap();
        let replacement = crate::PlanProposal::create(
            &graph,
            crate::PlanProposalInput {
                mode: crate::PlanMode::DesignBook,
                node_id: "BOOK".into(),
                expected_active_version: 1,
                body: crate::planning::fixture_hierarchical_plan_lock().layers[0]
                    .body
                    .clone(),
                assumptions: vec!["第二版全书方向".into()],
                open_questions: vec![],
                dependency_fingerprints: BTreeMap::new(),
            },
        )
        .unwrap();
        reopened.save_plan_proposal(&replacement, "T4").unwrap();
        let replacement_authorization = crate::AuthorActivation::authorize(
            &replacement,
            "author:local",
            "T4",
            "activate-book-v2",
        )
        .unwrap();
        assert_eq!(
            reopened.activate_plan(&replacement_authorization).unwrap(),
            2
        );
        assert!(reopened
            .freeze_writer_pack_for_chapter("CH001", "T5")
            .is_err());
        drop(reopened);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn settlement_rejects_candidate_without_bound_production_tracking_evidence() {
        let root = temp_root("accept-settle");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let mut store =
            ProjectDatabase::create_reserved(&database, &manifest, "2026-08-31T00:00:00Z").unwrap();
        let candidate_fingerprint =
            crate::fingerprint::sha256_fingerprint("chapter prose".as_bytes());
        store
            .connection()
            .execute(
                "INSERT INTO document_revisions( \
                 revision_id,document_id,content,content_fingerprint,created_at,source,authority_class \
                 ) VALUES('REV1','DOC-CH001','章节正文',?1,'2026-08-31T00:00:01Z','writer','review')",
                [&candidate_fingerprint],
            )
            .unwrap();
        store
            .connection()
            .execute(
                "UPDATE document_revisions SET content='chapter prose' WHERE revision_id='REV1'",
                [],
            )
            .unwrap();
        store
            .connection()
            .execute(
                "INSERT INTO candidates( \
                 candidate_id,document_id,revision_id,task_mode,candidate_kind,status, \
                 content_fingerprint,user_visible_gate,created_at \
                 ) VALUES('C1','DOC-CH001','REV1','DRAFT','draft','review_draft',?1,'ready', \
                 '2026-08-31T00:00:01Z')",
                [&candidate_fingerprint],
            )
            .unwrap();
        let report = crate::ReviewReport::create(crate::ReviewReportInput {
            candidate_fingerprint: candidate_fingerprint.clone(),
            mode: crate::ReviewMode::Solo,
            reviewer_sessions: BTreeSet::from(["reviewer-session".into()]),
            independent_context: true,
            deterministic_prechecks: vec!["format-ok".into()],
            findings: vec![],
            disagreements: vec![],
            infrastructure_failed: false,
        })
        .unwrap();
        store
            .save_review_report(&report, "2026-08-31T00:00:02Z")
            .unwrap();
        save_release(
            &mut store,
            "C1",
            &candidate_fingerprint,
            &report.fingerprint,
        );
        let acceptance = crate::AcceptanceDecision::create(
            "C1",
            &candidate_fingerprint,
            &report.fingerprint,
            "author:local",
            "accept-c1",
            "2026-08-31T00:00:03Z",
        )
        .unwrap();
        let acceptance_id = store.accept_candidate(&acceptance).unwrap();
        assert_eq!(store.accept_candidate(&acceptance).unwrap(), acceptance_id);
        let preflight = store
            .settlement_preflight(&acceptance_id, "chapter:CH001", "2026-08-31T00:00:04Z")
            .unwrap();
        let authorization = crate::SettlementAuthorization::create(
            &preflight,
            "author:local",
            "settle-c1",
            "2026-08-31T00:00:05Z",
        )
        .unwrap();
        assert!(store.apply_settlement(&authorization).is_err());
        let canon_count: u32 = store
            .connection()
            .query_row(
                "SELECT COUNT(*) FROM canon_state WHERE state_key='chapter:CH001'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(canon_count, 0);
        drop(store);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn production_stage_journal_survives_restart_without_duplicate_model_calls() {
        let root = temp_root("production-journal");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "Long Book", "zh-CN").unwrap();
        let mut store = ProjectDatabase::create_reserved(&database, &manifest, "T0").unwrap();
        let tracking_fingerprint = store
            .load_tracking_state("BOOK")
            .unwrap()
            .unwrap()
            .fingerprint;
        let plan_lock = crate::planning::fixture_hierarchical_plan_lock();
        for layer in &plan_lock.layers {
            let task_mode = match layer.target.kind {
                StoryKind::Book => "DESIGN-BOOK",
                StoryKind::Volume => "DESIGN-VOLUME",
                StoryKind::Unit => "PLAN-UNIT",
                StoryKind::Chapter => "PLAN-CHAPTER",
                StoryKind::Scene => unreachable!(),
            };
            store.connection.execute(
                "INSERT INTO plans(plan_id,task_mode,target_id,status,plan_json,content_fingerprint,created_at,updated_at) \
                 VALUES(?1,?2,?3,'active','{}',?4,'T0','T0')",
                params![
                    layer.proposal_id.to_string(),
                    task_mode,
                    layer.target.node_id,
                    layer.proposal_fingerprint
                ],
            ).unwrap();
        }
        let writer_pack = crate::WriterPack::freeze(
            "CH001",
            plan_lock,
            format!("sha256:{}", "5".repeat(64)),
            format!("sha256:{}", "3".repeat(64)),
            &tracking_fingerprint,
            "chapter pull",
            vec![],
            vec![],
        )
        .unwrap();
        let writer_pack_fingerprint = writer_pack.fingerprint.clone();
        store.save_writer_pack(&writer_pack, "T0").unwrap();
        let production = crate::ProductionRequest::freeze(
            "RUN1",
            crate::ProductionTaskMode::Draft,
            "DOC-CH001",
            crate::ProductionIntent {
                instruction: "write chapter".into(),
                reader_grip: "high".into(),
                author_profile: "balanced".into(),
                rule_material: vec![crate::BoundRuleMaterial {
                    id: "request".into(),
                    authority: "current_request".into(),
                    statement: "write chapter".into(),
                }],
                selected_preference_ids: vec![],
                repair_source: None,
                guidance_snapshot: None,
            },
            &writer_pack_fingerprint,
            format!("sha256:{}", "4".repeat(64)),
            "role_capability_route",
            None,
        )
        .unwrap();
        store.start_production(&production, "T1").unwrap();
        store.start_production(&production, "T1").unwrap();
        let model_request = crate::ModelRequest {
            request_id: "MR1".into(),
            model: "MODEL1".into(),
            system: "system".into(),
            user: "user".into(),
            temperature: None,
            max_output_tokens: None,
            absolute_deadline_ms: 30_000,
        };
        let job = crate::StageJob::freeze(
            "reader_engagement",
            "reader",
            model_request,
            format!("sha256:{}", "5".repeat(64)),
        )
        .unwrap();
        let call_id = store
            .dispatch_stage("RUN1", &job, "OWNER1", 30_000, "T2")
            .unwrap();
        assert_eq!(
            store
                .dispatch_stage("RUN1", &job, "OWNER1", 30_000, "T2")
                .unwrap(),
            call_id
        );
        let result = crate::ModelResult::record(
            "MR1",
            "SERVICE1",
            "MODEL1",
            "usable output",
            None,
            crate::ModelUsage {
                input_tokens: Some(10),
                output_tokens: Some(20),
                total_tokens: Some(30),
                cost_micros: None,
            },
        )
        .unwrap();
        store.confirm_stage(&call_id, &result, "T3").unwrap();
        store.confirm_stage(&call_id, &result, "T3").unwrap();
        let unknown_job = crate::StageJob::freeze(
            "surface_realization",
            "writer",
            crate::ModelRequest {
                request_id: "MR2".into(),
                model: "MODEL1".into(),
                system: "system".into(),
                user: "user".into(),
                temperature: None,
                max_output_tokens: None,
                absolute_deadline_ms: 30_000,
            },
            format!("sha256:{}", "6".repeat(64)),
        )
        .unwrap();
        let unknown_call = store
            .dispatch_stage("RUN1", &unknown_job, "OWNER2", 30_000, "T4")
            .unwrap();
        store
            .mark_stage_unconfirmed(&unknown_call, "transport_unknown", "T5")
            .unwrap();
        store
            .mark_stage_unconfirmed(&unknown_call, "transport_unknown", "T5")
            .unwrap();
        assert_eq!(
            store
                .cancel_production("RUN1", 0, "cancel-run-1", "T6")
                .unwrap(),
            (1, false)
        );
        assert_eq!(
            store
                .cancel_production("RUN1", 0, "cancel-run-1", "T6")
                .unwrap(),
            (1, true)
        );
        drop(store);
        let reopened = ProjectDatabase::open_strict(&database, &manifest).unwrap();
        let calls = reopened.production_stage_calls("RUN1").unwrap();
        assert_eq!(calls.len(), 2);
        assert_eq!(calls[0].state, crate::StageCallState::Confirmed);
        assert_eq!(calls[0].result.as_ref().unwrap().usage.cost_micros, None);
        assert_eq!(calls[1].state, crate::StageCallState::Cancelled);
        drop(reopened);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn revision_request_atomically_captures_reusable_learning_evidence() {
        let root = temp_root("revision-learning-intake");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "Long Book", "zh-CN").unwrap();
        let mut store = ProjectDatabase::create_reserved(&database, &manifest, "T0").unwrap();
        let manuscript = "候选正文";
        let candidate_fingerprint = crate::fingerprint::sha256_fingerprint(manuscript.as_bytes());
        let writer_pack_fingerprint = format!("sha256:{}", "a".repeat(64));
        let lineage = crate::CandidateArtifact {
            schema: "quillframe_candidate_artifact_v1".into(),
            candidate_id: "C1".into(),
            chapter_id: "CH001".into(),
            writer_pack_fingerprint,
            parent_candidate_fingerprint: None,
            revision: 1,
            manuscript: manuscript.into(),
            fingerprint: candidate_fingerprint.clone(),
        };
        lineage.validate().unwrap();
        store.connection.execute(
            "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) \
             VALUES('RUN1','DRAFT','DOC-CH001','review',?1,'T1','T1')",
            [format!("sha256:{}", "b".repeat(64))],
        ).unwrap();
        store.connection.execute(
            "INSERT INTO document_revisions(revision_id,document_id,content,content_fingerprint,created_at,source,authority_class) \
             VALUES('REV1','DOC-CH001',?1,?2,'T1','writer','review')",
            params![manuscript,candidate_fingerprint],
        ).unwrap();
        store.connection.execute(
            "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) \
             VALUES('C1','DOC-CH001','REV1','RUN1','DRAFT','draft','review_draft',?1,'PASS','T1')",
            [&candidate_fingerprint],
        ).unwrap();
        store
            .connection
            .execute(
                "INSERT INTO candidate_lineage(candidate_id,lineage_json) VALUES('C1',?1)",
                [serde_json::to_string(&lineage).unwrap()],
            )
            .unwrap();

        let request = crate::RevisionRequest::create(
            "C1",
            &candidate_fingerprint,
            "author:local",
            "对白允许关系性闲话、打岔和答非所问，不要句句解释设定。",
            "revise-c1",
            "T2",
        )
        .unwrap();
        let first = store.request_candidate_revision(&request).unwrap();
        assert!(!first.3);
        assert_eq!(first.2, format!("feedback-revision-{}", first.0));
        for (table, expected) in [
            ("candidate_revision_requests", 1_u32),
            ("checkpoints", 1),
            ("learning_feedback_events", 1),
            ("learning_evidence", 1),
        ] {
            let count: u32 = store
                .connection
                .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
                    row.get(0)
                })
                .unwrap();
            assert_eq!(count, expected, "unexpected {table} count");
        }
        let (feedback_text, source_type, source_id, state): (String, String, String, String) = store
            .connection
            .query_row(
                "SELECT f.feedback_text,f.source_type,f.source_id,e.state FROM learning_feedback_events f \
                 JOIN learning_evidence e ON e.evidence_id='learning-evidence-'||f.event_id WHERE f.event_id=?1",
                [&first.2],
                |row| Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?)),
            )
            .unwrap();
        assert_eq!(feedback_text, request.reason);
        assert_eq!(source_type, "candidate_revision_request");
        assert_eq!(source_id, first.0);
        assert_eq!(state, "awaiting_semantic");

        let replay = crate::RevisionRequest::create(
            "C1",
            &candidate_fingerprint,
            "author:local",
            &request.reason,
            "revise-c1",
            "T3",
        )
        .unwrap();
        let replayed = store.request_candidate_revision(&replay).unwrap();
        assert_eq!(replayed.0, first.0);
        assert_eq!(replayed.2, first.2);
        assert!(replayed.3);
        let feedback_count: u32 = store
            .connection
            .query_row("SELECT COUNT(*) FROM learning_feedback_events", [], |row| {
                row.get(0)
            })
            .unwrap();
        assert_eq!(feedback_count, 1);

        let conflicting = crate::RevisionRequest::create(
            "C1",
            &candidate_fingerprint,
            "author:local",
            "换成另一条要求",
            "revise-c1",
            "T4",
        )
        .unwrap();
        assert!(store.request_candidate_revision(&conflicting).is_err());
        drop(store);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn failed_gate_from_author_requested_revision_preserves_revision_lineage() {
        let root = temp_root("author-revision-failed-gate");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "Long Book", "zh-CN").unwrap();
        let mut store = ProjectDatabase::create_reserved(&database, &manifest, "T0").unwrap();
        let candidate_fingerprint = format!("sha256:{}", "7".repeat(64));
        let stage_fingerprint = format!("sha256:{}", "8".repeat(64));
        let checkpoint_id = "CHECKPOINT-AUTHOR-REVISION";
        store.connection.execute(
            "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) \
             VALUES('RUN-SOURCE','DRAFT','DOC-CH001','review',?1,'T1','T1')",
            [format!("sha256:{}", "1".repeat(64))],
        ).unwrap();
        store.connection.execute(
            "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
             VALUES(?1,'RUN-SOURCE','author_revision_repair_source',?2,?3,'T2')",
            params![
                checkpoint_id,
                serde_json::to_string(&serde_json::json!({"revision":4})).unwrap(),
                candidate_fingerprint
            ],
        ).unwrap();
        let production = crate::ProductionRequest::freeze(
            "RUN-REVISE",
            crate::ProductionTaskMode::Revise,
            "DOC-CH001",
            crate::ProductionIntent {
                instruction: "revise the released candidate".into(),
                reader_grip: "high".into(),
                author_profile: "balanced".into(),
                rule_material: vec![crate::BoundRuleMaterial {
                    id: "request".into(),
                    authority: "current_request".into(),
                    statement: "revise the released candidate".into(),
                }],
                selected_preference_ids: vec![],
                repair_source: Some(crate::RepairBinding {
                    source_run_id: "RUN-SOURCE".into(),
                    source_checkpoint_id: checkpoint_id.into(),
                    expected_candidate_fingerprint: candidate_fingerprint.clone(),
                }),
                guidance_snapshot: None,
            },
            format!("sha256:{}", "2".repeat(64)),
            format!("sha256:{}", "3".repeat(64)),
            "role_capability_route",
            None,
        )
        .unwrap();
        let production_json = serde_json::to_string(&production).unwrap();
        store.connection.execute(
            "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) \
             VALUES(?1,'REVISE','DOC-CH001','executing',?2,'T3','T3')",
            params![production.run_id, production.fingerprint],
        ).unwrap();
        store.connection.execute(
            "INSERT INTO production_executions(run_id,request_fingerprint,request_json,created_at,updated_at) \
             VALUES(?1,?2,?3,'T3','T3')",
            params![production.run_id, production.fingerprint, production_json],
        ).unwrap();

        let failed_checkpoint = store
            .record_failed_gate(
                &production.run_id,
                &candidate_fingerprint,
                "continuity_rule_audit",
                &stage_fingerprint,
                "T4",
            )
            .unwrap();
        let (kind, state): (String, String) = store
            .connection
            .query_row(
                "SELECT checkpoint_kind,state_json FROM checkpoints WHERE checkpoint_id=?1",
                [failed_checkpoint],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(kind, "failed_candidate_repair_source");
        assert_eq!(
            serde_json::from_str::<serde_json::Value>(&state).unwrap()["revision"],
            5
        );
        let status: String = store
            .connection
            .query_row(
                "SELECT status FROM runs WHERE run_id=?1",
                [&production.run_id],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(status, "failed_gate");
        drop(store);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn repair_lineage_walks_multiple_failed_bounded_sources() {
        let root = temp_root("repair-lineage");
        let directory = guard_directory(&root.join("projects").join("BOOK"), true).unwrap();
        let database = directory.path().join("project.sqlite");
        let manifest = ProjectManifest::new("BOOK", "Long Book", "zh-CN").unwrap();
        let store = ProjectDatabase::create_reserved(&database, &manifest, "T0").unwrap();
        let candidate_a = format!("sha256:{}", "a".repeat(64));
        let candidate_b = format!("sha256:{}", "b".repeat(64));
        let writer_pack = format!("sha256:{}", "c".repeat(64));
        let framework = format!("sha256:{}", "d".repeat(64));
        let intent = |repair_source| crate::ProductionIntent {
            instruction: "repair exact candidate".into(),
            reader_grip: "high".into(),
            author_profile: "balanced".into(),
            rule_material: vec![crate::BoundRuleMaterial {
                id: "request".into(),
                authority: "current_request".into(),
                statement: "repair exact candidate".into(),
            }],
            selected_preference_ids: vec![],
            repair_source,
            guidance_snapshot: None,
        };
        let base = crate::ProductionRequest::freeze(
            "RUN-BASE",
            crate::ProductionTaskMode::Draft,
            "DOC-CH001",
            intent(None),
            &writer_pack,
            &framework,
            "role_capability_route",
            None,
        )
        .unwrap();
        let middle = crate::ProductionRequest::freeze(
            "RUN-MIDDLE",
            crate::ProductionTaskMode::Revise,
            "DOC-CH001",
            intent(Some(crate::RepairBinding {
                source_run_id: base.run_id.clone(),
                source_checkpoint_id: "CHECKPOINT-BASE".into(),
                expected_candidate_fingerprint: candidate_a.clone(),
            })),
            &writer_pack,
            &framework,
            "role_capability_route",
            None,
        )
        .unwrap();
        let current = crate::ProductionRequest::freeze(
            "RUN-CURRENT",
            crate::ProductionTaskMode::Revise,
            "DOC-CH001",
            intent(Some(crate::RepairBinding {
                source_run_id: middle.run_id.clone(),
                source_checkpoint_id: "CHECKPOINT-MIDDLE".into(),
                expected_candidate_fingerprint: candidate_b.clone(),
            })),
            &writer_pack,
            &framework,
            "role_capability_route",
            None,
        )
        .unwrap();
        for (request, status) in [
            (&base, "failed_gate"),
            (&middle, "failed_gate"),
            (&current, "executing"),
        ] {
            store.connection.execute(
                "INSERT INTO runs(run_id,task_mode,target_ref,status,request_fingerprint,created_at,updated_at) \
                 VALUES(?1,?2,'DOC-CH001',?3,?4,'T1','T1')",
                params![
                    request.run_id,
                    match request.task_mode {
                        crate::ProductionTaskMode::Draft => "DRAFT",
                        crate::ProductionTaskMode::Revise => "REVISE",
                    },
                    status,
                    request.fingerprint
                ],
            ).unwrap();
            store.connection.execute(
                "INSERT INTO production_executions(run_id,request_fingerprint,request_json,created_at,updated_at) \
                 VALUES(?1,?2,?3,'T1','T1')",
                params![request.run_id,request.fingerprint,serde_json::to_string(request).unwrap()],
            ).unwrap();
        }
        for (checkpoint_id, run_id, candidate, revision) in [
            ("CHECKPOINT-BASE", "RUN-BASE", &candidate_a, 1),
            ("CHECKPOINT-MIDDLE", "RUN-MIDDLE", &candidate_b, 2),
        ] {
            store.connection.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) \
                 VALUES(?1,?2,'failed_candidate_repair_source',?3,?4,'T2')",
                params![checkpoint_id,run_id,serde_json::json!({"revision":revision}).to_string(),candidate],
            ).unwrap();
        }
        assert_eq!(
            store.validated_repair_lineage_run_ids(&current).unwrap(),
            vec!["RUN-MIDDLE".to_string(), "RUN-BASE".to_string()]
        );
        drop(store);
        drop(directory);
        std::fs::remove_dir_all(root).unwrap();
    }
}
