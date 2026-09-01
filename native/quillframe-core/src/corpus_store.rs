use std::path::{Path, PathBuf};

use quillframe_native::{
    guard_directory, read_guarded_file, QfNativeGuard, QfNativeIdentity, QfNativeLock,
};
use rusqlite::{params, Connection, OpenFlags, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

use crate::{
    fingerprint::sha256_fingerprint, AnalyzeStage, ChapterBoundary, CoreError, CoreResult,
    CorpusMechanism, EvidenceAnchor, ModelRequest, ModelResult, PromptAssembly,
    SourceFreeCorpusPack,
};

const CORPUS_SCHEMA: &str = include_str!("../../../persistence/schema/corpus/001_initial.sql");
const MAX_WORK_BYTES: u64 = 128 * 1024 * 1024;
const MAX_SCAN_WORKS: usize = 500;
const MAX_SCAN_DEPTH: usize = 8;
const DEFAULT_PROPOSAL_LIMIT: usize = 24;
const MAX_MODEL_INPUT_BYTES: usize = 512 * 1024;

pub struct CorpusDatabase {
    connection: Connection,
    root: PathBuf,
    _root_guard: QfNativeGuard,
    _database_guard: QfNativeGuard,
    _lock: QfNativeLock,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct CorpusWorkProjection {
    pub work_id: String,
    pub display_label: String,
    pub rights_class: String,
    pub selected: bool,
}

#[derive(Clone, Debug, Serialize)]
pub struct CorpusSelectionProjection {
    pub collection_id: String,
    pub study_id: String,
    pub profile: String,
    pub status: String,
    pub proposal_fingerprint: String,
    pub available_pool_count: u64,
    pub items: Vec<CorpusWorkProjection>,
}

#[derive(Clone, Debug, Serialize)]
pub struct CorpusStudyProjection {
    pub study_id: String,
    pub profile: String,
    pub status: String,
    pub checkpoint_fingerprint: String,
    pub current_stage: String,
    pub current_stage_ordinal: u8,
    pub paused_after_golden_three: bool,
    pub continue_required: bool,
    pub available_pool_count: u64,
    pub activated_count: u64,
    pub analysed_count: u64,
    pub semantic_attempts: u64,
    pub pack_candidates: Vec<Value>,
    pub calls: Vec<Value>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusMechanismDraft {
    pub mechanism_id: String,
    pub reader_need: String,
    pub emotion_chain: Vec<String>,
    pub dramatic_function: String,
    pub replaceable_slots: Vec<String>,
    pub forbidden_copy_elements: Vec<String>,
    pub rhythm_refs: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusStageOutput {
    pub genre: String,
    pub mechanisms: Vec<CorpusMechanismDraft>,
    pub rhythm_summary: String,
    pub style_guidance: Vec<String>,
    pub evidence_summary: String,
    pub analysis: CorpusStageAnalysis,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CorpusStageAnalysis {
    GoldenThree {
        chapter_functions: Vec<String>,
        opening_promise: String,
    },
    ChapterExtraction {
        chapter_summaries: Vec<String>,
        causal_beats: Vec<String>,
        emotional_progression: Vec<String>,
        coverage_state: String,
        next_unit_keys: Vec<String>,
        stop_reason: Option<String>,
    },
    AggregateMechanisms {
        convergences: Vec<String>,
        disagreements: Vec<String>,
        coverage_gaps: Vec<String>,
    },
    StoryEntities {
        character_functions: Vec<String>,
        relationship_pressures: Vec<String>,
        escalation_paths: Vec<String>,
    },
    Report {
        structure_findings: Vec<String>,
        character_engine: Vec<String>,
        payoff_and_reversal: Vec<String>,
    },
    StyleProfile {
        voice_principles: Vec<String>,
        rhythm_protocol: Vec<String>,
        anti_copy_boundaries: Vec<String>,
    },
}

#[derive(Clone, Debug, Serialize)]
pub struct CorpusStageDispatch {
    pub study_id: String,
    pub stage: AnalyzeStage,
    pub unit_key: String,
    pub call_id: String,
    pub request: ModelRequest,
    pub checkpoint_fingerprint: String,
}

impl CorpusStageOutput {
    pub fn validate_for(&self, stage: AnalyzeStage) -> CoreResult<()> {
        if self.genre.trim().is_empty()
            || self.mechanisms.is_empty()
            || self.rhythm_summary.trim().is_empty()
            || self.style_guidance.is_empty()
            || self.evidence_summary.trim().is_empty()
            || self.mechanisms.iter().any(|m| {
                m.mechanism_id.trim().is_empty()
                    || m.reader_need.trim().is_empty()
                    || m.dramatic_function.trim().is_empty()
                    || m.emotion_chain.len() < 3
                    || m.replaceable_slots.len() < 3
                    || m.forbidden_copy_elements.is_empty()
            })
        {
            return Err(CoreError::InvalidProject(
                "corpus semantic artifact is incomplete".into(),
            ));
        }
        let valid_stage = matches!(
            (stage, &self.analysis),
            (AnalyzeStage::GoldenThree, CorpusStageAnalysis::GoldenThree { chapter_functions, opening_promise })
                if !chapter_functions.is_empty() && !opening_promise.trim().is_empty()
        ) || matches!(
            (stage, &self.analysis),
            (AnalyzeStage::ChapterExtraction, CorpusStageAnalysis::ChapterExtraction { chapter_summaries, causal_beats, emotional_progression, coverage_state, next_unit_keys, stop_reason })
                if !chapter_summaries.is_empty() && !causal_beats.is_empty() && !emotional_progression.is_empty()
                    && matches!(coverage_state.as_str(),"expanding"|"saturated")
                    && next_unit_keys.len() <= 8
                    && ((coverage_state=="expanding" && !next_unit_keys.is_empty() && stop_reason.is_none())
                        || (coverage_state=="saturated" && next_unit_keys.is_empty() && stop_reason.as_ref().is_some_and(|reason|!reason.trim().is_empty())))
        ) || matches!(
            (stage, &self.analysis),
            (AnalyzeStage::AggregateMechanisms, CorpusStageAnalysis::AggregateMechanisms { convergences, .. }) if !convergences.is_empty()
        ) || matches!(
            (stage, &self.analysis),
            (AnalyzeStage::StoryEntities, CorpusStageAnalysis::StoryEntities { character_functions, relationship_pressures, escalation_paths })
                if !character_functions.is_empty() && !relationship_pressures.is_empty() && !escalation_paths.is_empty()
        ) || matches!(
            (stage, &self.analysis),
            (AnalyzeStage::Report, CorpusStageAnalysis::Report { structure_findings, character_engine, payoff_and_reversal })
                if !structure_findings.is_empty() && !character_engine.is_empty() && !payoff_and_reversal.is_empty()
        ) || matches!(
            (stage, &self.analysis),
            (AnalyzeStage::StyleProfile, CorpusStageAnalysis::StyleProfile { voice_principles, rhythm_protocol, anti_copy_boundaries })
                if !voice_principles.is_empty() && !rhythm_protocol.is_empty() && !anti_copy_boundaries.is_empty()
        );
        if !valid_stage {
            return Err(CoreError::InvalidProject(
                "corpus artifact does not match its typed analyze stage".into(),
            ));
        }
        Ok(())
    }
}

struct ScannedWork {
    relative_ref: String,
    title: String,
    source_fingerprint: String,
    bytes: u64,
    boundaries: Vec<ChapterBoundary>,
}

impl CorpusDatabase {
    pub fn open(root: impl Into<PathBuf>, created_at: &str) -> CoreResult<Self> {
        let root = root.into();
        let root_guard = guard_directory(&root, true).map_err(native_error)?;
        let lock = QfNativeLock::try_acquire(&root.join(".corpus.lock")).map_err(native_error)?;
        let path = root.join("corpus.sqlite");
        let create = !path.exists();
        let database_guard = quillframe_native::guard_file(
            &path,
            if create {
                quillframe_native::FileMode::CreateNew
            } else {
                quillframe_native::FileMode::OpenReadWrite
            },
            true,
        )
        .map_err(native_error)?;
        let flags = OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX;
        let connection = Connection::open_with_flags(&path, flags).map_err(storage)?;
        connection
            .pragma_update(None, "foreign_keys", "ON")
            .map_err(storage)?;
        connection
            .pragma_update(None, "journal_mode", "WAL")
            .map_err(storage)?;
        connection
            .pragma_update(None, "synchronous", "FULL")
            .map_err(storage)?;
        if create {
            connection.execute_batch(CORPUS_SCHEMA).map_err(storage)?;
            connection.execute("INSERT INTO corpus_schema_identity(scope,release,schema_checksum) VALUES('corpus','1.0',?1)",
                [sha256_fingerprint(CORPUS_SCHEMA.replace("\r\n","\n").as_bytes())]).map_err(storage)?;
        }
        validate_schema(&connection)?;
        if created_at.trim().is_empty() {
            return Err(CoreError::Storage("corpus timestamp is required".into()));
        }
        Ok(Self {
            connection,
            root,
            _root_guard: root_guard,
            _database_guard: database_guard,
            _lock: lock,
        })
    }

    pub fn scan_collection(
        &mut self,
        collection_path: &Path,
        created_at: &str,
    ) -> CoreResult<Value> {
        if !collection_path.is_absolute() {
            return Err(CoreError::InvalidProject(
                "Corpus collection path must be absolute".into(),
            ));
        }
        let root_guard = guard_directory(collection_path, false).map_err(native_error)?;
        let mut works = Vec::new();
        scan_directory(collection_path, collection_path, 0, &mut works)?;
        root_guard.revalidate().map_err(native_error)?;
        if works.is_empty() {
            return Err(CoreError::InvalidProject(
                "Corpus collection contains no eligible UTF-8 txt works".into(),
            ));
        }
        works.sort_by(|a, b| a.relative_ref.cmp(&b.relative_ref));
        let identity = identity_value(root_guard.identity());
        let scan_payload = json!({"root_identity":identity,"works":works.iter().map(|work|json!({
            "relative_ref":work.relative_ref,"source_fingerprint":work.source_fingerprint,"byte_size":work.bytes})).collect::<Vec<_>>()});
        let scan_fingerprint = sha256_fingerprint(
            serde_json::to_vec(&scan_payload)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let collection_id = format!("collection_{}", &scan_fingerprint[7..]);
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        if transaction
            .query_row(
                "SELECT COUNT(*) FROM corpus_collections WHERE collection_id=?1",
                [&collection_id],
                |row| row.get::<_, u64>(0),
            )
            .map_err(storage)?
            == 0
        {
            transaction.execute("INSERT INTO corpus_collections(collection_id,root_path,root_identity_json,scan_fingerprint,work_count,created_at,updated_at) \
                VALUES(?1,?2,?3,?4,?5,?6,?6)",params![collection_id,collection_path.to_string_lossy(),
                serde_json::to_string(&identity).map_err(|error|CoreError::Serialization(error.to_string()))?,scan_fingerprint,works.len(),created_at]).map_err(storage)?;
            for work in &works {
                let public_id = format!(
                    "work_{}",
                    &sha256_fingerprint(
                        format!("{}:{}", scan_fingerprint, work.source_fingerprint).as_bytes()
                    )[7..]
                );
                let version_id = format!(
                    "version_{}",
                    &sha256_fingerprint(
                        format!("{}:{}", public_id, work.source_fingerprint).as_bytes()
                    )[7..]
                );
                transaction.execute("INSERT INTO corpus_work_versions(work_version_id,collection_id,public_work_id,display_title,relative_ref, \
                    source_fingerprint,byte_size,boundaries_json,rights_class,state,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8, \
                    'local_user_provided','eligible',?9)",params![version_id,collection_id,public_id,work.title,work.relative_ref,
                    work.source_fingerprint,work.bytes,serde_json::to_string(&work.boundaries).map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]).map_err(storage)?;
            }
        }
        transaction.commit().map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_corpus_collection_scan_v2","collection_id":collection_id,
            "scan_fingerprint":scan_fingerprint,"eligible_work_count":works.len(),"quarantined_count":0,
            "private_local_only":true,"source_prose_visible":false,"authority":false}),
        )
    }

    pub fn propose_selection(
        &mut self,
        collection_id: &str,
        profile: &str,
        limit: Option<usize>,
        created_at: &str,
    ) -> CoreResult<CorpusSelectionProjection> {
        if !matches!(profile, "general" | "adult_explicit") {
            return Err(CoreError::InvalidProject("unknown Corpus profile".into()));
        }
        if collection_id.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "Corpus collection_id is required".into(),
            ));
        }
        let collection_id: String = self
            .connection
            .query_row(
                "SELECT collection_id FROM corpus_collections WHERE collection_id=?1",
                [collection_id],
                |row| row.get(0),
            )
            .map_err(storage)?;
        let available:u64=self.connection.query_row("SELECT COUNT(*) FROM corpus_work_versions WHERE collection_id=?1 AND state='eligible'",[&collection_id],|row|row.get(0)).map_err(storage)?;
        let take = limit
            .unwrap_or(DEFAULT_PROPOSAL_LIMIT)
            .clamp(1, DEFAULT_PROPOSAL_LIMIT)
            .min(available as usize);
        let mut statement=self.connection.prepare("SELECT public_work_id,display_title,rights_class,byte_size,boundaries_json FROM corpus_work_versions WHERE collection_id=?1 AND state='eligible' ORDER BY public_work_id").map_err(storage)?;
        let pool = statement
            .query_map([&collection_id], |row| {
                let boundaries: String = row.get(4)?;
                let chapter_count = serde_json::from_str::<Vec<ChapterBoundary>>(&boundaries)
                    .map(|items| items.len() as u64)
                    .unwrap_or(0);
                Ok((
                    CorpusWorkProjection {
                        work_id: row.get(0)?,
                        display_label: row.get(1)?,
                        rights_class: row.get(2)?,
                        selected: true,
                    },
                    row.get::<_, u64>(3)?,
                    chapter_count,
                ))
            })
            .map_err(storage)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage)?;
        drop(statement);
        let items = coverage_stratified_selection(pool, take);
        let selection_json = serde_json::to_string(&items)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let proposal_fingerprint = sha256_fingerprint(
            serde_json::to_vec(&json!({"collection_id":collection_id,"profile":profile,
            "work_ids":items.iter().map(|item|&item.work_id).collect::<Vec<_>>()}))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let study_id = format!("study_{}", &proposal_fingerprint[7..]);
        self.connection.execute("INSERT INTO corpus_selection_proposals(study_id,collection_id,profile,proposal_fingerprint,selection_json,status,created_at,updated_at) \
            VALUES(?1,?2,?3,?4,?5,'proposed',?6,?6) ON CONFLICT(study_id) DO NOTHING",
            params![study_id,collection_id,profile,proposal_fingerprint,selection_json,created_at]).map_err(storage)?;
        Ok(CorpusSelectionProjection {
            collection_id,
            study_id,
            profile: profile.into(),
            status: "proposed".into(),
            proposal_fingerprint,
            available_pool_count: available,
            items,
        })
    }

    pub fn selection(&self, study_id: &str) -> CoreResult<CorpusSelectionProjection> {
        let (collection_id, profile, proposal_fingerprint, selection_json, status): (
            String,
            String,
            String,
            String,
            String,
        ) = self
            .connection
            .query_row(
                "SELECT collection_id,profile,proposal_fingerprint,selection_json,status FROM corpus_selection_proposals WHERE study_id=?1",
                [study_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?)),
            )
            .map_err(storage)?;
        let items = serde_json::from_str(&selection_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        let available_pool_count = self
            .connection
            .query_row(
                "SELECT COUNT(*) FROM corpus_work_versions WHERE collection_id=?1 AND state='eligible'",
                [&collection_id],
                |row| row.get(0),
            )
            .map_err(storage)?;
        Ok(CorpusSelectionProjection {
            collection_id,
            study_id: study_id.into(),
            profile,
            status,
            proposal_fingerprint,
            available_pool_count,
            items,
        })
    }

    pub fn confirm_selection(
        &mut self,
        study_id: &str,
        work_ids: &[String],
        proposal_fingerprint: &str,
        profile: &str,
        created_at: &str,
    ) -> CoreResult<CorpusSelectionProjection> {
        if work_ids.is_empty()
            || work_ids.len() > DEFAULT_PROPOSAL_LIMIT
            || work_ids
                .iter()
                .collect::<std::collections::BTreeSet<_>>()
                .len()
                != work_ids.len()
        {
            return Err(CoreError::InvalidProject(
                "Corpus selection must be a non-empty minimal cohort".into(),
            ));
        }
        let (collection,stored_profile,stored_fp,selection_json,status):(String,String,String,String,String)=self.connection.query_row(
            "SELECT collection_id,profile,proposal_fingerprint,selection_json,status FROM corpus_selection_proposals WHERE study_id=?1",
            [study_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?))).map_err(storage)?;
        if stored_profile != profile
            || stored_fp != proposal_fingerprint
            || !matches!(status.as_str(), "proposed" | "confirmed")
        {
            return Err(CoreError::AuthorityConflict(
                "Corpus proposal changed before confirmation".into(),
            ));
        }
        let proposed: Vec<CorpusWorkProjection> = serde_json::from_str(&selection_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        if work_ids
            .iter()
            .any(|id| !proposed.iter().any(|item| &item.work_id == id))
        {
            return Err(CoreError::AuthorityConflict(
                "Corpus confirmation contains a work outside the proposal".into(),
            ));
        }
        let confirmed = proposed
            .into_iter()
            .filter(|item| work_ids.contains(&item.work_id))
            .collect::<Vec<_>>();
        let confirmed_json = serde_json::to_string(&confirmed)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let checkpoint = sha256_fingerprint(
            serde_json::to_vec(
                &json!({"study_id":study_id,"stage":"boundary_index","work_ids":work_ids,
            "proposal_fingerprint":proposal_fingerprint}),
            )
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        transaction.execute("UPDATE corpus_selection_proposals SET selection_json=?2,status='confirmed',updated_at=?3 WHERE study_id=?1",
            params![study_id,confirmed_json,created_at]).map_err(storage)?;
        transaction.execute("INSERT INTO corpus_studies(study_id,current_stage,checkpoint_fingerprint,progress_json,created_at,updated_at) \
            VALUES(?1,'boundary_index',?2,?3,?4,?4) ON CONFLICT(study_id) DO NOTHING",
            params![study_id,checkpoint,serde_json::to_string(&json!({"completed_stages":["boundary_index"],"selected_work_ids":work_ids}))
                .map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]).map_err(storage)?;
        transaction.execute("UPDATE corpus_studies SET current_stage='golden_three',updated_at=?2 WHERE study_id=?1 AND current_stage='boundary_index'",
            params![study_id,created_at]).map_err(storage)?;
        transaction.commit().map_err(storage)?;
        let available=self.connection.query_row("SELECT COUNT(*) FROM corpus_work_versions WHERE collection_id=?1 AND state='eligible'",[&collection],|row|row.get(0)).map_err(storage)?;
        Ok(CorpusSelectionProjection {
            collection_id: collection,
            study_id: study_id.into(),
            profile: profile.into(),
            status: "confirmed".into(),
            proposal_fingerprint: proposal_fingerprint.into(),
            available_pool_count: available,
            items: confirmed,
        })
    }

    pub fn dispatch_next_stage(
        &mut self,
        study_id: &str,
        model: &str,
        created_at: &str,
    ) -> CoreResult<Option<CorpusStageDispatch>> {
        if model.trim().is_empty() {
            return Err(CoreError::InvalidProject(
                "Corpus analysis requires a model".into(),
            ));
        }
        let (stage_key,checkpoint,status):(String,String,String)=self.connection.query_row(
            "SELECT s.current_stage,s.checkpoint_fingerprint,p.status FROM corpus_studies s JOIN corpus_selection_proposals p USING(study_id) WHERE s.study_id=?1",
            [study_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))).map_err(storage)?;
        if status == "paused_golden_three" {
            return Err(CoreError::AuthorityConflict(
                "Golden Three preview is paused; explicit continuation is required".into(),
            ));
        }
        if matches!(status.as_str(), "complete" | "cancelled") {
            return Ok(None);
        }
        let stage = parse_stage(&stage_key)?;
        let all_units = self.stage_units(study_id, stage)?;
        let units = if stage == AnalyzeStage::ChapterExtraction {
            let (progress_json, prior_calls): (String, u64) = self.connection.query_row(
                "SELECT progress_json,(SELECT COUNT(*) FROM corpus_stage_calls c WHERE c.study_id=s.study_id AND c.stage_key='chapter_extraction') \
                 FROM corpus_studies s WHERE study_id=?1",
                [study_id],|row|Ok((row.get(0)?,row.get(1)?))
            ).map_err(storage)?;
            let progress: Value = serde_json::from_str(&progress_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let requested = progress
                .get("chapter_extraction_queue")
                .and_then(Value::as_array)
                .map(|values| {
                    values
                        .iter()
                        .filter_map(Value::as_str)
                        .map(str::to_string)
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            if prior_calls == 0 {
                all_units.first().cloned().into_iter().collect()
            } else {
                requested
            }
        } else {
            all_units.clone()
        };
        let mut pending = None;
        for unit in units {
            let state:Option<String>=self.connection.query_row(
                "SELECT state FROM corpus_stage_calls WHERE study_id=?1 AND stage_key=?2 AND unit_key=?3",
                params![study_id,stage_key,unit],|row|row.get(0)).optional().map_err(storage)?;
            match state.as_deref() {
                Some("confirmed") => continue,
                Some("dispatched" | "unconfirmed") => {
                    return Err(CoreError::ModelRuntime(
                        "unconfirmed_model_outcome: Corpus stage will not be sent twice".into(),
                    ))
                }
                Some(_) => {
                    return Err(CoreError::AuthorityConflict(
                        "Corpus stage call is not executable".into(),
                    ))
                }
                None => {
                    pending = Some(unit);
                    break;
                }
            }
        }
        let Some(unit_key) = pending else {
            if stage != AnalyzeStage::ChapterExtraction {
                self.advance_stage(study_id, stage, created_at)?;
            }
            return Ok(None);
        };
        let (input, evidence) = self.stage_input(study_id, stage, &unit_key)?;
        let input_bytes = serde_json::to_vec(&input)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if input_bytes.len() > MAX_MODEL_INPUT_BYTES {
            return Err(CoreError::ContextBoundary(
            "Corpus stage input exceeds 512 KiB; chapter chunking or cohort size must be reduced".into()));
        }
        let assembly =
            PromptAssembly::build(&format!("corpus_{stage_key}"), corpus_system(stage), input)?;
        let input_fingerprint = assembly.fingerprint.clone();
        let request_id = format!(
            "corpus-{}-{}",
            stage_key,
            &sha256_fingerprint(format!("{study_id}:{unit_key}:{input_fingerprint}").as_bytes())
                [7..23]
        );
        let request = ModelRequest {
            request_id: request_id.clone(),
            model: model.into(),
            system: assembly.system_text(),
            user: assembly.user_text()?,
            temperature: Some(if stage == AnalyzeStage::StyleProfile {
                0.25
            } else {
                0.15
            }),
            max_output_tokens: Some(6_000),
            absolute_deadline_ms: 120_000,
        };
        let call_id = format!("call_{}", uuid::Uuid::new_v4());
        let job = json!({"schema":"quillframe_corpus_stage_job_v1","stage":stage_key,"unit_key":unit_key,
            "model":model,"input_fingerprint":input_fingerprint,"evidence":evidence,
            "prompt_itemization":assembly.itemization(),"prompt_persisted":false});
        self.connection.execute("INSERT INTO corpus_stage_calls(call_id,study_id,stage_key,unit_key,request_id,input_fingerprint,job_json,state,created_at,updated_at) \
            VALUES(?1,?2,?3,?4,?5,?6,?7,'dispatched',?8,?8)",params![call_id,study_id,stage_key,unit_key,request_id,
            input_fingerprint,serde_json::to_string(&job).map_err(|error|CoreError::Serialization(error.to_string()))?,created_at]).map_err(storage)?;
        Ok(Some(CorpusStageDispatch {
            study_id: study_id.into(),
            stage,
            unit_key,
            call_id,
            request,
            checkpoint_fingerprint: checkpoint,
        }))
    }

    pub fn confirm_stage(
        &mut self,
        study_id: &str,
        call_id: &str,
        result: &ModelResult,
        updated_at: &str,
    ) -> CoreResult<Value> {
        result.validate()?;
        let (stage_key,unit_key,request_id,state,job_json):(String,String,String,String,String)=self.connection.query_row(
            "SELECT stage_key,unit_key,request_id,state,job_json FROM corpus_stage_calls WHERE call_id=?1 AND study_id=?2",
            params![call_id,study_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?))).map_err(storage)?;
        if state != "dispatched" || request_id != result.request_id {
            return Err(CoreError::AuthorityConflict(
                "Corpus result does not match its dispatched call".into(),
            ));
        }
        let output: CorpusStageOutput = serde_json::from_str(&result.content).map_err(|error| {
            CoreError::ModelRuntime(format!("Corpus stage returned invalid JSON: {error}"))
        })?;
        let stage = parse_stage(&stage_key)?;
        output.validate_for(stage)?;
        let extraction_control = if let CorpusStageAnalysis::ChapterExtraction {
            coverage_state,
            next_unit_keys,
            stop_reason,
            ..
        } = &output.analysis
        {
            let universe = self.stage_units(study_id, stage)?;
            let unique = next_unit_keys
                .iter()
                .collect::<std::collections::BTreeSet<_>>();
            let already_confirmed = self
                .connection
                .prepare(
                    "SELECT unit_key FROM corpus_stage_calls WHERE study_id=?1 AND stage_key='chapter_extraction' AND state='confirmed'",
                )
                .map_err(storage)?
                .query_map([study_id], |row| row.get::<_, String>(0))
                .map_err(storage)?
                .collect::<Result<std::collections::BTreeSet<_>, _>>()
                .map_err(storage)?;
            if unique.len() != next_unit_keys.len()
                || next_unit_keys.iter().any(|next| {
                    next == &unit_key
                        || !universe.contains(next)
                        || already_confirmed.contains(next)
                })
            {
                return Err(CoreError::AuthorityConflict(
                    "Corpus evidence request selected duplicate, unknown or completed units".into(),
                ));
            }
            Some((
                coverage_state.clone(),
                next_unit_keys.clone(),
                stop_reason.clone(),
            ))
        } else {
            None
        };
        let job: Value = serde_json::from_str(&job_json)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        let evidence: Vec<EvidenceAnchor> =
            serde_json::from_value(job.get("evidence").cloned().unwrap_or_else(|| json!([])))
                .map_err(|error| CoreError::Storage(error.to_string()))?;
        if evidence.is_empty() {
            return Err(CoreError::AuthorityConflict(
                "Corpus semantic result has no bound source evidence".into(),
            ));
        }
        let artifact_fingerprint = sha256_fingerprint(result.content.as_bytes());
        let evidence_fp = sha256_fingerprint(
            serde_json::to_vec(&evidence)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let artifact_id = format!(
            "artifact_{}",
            &sha256_fingerprint(
                format!("{study_id}:{stage_key}:{unit_key}:{artifact_fingerprint}").as_bytes()
            )[7..]
        );
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        transaction.execute("INSERT INTO corpus_artifacts(artifact_id,study_id,stage_key,unit_key,payload_json,artifact_fingerprint,evidence_bundle_fingerprint,created_at) \
            VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",params![artifact_id,study_id,stage_key,unit_key,result.content,artifact_fingerprint,evidence_fp,updated_at]).map_err(storage)?;
        let changed=transaction.execute("UPDATE corpus_stage_calls SET state='confirmed',result_json=?1,result_fingerprint=?2,updated_at=?3 \
            WHERE call_id=?4 AND state='dispatched'",params![serde_json::to_string(result).map_err(|error|CoreError::Serialization(error.to_string()))?,
            result.fingerprint,updated_at,call_id]).map_err(storage)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "Corpus call changed before confirmation".into(),
            ));
        }
        if let Some((coverage_state, next_unit_keys, stop_reason)) = &extraction_control {
            let progress_json: String = transaction
                .query_row(
                    "SELECT progress_json FROM corpus_studies WHERE study_id=?1",
                    [study_id],
                    |row| row.get(0),
                )
                .map_err(storage)?;
            let mut progress: Value = serde_json::from_str(&progress_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let object = progress.as_object_mut().ok_or_else(|| {
                CoreError::Storage("Corpus progress snapshot is not an object".into())
            })?;
            object.insert(
                "chapter_extraction_coverage".into(),
                Value::String(coverage_state.clone()),
            );
            object.insert(
                "chapter_extraction_queue".into(),
                serde_json::to_value(next_unit_keys)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?,
            );
            object.insert(
                "chapter_extraction_stop_reason".into(),
                serde_json::to_value(stop_reason)
                    .map_err(|error| CoreError::Serialization(error.to_string()))?,
            );
            transaction
                .execute(
                    "UPDATE corpus_studies SET progress_json=?2,updated_at=?3 WHERE study_id=?1",
                    params![
                        study_id,
                        serde_json::to_string(&progress)
                            .map_err(|error| CoreError::Serialization(error.to_string()))?,
                        updated_at
                    ],
                )
                .map_err(storage)?;
        }
        transaction.commit().map_err(storage)?;
        let units = self.stage_units(study_id, stage)?;
        let confirmed:u64=self.connection.query_row("SELECT COUNT(*) FROM corpus_stage_calls WHERE study_id=?1 AND stage_key=?2 AND state='confirmed'",
            params![study_id,stage_key],|row|row.get(0)).map_err(storage)?;
        let saturated = extraction_control
            .as_ref()
            .is_some_and(|(coverage_state, _, _)| coverage_state == "saturated");
        if saturated || confirmed == units.len() as u64 {
            self.advance_stage(study_id, stage, updated_at)?;
        }
        Ok(
            json!({"schema":"quillframe_corpus_stage_confirmation_v1","study_id":study_id,"stage":stage_key,
            "unit_key":unit_key,"artifact_fingerprint":artifact_fingerprint,"confirmed_units":confirmed,"total_units":units.len(),"authority":false}),
        )
    }

    pub fn mark_stage_unconfirmed(
        &mut self,
        study_id: &str,
        call_id: &str,
        error_code: &str,
        updated_at: &str,
    ) -> CoreResult<()> {
        let changed = self
            .connection
            .execute(
                "UPDATE corpus_stage_calls SET state='unconfirmed',error_code=?1,updated_at=?2 \
            WHERE study_id=?3 AND call_id=?4 AND state='dispatched'",
                params![error_code, updated_at, study_id, call_id],
            )
            .map_err(storage)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "Corpus call changed before unconfirmed outcome was recorded".into(),
            ));
        }
        Ok(())
    }

    pub fn continue_after_golden_three(
        &mut self,
        study_id: &str,
        expected_checkpoint: &str,
        authorization: &str,
        created_at: &str,
    ) -> CoreResult<()> {
        if authorization.trim().is_empty() {
            return Err(CoreError::AuthorityConflict(
                "Corpus continuation requires explicit author authorization".into(),
            ));
        }
        let (stage,status,checkpoint):(String,String,String)=self.connection.query_row(
            "SELECT s.current_stage,p.status,s.checkpoint_fingerprint FROM corpus_studies s JOIN corpus_selection_proposals p USING(study_id) WHERE s.study_id=?1",
            [study_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))).map_err(storage)?;
        if stage != "golden_three"
            || status != "paused_golden_three"
            || checkpoint != expected_checkpoint
        {
            return Err(CoreError::AuthorityConflict(
                "Golden Three checkpoint changed before continuation".into(),
            ));
        }
        let authorization_fp = sha256_fingerprint(
            serde_json::to_vec(&json!({"study_id":study_id,"checkpoint":checkpoint,
            "authorization":authorization}))
            .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        transaction.execute("INSERT INTO corpus_continue_authorizations(authorization_id,study_id,expected_checkpoint_fingerprint,authorization_fingerprint,created_at) \
            VALUES(?1,?2,?3,?4,?5)",params![format!("continue_{}",uuid::Uuid::new_v4()),study_id,checkpoint,authorization_fp,created_at]).map_err(storage)?;
        let next_checkpoint = checkpoint_for(study_id, "chapter_extraction", &authorization_fp)?;
        transaction.execute("UPDATE corpus_studies SET current_stage='chapter_extraction',checkpoint_fingerprint=?2,updated_at=?3 WHERE study_id=?1",
            params![study_id,next_checkpoint,created_at]).map_err(storage)?;
        transaction.execute("UPDATE corpus_selection_proposals SET status='running',updated_at=?2 WHERE study_id=?1",
            params![study_id,created_at]).map_err(storage)?;
        transaction.commit().map_err(storage)
    }

    pub fn source_free_pack(&self, study_id: &str) -> CoreResult<Option<SourceFreeCorpusPack>> {
        let payload:Option<String>=self.connection.query_row("SELECT payload_json FROM corpus_pack_candidates WHERE study_id=?1 AND leakage_gate='pass'",
            [study_id],|row|row.get(0)).optional().map_err(storage)?;
        payload
            .map(|value| {
                serde_json::from_str::<SourceFreeCorpusPack>(&value)
                    .map_err(|error| CoreError::Storage(error.to_string()))
                    .and_then(|pack| {
                        pack.validate()?;
                        Ok(pack)
                    })
            })
            .transpose()
    }

    pub fn study_status(&self, study_id: &str) -> CoreResult<Value> {
        let (stage,checkpoint,status,profile,selection):(String,String,String,String,String)=self.connection.query_row(
            "SELECT s.current_stage,s.checkpoint_fingerprint,p.status,p.profile,p.selection_json FROM corpus_studies s JOIN corpus_selection_proposals p USING(study_id) WHERE s.study_id=?1",
            [study_id],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?,row.get(4)?))).map_err(storage)?;
        let items: Vec<CorpusWorkProjection> = serde_json::from_str(&selection)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        let semantic_attempts: u64 = self
            .connection
            .query_row(
                "SELECT COUNT(*) FROM corpus_stage_calls WHERE study_id=?1",
                [study_id],
                |row| row.get(0),
            )
            .map_err(storage)?;
        let analysed_count:u64=self.connection.query_row("SELECT COUNT(DISTINCT unit_key) FROM corpus_stage_calls WHERE study_id=?1 AND state='confirmed'",[study_id],|row|row.get(0)).map_err(storage)?;
        let pack = self.source_free_pack(study_id)?;
        Ok(
            json!({"schema":"quillframe_corpus_study_status_v2","study_id":study_id,"profile":profile,"status":status,
            "current_stage":stage,"current_stage_ordinal":parse_stage(&stage)?.ordinal(),"checkpoint_fingerprint":checkpoint,
            "paused_after_golden_three":status=="paused_golden_three","continue_required":status=="paused_golden_three",
            "available_pool_count":items.len(),"activated_count":items.len(),"analysed_count":analysed_count,
            "semantic_attempts":semantic_attempts,"source_free_pack_fingerprint":pack.as_ref().map(|value|&value.fingerprint),
            "source_prose_visible":false,"authority":false}),
        )
    }

    pub fn cancel_study(&mut self, study_id: &str, updated_at: &str) -> CoreResult<Value> {
        let changed=self.connection.execute("UPDATE corpus_selection_proposals SET status='cancelled',updated_at=?2 WHERE study_id=?1 AND status NOT IN ('complete','cancelled')",
            params![study_id,updated_at]).map_err(storage)?;
        self.connection
            .execute(
                "UPDATE corpus_studies SET cancel_requested=1,updated_at=?2 WHERE study_id=?1",
                params![study_id, updated_at],
            )
            .map_err(storage)?;
        Ok(
            json!({"schema":"quillframe_corpus_study_status_v2","study_id":study_id,"status":if changed==1{"cancelled"}else{"unchanged"},"authority":false}),
        )
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    fn stage_units(&self, study_id: &str, stage: AnalyzeStage) -> CoreResult<Vec<String>> {
        if !matches!(
            stage,
            AnalyzeStage::GoldenThree
                | AnalyzeStage::ChapterExtraction
                | AnalyzeStage::StoryEntities
        ) {
            return Ok(vec!["all".into()]);
        }
        let (_, items) = self.confirmed_selection(study_id)?;
        if stage != AnalyzeStage::ChapterExtraction {
            return Ok(items.into_iter().map(|item| item.work_id).collect());
        }
        let mut units = Vec::new();
        for item in items {
            let boundaries_json: String = self
                .connection
                .query_row(
                    "SELECT boundaries_json FROM corpus_work_versions WHERE public_work_id=?1",
                    [&item.work_id],
                    |row| row.get(0),
                )
                .map_err(storage)?;
            let boundaries: Vec<ChapterBoundary> = serde_json::from_str(&boundaries_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let mut start = 0usize;
            while start < boundaries.len() {
                let mut end = start + 1;
                while end < boundaries.len()
                    && boundaries[end]
                        .end_byte
                        .saturating_sub(boundaries[start].start_byte)
                        <= 192 * 1024
                {
                    end += 1;
                }
                units.push(format!("{}:{}:{}", item.work_id, start, end));
                start = end;
            }
        }
        Ok(units)
    }

    fn confirmed_selection(
        &self,
        study_id: &str,
    ) -> CoreResult<(String, Vec<CorpusWorkProjection>)> {
        let (collection,status,selection):(String,String,String)=self.connection.query_row(
            "SELECT collection_id,status,selection_json FROM corpus_selection_proposals WHERE study_id=?1",[study_id],
            |row|Ok((row.get(0)?,row.get(1)?,row.get(2)?))).map_err(storage)?;
        if !matches!(
            status.as_str(),
            "confirmed" | "running" | "paused_golden_three" | "complete"
        ) {
            return Err(CoreError::AuthorityConflict(
                "Corpus selection has not been confirmed".into(),
            ));
        }
        let items = serde_json::from_str(&selection)
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        Ok((collection, items))
    }

    fn stage_input(
        &self,
        study_id: &str,
        stage: AnalyzeStage,
        unit: &str,
    ) -> CoreResult<(Value, Vec<EvidenceAnchor>)> {
        let (collection, items) = self.confirmed_selection(study_id)?;
        if matches!(
            stage,
            AnalyzeStage::GoldenThree | AnalyzeStage::ChapterExtraction
        ) {
            let work_id = unit.split(':').next().unwrap_or(unit);
            if !items.iter().any(|item| item.work_id == work_id) {
                return Err(CoreError::AuthorityConflict(
                    "Corpus stage unit is outside the confirmed selection".into(),
                ));
            }
            let (root_path,relative_ref,source_fp,boundaries_json):(String,String,String,String)=self.connection.query_row(
                "SELECT c.root_path,w.relative_ref,w.source_fingerprint,w.boundaries_json FROM corpus_work_versions w JOIN corpus_collections c USING(collection_id) \
                 WHERE w.collection_id=?1 AND w.public_work_id=?2",params![collection,work_id],
                |row|Ok((row.get(0)?,row.get(1)?,row.get(2)?,row.get(3)?))).map_err(storage)?;
            let path = PathBuf::from(root_path)
                .join(relative_ref.replace('/', std::path::MAIN_SEPARATOR_STR));
            let (raw, _) = read_guarded_file(&path, MAX_WORK_BYTES).map_err(native_error)?;
            let bytes = raw.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&raw);
            if sha256_fingerprint(bytes) != source_fp {
                return Err(CoreError::AuthorityConflict(
                    "Corpus source changed after scan".into(),
                ));
            }
            let boundaries: Vec<ChapterBoundary> = serde_json::from_str(&boundaries_json)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            let (start_index, end_index) = if stage == AnalyzeStage::GoldenThree {
                (0, boundaries.len().min(3))
            } else {
                let parts = unit.rsplitn(3, ':').collect::<Vec<_>>();
                if parts.len() != 3 {
                    return Err(CoreError::Storage("invalid chapter extraction unit".into()));
                }
                (
                    parts[1]
                        .parse::<usize>()
                        .map_err(|_| CoreError::Storage("invalid chapter start".into()))?,
                    parts[0]
                        .parse::<usize>()
                        .map_err(|_| CoreError::Storage("invalid chapter end".into()))?,
                )
            };
            let slice = &boundaries[start_index..end_index];
            let start = slice.first().unwrap().start_byte as usize;
            let end = slice.last().unwrap().end_byte as usize;
            let excerpt = std::str::from_utf8(&bytes[start..end])
                .map_err(|_| CoreError::Storage("Corpus excerpt lost UTF-8 boundaries".into()))?;
            let evidence = slice
                .iter()
                .map(|boundary| EvidenceAnchor {
                    work_id: work_id.to_owned(),
                    chapter: boundary.chapter,
                    start_byte: boundary.start_byte,
                    end_byte: boundary.end_byte,
                    excerpt_fingerprint: sha256_fingerprint(
                        &bytes[boundary.start_byte as usize..boundary.end_byte as usize],
                    ),
                })
                .collect();
            let remaining_unit_keys = if stage == AnalyzeStage::ChapterExtraction {
                self.stage_units(study_id, stage)?
                    .into_iter()
                    .filter(|candidate| candidate != unit)
                    .filter(|candidate| {
                        self.connection.query_row(
                            "SELECT COUNT(*) FROM corpus_stage_calls WHERE study_id=?1 AND stage_key='chapter_extraction' AND unit_key=?2",
                            params![study_id,candidate],|row|row.get::<_,u64>(0)
                        ).unwrap_or(1)==0
                    })
                    .take(64)
                    .collect::<Vec<_>>()
            } else {
                Vec::new()
            };
            return Ok((
                json!({"study_id":study_id,"stage":stage_name(stage),"anonymous_work_id":work_id,
                "chapters":excerpt,"remaining_unit_keys":remaining_unit_keys,"contract":corpus_contract(stage)}),
                evidence,
            ));
        }
        let mut statement=self.connection.prepare("SELECT a.payload_json,c.job_json FROM corpus_artifacts a JOIN corpus_stage_calls c \
            ON c.study_id=a.study_id AND c.stage_key=a.stage_key AND c.unit_key=a.unit_key WHERE a.study_id=?1 ORDER BY a.stage_key,a.unit_key")
            .map_err(storage)?;
        let rows = statement
            .query_map([study_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })
            .map_err(storage)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage)?;
        let mut artifacts = Vec::new();
        let mut evidence = Vec::new();
        for (payload, job) in rows {
            artifacts.push(
                serde_json::from_str::<Value>(&payload)
                    .map_err(|error| CoreError::Storage(error.to_string()))?,
            );
            let job: Value = serde_json::from_str(&job)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            evidence.extend(
                serde_json::from_value::<Vec<EvidenceAnchor>>(
                    job.get("evidence").cloned().unwrap_or_else(|| json!([])),
                )
                .map_err(|error| CoreError::Storage(error.to_string()))?,
            );
        }
        evidence.sort_by_key(|item| (item.chapter, item.start_byte, item.end_byte));
        evidence.dedup();
        Ok((
            json!({"study_id":study_id,"stage":stage_name(stage),"prior_semantic_artifacts":artifacts,
            "contract":corpus_contract(stage)}),
            evidence,
        ))
    }

    fn advance_stage(
        &mut self,
        study_id: &str,
        stage: AnalyzeStage,
        updated_at: &str,
    ) -> CoreResult<()> {
        if stage == AnalyzeStage::GoldenThree {
            let fp = checkpoint_for(study_id, "golden_three_paused", updated_at)?;
            let transaction = self
                .connection
                .transaction_with_behavior(TransactionBehavior::Immediate)
                .map_err(storage)?;
            transaction.execute("UPDATE corpus_studies SET checkpoint_fingerprint=?2,updated_at=?3 WHERE study_id=?1",params![study_id,fp,updated_at]).map_err(storage)?;
            transaction.execute("UPDATE corpus_selection_proposals SET status='paused_golden_three',updated_at=?2 WHERE study_id=?1",params![study_id,updated_at]).map_err(storage)?;
            return transaction.commit().map_err(storage);
        }
        if let Some(next) = next_stage(stage) {
            let name = stage_name(next);
            let fp = checkpoint_for(study_id, name, updated_at)?;
            self.connection.execute("UPDATE corpus_studies SET current_stage=?2,checkpoint_fingerprint=?3,updated_at=?4 WHERE study_id=?1",
                params![study_id,name,fp,updated_at]).map_err(storage)?;
            self.connection.execute("UPDATE corpus_selection_proposals SET status='running',updated_at=?2 WHERE study_id=?1",params![study_id,updated_at]).map_err(storage)?;
        } else {
            self.finish_pack(study_id, updated_at)?;
        }
        Ok(())
    }

    fn finish_pack(&mut self, study_id: &str, created_at: &str) -> CoreResult<()> {
        let mut statement=self.connection.prepare("SELECT a.payload_json,c.job_json FROM corpus_artifacts a JOIN corpus_stage_calls c \
            ON c.study_id=a.study_id AND c.stage_key=a.stage_key AND c.unit_key=a.unit_key WHERE a.study_id=?1 AND a.stage_key='style_profile'")
            .map_err(storage)?;
        let rows = statement
            .query_map([study_id], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })
            .map_err(storage)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage)?;
        drop(statement);
        let mut outputs = Vec::new();
        let mut evidence = Vec::new();
        for (payload, job) in rows {
            outputs.push(
                serde_json::from_str::<CorpusStageOutput>(&payload)
                    .map_err(|error| CoreError::Storage(error.to_string()))?,
            );
            let job: Value = serde_json::from_str(&job)
                .map_err(|error| CoreError::Storage(error.to_string()))?;
            evidence.extend(
                serde_json::from_value::<Vec<EvidenceAnchor>>(job["evidence"].clone())
                    .map_err(|error| CoreError::Storage(error.to_string()))?,
            );
        }
        let output = outputs.into_iter().next().ok_or_else(|| {
            CoreError::AuthorityConflict("style profile artifact is missing".into())
        })?;
        let mechanisms = output
            .mechanisms
            .into_iter()
            .map(|item| CorpusMechanism {
                mechanism_id: item.mechanism_id,
                reader_need: item.reader_need,
                emotion_chain: item.emotion_chain,
                dramatic_function: item.dramatic_function,
                replaceable_slots: item.replaceable_slots,
                forbidden_copy_elements: item.forbidden_copy_elements,
                rhythm_refs: item.rhythm_refs,
                evidence: evidence.clone(),
            })
            .collect();
        let pack = SourceFreeCorpusPack::build(
            output.genre,
            mechanisms,
            output.rhythm_summary,
            output.style_guidance,
        )?;
        let (_, items) = self.confirmed_selection(study_id)?;
        let serialized = serde_json::to_string(&pack)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if items
            .iter()
            .filter(|item| item.display_label.chars().count() > 2)
            .any(|item| serialized.contains(&item.display_label))
        {
            return Err(CoreError::ContextBoundary(
                "source-free Corpus pack leaked a source title".into(),
            ));
        }
        let evidence_fp = sha256_fingerprint(
            serde_json::to_vec(&evidence)
                .map_err(|error| CoreError::Serialization(error.to_string()))?,
        );
        let transaction = self
            .connection
            .transaction_with_behavior(TransactionBehavior::Immediate)
            .map_err(storage)?;
        transaction.execute("INSERT INTO corpus_pack_candidates(pack_fingerprint,study_id,payload_json,evidence_bundle_fingerprint,leakage_gate,created_at) \
            VALUES(?1,?2,?3,?4,'pass',?5)",params![pack.fingerprint,study_id,serialized,evidence_fp,created_at]).map_err(storage)?;
        transaction.execute("UPDATE corpus_selection_proposals SET status='complete',updated_at=?2 WHERE study_id=?1",params![study_id,created_at]).map_err(storage)?;
        transaction.commit().map_err(storage)
    }
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
fn parse_stage(value: &str) -> CoreResult<AnalyzeStage> {
    match value {
        "boundary_index" => Ok(AnalyzeStage::BoundaryIndex),
        "golden_three" => Ok(AnalyzeStage::GoldenThree),
        "chapter_extraction" => Ok(AnalyzeStage::ChapterExtraction),
        "aggregate_mechanisms" => Ok(AnalyzeStage::AggregateMechanisms),
        "story_entities" => Ok(AnalyzeStage::StoryEntities),
        "report" => Ok(AnalyzeStage::Report),
        "style_profile" => Ok(AnalyzeStage::StyleProfile),
        _ => Err(CoreError::Storage("unknown Corpus stage".into())),
    }
}
fn next_stage(stage: AnalyzeStage) -> Option<AnalyzeStage> {
    match stage {
        AnalyzeStage::BoundaryIndex => Some(AnalyzeStage::GoldenThree),
        AnalyzeStage::GoldenThree => Some(AnalyzeStage::ChapterExtraction),
        AnalyzeStage::ChapterExtraction => Some(AnalyzeStage::AggregateMechanisms),
        AnalyzeStage::AggregateMechanisms => Some(AnalyzeStage::StoryEntities),
        AnalyzeStage::StoryEntities => Some(AnalyzeStage::Report),
        AnalyzeStage::Report => Some(AnalyzeStage::StyleProfile),
        AnalyzeStage::StyleProfile => None,
    }
}
fn checkpoint_for(study_id: &str, stage: &str, binding: &str) -> CoreResult<String> {
    serde_json::to_vec(&json!({"study_id":study_id,"stage":stage,"binding":binding}))
        .map(sha256_fingerprint)
        .map_err(|error| CoreError::Serialization(error.to_string()))
}
fn corpus_system(stage: AnalyzeStage) -> &'static str {
    match stage{
    AnalyzeStage::GoldenThree=>"You are the Golden Three analyst for Chinese web fiction. Diagnose hook, character promise, reader reward, causal scene turns and chapter pull. Return strict JSON only; never copy sentences or expose titles.",
    AnalyzeStage::ChapterExtraction=>"You are a Chinese web-novel mechanism analyst. Extract reusable dramatic mechanisms, emotion chains, pacing and reader needs from the supplied chapter chunk. Return strict JSON only; never imitate or quote source prose.",
    AnalyzeStage::AggregateMechanisms=>"Aggregate semantic findings into deduplicated, replaceable web-novel mechanisms. Preserve disagreements and uncertainty. Return strict JSON only.",
    AnalyzeStage::StoryEntities=>"Analyze character functions, relationship pressure and long-form escalation from prior semantic artifacts. Return strict JSON only without source identities.",
    AnalyzeStage::Report=>"Synthesize a story-skill analyze report across Golden Three, structure, character engine, payoff cadence, reversals, emotional progression and prose execution. Return strict JSON only.",
    AnalyzeStage::StyleProfile=>"Build a source-free Writer Corpus pack for original Chinese web fiction. Keep only reader needs, dramatic functions, replaceable slots, forbidden copying boundaries, rhythm references and style guidance. Return strict JSON only.",
    AnalyzeStage::BoundaryIndex=>"Boundary indexing is deterministic and must not call a model."}
}
fn corpus_contract(stage: AnalyzeStage) -> Value {
    json!({"stage":stage_name(stage),"return":"JSON only",
    "shape":{"genre":"string","mechanisms":[{"mechanism_id":"string","reader_need":"string",
        "emotion_chain":["at least three states"],"dramatic_function":"string","replaceable_slots":["at least three slots"],
        "forbidden_copy_elements":["source-specific elements never to copy"],"rhythm_refs":["abstract rhythm label"]}],
        "rhythm_summary":"string","style_guidance":["original prose guidance"],"evidence_summary":"reasoned summary without quotations",
        "analysis":corpus_stage_analysis_contract(stage)},
    "prohibitions":["no source title","no character or place names","no verbatim sentence","no imitation request"]})
}

fn corpus_stage_analysis_contract(stage: AnalyzeStage) -> Value {
    match stage {
        AnalyzeStage::GoldenThree => {
            json!({"kind":"golden_three","chapter_functions":["one entry per supplied opening chapter"],"opening_promise":"string"})
        }
        AnalyzeStage::ChapterExtraction => {
            json!({"kind":"chapter_extraction","chapter_summaries":["source-free summary"],"causal_beats":["trigger-choice-consequence"],"emotional_progression":["state transition"],
                "coverage_state":"expanding|saturated","next_unit_keys":["zero to eight exact keys from remaining_unit_keys; required when expanding"],
                "stop_reason":"required non-empty string only when saturated"})
        }
        AnalyzeStage::AggregateMechanisms => {
            json!({"kind":"aggregate_mechanisms","convergences":["cross-work finding"],"disagreements":["conflicting evidence"],"coverage_gaps":["evidence still needed"]})
        }
        AnalyzeStage::StoryEntities => {
            json!({"kind":"story_entities","character_functions":["function without names"],"relationship_pressures":["relationship evolution"],"escalation_paths":["long-form escalation"]})
        }
        AnalyzeStage::Report => {
            json!({"kind":"report","structure_findings":["finding"],"character_engine":["finding"],"payoff_and_reversal":["finding"]})
        }
        AnalyzeStage::StyleProfile => {
            json!({"kind":"style_profile","voice_principles":["positive original prose rule"],"rhythm_protocol":["beat-driven rhythm"],"anti_copy_boundaries":["specific non-copy boundary"]})
        }
        AnalyzeStage::BoundaryIndex => json!({"kind":"deterministic_boundary_index"}),
    }
}

fn coverage_stratified_selection(
    mut pool: Vec<(CorpusWorkProjection, u64, u64)>,
    take: usize,
) -> Vec<CorpusWorkProjection> {
    if pool.len() <= take {
        return pool.into_iter().map(|item| item.0).collect();
    }
    let max_bytes = pool.iter().map(|item| item.1).max().unwrap_or(1).max(1);
    let max_chapters = pool.iter().map(|item| item.2).max().unwrap_or(1).max(1);
    pool.sort_by(|left, right| {
        right
            .2
            .cmp(&left.2)
            .then_with(|| right.1.cmp(&left.1))
            .then_with(|| left.0.work_id.cmp(&right.0.work_id))
    });
    let mut selected = vec![pool.remove(0)];
    while selected.len() < take && !pool.is_empty() {
        let (index, _) = pool
            .iter()
            .enumerate()
            .map(|(index, candidate)| {
                let nearest = selected
                    .iter()
                    .map(|chosen| {
                        let byte_distance =
                            candidate.1.abs_diff(chosen.1) as u128 * 1_000 / max_bytes as u128;
                        let chapter_distance =
                            candidate.2.abs_diff(chosen.2) as u128 * 1_000 / max_chapters as u128;
                        byte_distance + chapter_distance
                    })
                    .min()
                    .unwrap_or(0);
                (index, nearest)
            })
            .max_by(|(left_index, left_score), (right_index, right_score)| {
                left_score.cmp(right_score).then_with(|| {
                    pool[*right_index]
                        .0
                        .work_id
                        .cmp(&pool[*left_index].0.work_id)
                })
            })
            .unwrap();
        selected.push(pool.remove(index));
    }
    selected.into_iter().map(|item| item.0).collect()
}

fn scan_directory(
    root: &Path,
    current: &Path,
    depth: usize,
    works: &mut Vec<ScannedWork>,
) -> CoreResult<()> {
    if depth > MAX_SCAN_DEPTH {
        return Err(CoreError::InvalidProject(
            "Corpus directory nesting exceeds the supported depth".into(),
        ));
    }
    let guard = guard_directory(current, false).map_err(native_error)?;
    let mut entries = std::fs::read_dir(current)
        .map_err(|error| CoreError::Storage(error.to_string()))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| CoreError::Storage(error.to_string()))?;
    entries.sort_by_key(|entry| entry.file_name());
    for entry in entries {
        let file_type = entry
            .file_type()
            .map_err(|error| CoreError::Storage(error.to_string()))?;
        if file_type.is_symlink() {
            return Err(CoreError::InvalidProject(
                "Corpus scan rejects links and reparse points".into(),
            ));
        }
        let path = entry.path();
        if file_type.is_dir() {
            scan_directory(root, &path, depth + 1, works)?;
            continue;
        }
        if !file_type.is_file()
            || path
                .extension()
                .and_then(|value| value.to_str())
                .map(|value| !value.eq_ignore_ascii_case("txt"))
                .unwrap_or(true)
        {
            continue;
        }
        if works.len() >= MAX_SCAN_WORKS {
            return Err(CoreError::InvalidProject(
                "Corpus collection exceeds 500 eligible works; split it into explicit collections"
                    .into(),
            ));
        }
        let (raw, identity) = read_guarded_file(&path, MAX_WORK_BYTES).map_err(native_error)?;
        if identity.link_count != 1 {
            return Err(CoreError::InvalidProject(
                "Corpus source must have exactly one hard link".into(),
            ));
        }
        let bytes = raw.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&raw);
        let text = std::str::from_utf8(bytes).map_err(|_| {
            CoreError::InvalidProject(format!("Corpus TXT is not UTF-8: {}", path.display()))
        })?;
        if text.trim().is_empty() {
            continue;
        }
        let source_fingerprint = sha256_fingerprint(bytes);
        let boundaries = chapter_boundaries(text, &source_fingerprint)?;
        let relative = path
            .strip_prefix(root)
            .map_err(|_| CoreError::Storage("Corpus entry escaped its collection root".into()))?;
        let relative_ref = relative
            .components()
            .map(|part| part.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");
        let title = path
            .file_stem()
            .and_then(|value| value.to_str())
            .unwrap_or("untitled")
            .trim()
            .to_string();
        works.push(ScannedWork {
            relative_ref,
            title,
            source_fingerprint,
            bytes: bytes.len() as u64,
            boundaries,
        });
    }
    guard.revalidate().map_err(native_error)?;
    Ok(())
}

fn chapter_boundaries(text: &str, source_fingerprint: &str) -> CoreResult<Vec<ChapterBoundary>> {
    let mut starts = Vec::<(usize, String)>::new();
    let mut offset = 0usize;
    for line in text.split_inclusive('\n') {
        let label = line.trim().trim_start_matches('\u{feff}');
        if is_chapter_heading(label) {
            starts.push((offset, label.to_string()));
        }
        offset += line.len();
    }
    if starts.is_empty() {
        starts.push((0, "正文".into()));
    }
    let mut boundaries = Vec::with_capacity(starts.len());
    for (index, (start, title)) in starts.iter().enumerate() {
        let end = starts
            .get(index + 1)
            .map(|value| value.0)
            .unwrap_or(text.len());
        if *start >= end {
            continue;
        }
        boundaries.push(ChapterBoundary {
            chapter: (boundaries.len() + 1) as u32,
            title: title.clone(),
            start_byte: *start as u64,
            end_byte: end as u64,
            source_fingerprint: source_fingerprint.into(),
        });
    }
    if boundaries.is_empty() {
        return Err(CoreError::InvalidProject(
            "Corpus TXT has no analysable content".into(),
        ));
    }
    Ok(boundaries)
}

fn is_chapter_heading(value: &str) -> bool {
    let compact = value.trim();
    if compact.len() > 160 {
        return false;
    }
    let lower = compact.to_ascii_lowercase();
    lower.starts_with("chapter ")
        || (compact.starts_with('第')
            && compact
                .chars()
                .skip(1)
                .take(12)
                .any(|character| matches!(character, '章' | '回' | '卷' | '节')))
}

fn validate_schema(connection: &Connection) -> CoreResult<()> {
    let (scope, release): (String, String) = connection
        .query_row(
            "SELECT scope,release FROM corpus_schema_identity",
            [],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .map_err(storage)?;
    if scope != "corpus" || release != "1.0" {
        return Err(CoreError::Storage(
            "Unsupported Corpus database schema".into(),
        ));
    }
    connection
        .execute_batch("PRAGMA foreign_key_check;")
        .map_err(storage)?;
    Ok(())
}

fn identity_value(identity: QfNativeIdentity) -> Value {
    json!({"volume_id":identity.volume_id,"file_id_low":identity.file_id_low,
    "file_id_high":identity.file_id_high,"link_count":identity.link_count,"byte_size":identity.byte_size})
}
fn native_error(error: quillframe_native::NativeError) -> CoreError {
    CoreError::Storage(error.to_string())
}
fn storage(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ModelUsage;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_root(label: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "qf-corpus-{label}-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
    }
    fn output(stage: AnalyzeStage) -> String {
        let analysis = match stage {
            AnalyzeStage::GoldenThree => CorpusStageAnalysis::GoldenThree {
                chapter_functions: vec!["起势".into(), "加压".into(), "兑现".into()],
                opening_promise: "主角以选择和代价改变局面".into(),
            },
            AnalyzeStage::ChapterExtraction => CorpusStageAnalysis::ChapterExtraction {
                chapter_summaries: vec!["角色受压后主动选择并承担后果".into()],
                causal_beats: vec!["压力—选择—行动—反馈".into()],
                emotional_progression: vec!["受压—决断—释放".into()],
                coverage_state: "saturated".into(),
                next_unit_keys: vec![],
                stop_reason: Some("evidence coverage converged".into()),
            },
            AnalyzeStage::AggregateMechanisms => CorpusStageAnalysis::AggregateMechanisms {
                convergences: vec!["公开反馈兑现角色选择".into()],
                disagreements: vec![],
                coverage_gaps: vec![],
            },
            AnalyzeStage::StoryEntities => CorpusStageAnalysis::StoryEntities {
                character_functions: vec!["承压决策者".into()],
                relationship_pressures: vec!["怀疑经共同代价转为信任".into()],
                escalation_paths: vec!["局部选择暴露更大威胁".into()],
            },
            AnalyzeStage::Report => CorpusStageAnalysis::Report {
                structure_findings: vec!["章内因果闭合，章尾开启新债".into()],
                character_engine: vec!["选择和代价驱动人物变化".into()],
                payoff_and_reversal: vec!["公开反馈完成兑现".into()],
            },
            AnalyzeStage::StyleProfile => CorpusStageAnalysis::StyleProfile {
                voice_principles: vec!["对白绑定动作与空间".into()],
                rhythm_protocol: vec!["节奏由戏剧拍点驱动".into()],
                anti_copy_boundaries: vec!["不得保留专名、原句或情节拼装".into()],
            },
            AnalyzeStage::BoundaryIndex => unreachable!(),
        };
        serde_json::to_string(&CorpusStageOutput {
            genre: "玄幻".into(),
            mechanisms: vec![CorpusMechanismDraft {
                mechanism_id: "pressure-release".into(),
                reader_need: "见证主角以行动逆转判断".into(),
                emotion_chain: vec!["受压".into(), "选择".into(), "兑现".into()],
                dramatic_function: "让公开误判经过行动与代价得到反转".into(),
                replaceable_slots: vec!["压力来源".into(), "主角选择".into(), "见证反馈".into()],
                forbidden_copy_elements: vec!["专名".into(), "原句".into()],
                rhythm_refs: vec!["三拍释放".into()],
            }],
            rhythm_summary: "场景内蓄压，章末完成一次兑现并打开新问题".into(),
            style_guidance: vec!["对白必须绑定动作、空间与侧面反应".into()],
            evidence_summary: "抽象机制由多个章节证据支持，不保留引文".into(),
            analysis,
        })
        .unwrap()
    }

    #[test]
    fn corpus_pipeline_pauses_after_golden_three_and_builds_source_free_pack() {
        let root = temp_root("pipeline");
        let books = root.join("books");
        std::fs::create_dir_all(&books).unwrap();
        std::fs::write(books.join("book1.txt"),"第一章 起势\n这是绝不能进入数据库的原文甲。\n第二章 加压\n人物作出选择。\n第三章 兑现\n行动产生后果。\n第四章 新问\n新的压力到来。\n").unwrap();
        std::fs::write(books.join("book2.txt"),"第一章 相遇\n这是绝不能进入数据库的原文乙。\n第二章 对抗\n关系发生变化。\n第三章 代价\n选择必须付钱。\n").unwrap();
        let db_root = root.join("state");
        let mut db = CorpusDatabase::open(&db_root, "2026-08-31T00:00:00Z").unwrap();
        let scan = db.scan_collection(&books, "2026-08-31T00:00:00Z").unwrap();
        assert_eq!(scan["eligible_work_count"], 2);
        let collection_id = scan["collection_id"].as_str().unwrap();
        let proposal = db
            .propose_selection(collection_id, "general", Some(2), "2026-08-31T00:00:01Z")
            .unwrap();
        let ids = proposal
            .items
            .iter()
            .map(|item| item.work_id.clone())
            .collect::<Vec<_>>();
        db.confirm_selection(
            &proposal.study_id,
            &ids,
            &proposal.proposal_fingerprint,
            "general",
            "2026-08-31T00:00:02Z",
        )
        .unwrap();
        for ordinal in 0..2 {
            let call = db
                .dispatch_next_stage(&proposal.study_id, "mock-model", "2026-08-31T00:00:03Z")
                .unwrap()
                .unwrap();
            let result = ModelResult::record(
                call.request.request_id,
                "mock",
                "mock-model",
                output(call.stage),
                Some(format!("r{ordinal}")),
                ModelUsage {
                    input_tokens: Some(1),
                    output_tokens: Some(1),
                    total_tokens: Some(2),
                    cost_micros: None,
                },
            )
            .unwrap();
            db.confirm_stage(
                &proposal.study_id,
                &call.call_id,
                &result,
                "2026-08-31T00:00:04Z",
            )
            .unwrap();
        }
        assert!(db
            .dispatch_next_stage(&proposal.study_id, "mock-model", "2026-08-31T00:00:05Z")
            .is_err());
        let checkpoint: String = db
            .connection
            .query_row(
                "SELECT checkpoint_fingerprint FROM corpus_studies WHERE study_id=?1",
                [&proposal.study_id],
                |row| row.get(0),
            )
            .unwrap();
        db.continue_after_golden_three(
            &proposal.study_id,
            &checkpoint,
            "author clicked continue",
            "2026-08-31T00:00:06Z",
        )
        .unwrap();
        let mut safety = 0;
        while db.source_free_pack(&proposal.study_id).unwrap().is_none() {
            safety += 1;
            assert!(safety < 30);
            if let Some(call) = db
                .dispatch_next_stage(&proposal.study_id, "mock-model", "2026-08-31T00:00:07Z")
                .unwrap()
            {
                let result = ModelResult::record(
                    call.request.request_id,
                    "mock",
                    "mock-model",
                    output(call.stage),
                    None,
                    ModelUsage {
                        input_tokens: Some(1),
                        output_tokens: Some(1),
                        total_tokens: Some(2),
                        cost_micros: None,
                    },
                )
                .unwrap();
                db.confirm_stage(
                    &proposal.study_id,
                    &call.call_id,
                    &result,
                    "2026-08-31T00:00:08Z",
                )
                .unwrap();
            }
        }
        let pack = db.source_free_pack(&proposal.study_id).unwrap().unwrap();
        pack.validate().unwrap();
        assert!(pack.writer_projection().unwrap().evidence_absent);
        drop(db);
        let database_bytes = std::fs::read(db_root.join("corpus.sqlite")).unwrap();
        assert!(!String::from_utf8_lossy(&database_bytes).contains("绝不能进入数据库的原文"));
        std::fs::remove_dir_all(root).unwrap();
    }
}
