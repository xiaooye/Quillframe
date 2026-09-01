use std::path::{Path, PathBuf};
use std::time::Duration;

use quillframe_native::{guard_directory, guard_file, FileMode, QfNativeGuard, QfNativeLock};
use rusqlite::{params, Connection, OpenFlags, OptionalExtension};
use serde::{Deserialize, Serialize};

use crate::{
    apply_fresh_global_schema, validate_current_global_schema, AuthStyle, CoreError, CoreResult,
    ModelCatalog, ProjectManifest, ProtocolFamily, ServiceEndpoint,
};

pub struct GlobalDatabase {
    connection: Connection,
    _root_guard: QfNativeGuard,
    _database_guard: QfNativeGuard,
    _lock: QfNativeLock,
    path: PathBuf,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RegisteredProject {
    pub project_id: String,
    pub title: String,
    pub language: String,
    pub project_dir: String,
    pub registered_at: String,
    pub last_opened_at: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelServiceRecord {
    pub endpoint: ServiceEndpoint,
    pub enabled: bool,
    pub discovery_state: String,
    pub catalog: Option<ModelCatalog>,
    pub last_checked_at: Option<String>,
    pub version: u64,
    pub created_at: String,
    pub updated_at: String,
}

impl GlobalDatabase {
    pub fn create(root: &Path, created_at: &str) -> CoreResult<Self> {
        timestamp(created_at)?;
        let root_guard = guard_directory(root, true).map_err(native_error)?;
        let lock = QfNativeLock::try_acquire(&root.join(".global.lock")).map_err(native_error)?;
        let path = root.join("global.sqlite");
        let database_guard = guard_file(&path, FileMode::CreateNew, true).map_err(native_error)?;
        let mut connection = open(&path)?;
        connection
            .pragma_update(None, "journal_mode", "WAL")
            .map_err(storage_error)?;
        connection
            .pragma_update(None, "synchronous", "FULL")
            .map_err(storage_error)?;
        apply_fresh_global_schema(&mut connection, created_at)?;
        Ok(Self {
            connection,
            _root_guard: root_guard,
            _database_guard: database_guard,
            _lock: lock,
            path,
        })
    }

    pub fn open(root: &Path) -> CoreResult<Self> {
        let root_guard = guard_directory(root, false).map_err(native_error)?;
        let lock = QfNativeLock::try_acquire(&root.join(".global.lock")).map_err(native_error)?;
        let path = root.join("global.sqlite");
        let database_guard =
            guard_file(&path, FileMode::OpenReadWrite, true).map_err(native_error)?;
        let connection = open(&path)?;
        validate_current_global_schema(&connection)?;
        root_guard.revalidate().map_err(native_error)?;
        database_guard.revalidate().map_err(native_error)?;
        Ok(Self {
            connection,
            _root_guard: root_guard,
            _database_guard: database_guard,
            _lock: lock,
            path,
        })
    }

    pub fn register_project(
        &mut self,
        manifest: &ProjectManifest,
        project_dir: &Path,
        registered_at: &str,
    ) -> CoreResult<()> {
        manifest.validate()?;
        timestamp(registered_at)?;
        if !project_dir.is_absolute() {
            return Err(CoreError::InvalidProject(
                "registered project directory must be absolute".into(),
            ));
        }
        self.connection
            .execute(
                "INSERT INTO project_registry( \
                 project_id,title,language,project_schema_version,project_dir,registered_at,last_opened_at \
                 ) VALUES(?1,?2,?3,1,?4,?5,?5)",
                params![
                    manifest.id,
                    manifest.title,
                    manifest.language,
                    project_dir.to_string_lossy(),
                    registered_at
                ],
            )
            .map_err(storage_error)?;
        Ok(())
    }

    pub fn projects(&self) -> CoreResult<Vec<RegisteredProject>> {
        let mut statement = self
            .connection
            .prepare(
                "SELECT project_id,title,language,project_dir,registered_at,last_opened_at \
                 FROM project_registry ORDER BY last_opened_at DESC,project_id",
            )
            .map_err(storage_error)?;
        let rows = statement
            .query_map([], |row| {
                Ok(RegisteredProject {
                    project_id: row.get(0)?,
                    title: row.get(1)?,
                    language: row.get(2)?,
                    project_dir: row.get(3)?,
                    registered_at: row.get(4)?,
                    last_opened_at: row.get(5)?,
                })
            })
            .map_err(storage_error)?;
        rows.collect::<Result<Vec<_>, _>>().map_err(storage_error)
    }

    pub fn project(&self, project_id: &str) -> CoreResult<Option<RegisteredProject>> {
        use rusqlite::OptionalExtension;
        self.connection
            .query_row(
                "SELECT project_id,title,language,project_dir,registered_at,last_opened_at \
                 FROM project_registry WHERE project_id=?1",
                [project_id],
                |row| {
                    Ok(RegisteredProject {
                        project_id: row.get(0)?,
                        title: row.get(1)?,
                        language: row.get(2)?,
                        project_dir: row.get(3)?,
                        registered_at: row.get(4)?,
                        last_opened_at: row.get(5)?,
                    })
                },
            )
            .optional()
            .map_err(storage_error)
    }

    pub fn save_model_service(
        &mut self,
        endpoint: &ServiceEndpoint,
        expected_version: u64,
        updated_at: &str,
    ) -> CoreResult<ModelServiceRecord> {
        endpoint.validate_url()?;
        timestamp(updated_at)?;
        let transaction = self.connection.transaction().map_err(storage_error)?;
        let current = transaction
            .query_row(
                "SELECT version,created_at FROM model_services WHERE service_id=?1",
                [&endpoint.service_id],
                |row| Ok((row.get::<_, u64>(0)?, row.get::<_, String>(1)?)),
            )
            .optional()
            .map_err(storage_error)?;
        let version = match current.as_ref() {
            None if expected_version == 0 => 1,
            Some((version, _)) if *version == expected_version => version + 1,
            _ => {
                return Err(CoreError::AuthorityConflict(
                    "model service version changed".into(),
                ))
            }
        };
        let created_at = current
            .map(|(_, created)| created)
            .unwrap_or_else(|| updated_at.into());
        transaction.execute(
            "INSERT INTO model_services(service_id,endpoint,credential_ref,enabled,auth_style,discovery_state,snapshot_json,created_at,updated_at,protocol_family,allow_loopback_http,version) \
             VALUES(?1,?2,?3,1,?4,'unknown','{}',?5,?6,?7,?8,?9) \
             ON CONFLICT(service_id) DO UPDATE SET endpoint=excluded.endpoint,credential_ref=excluded.credential_ref,auth_style=excluded.auth_style, \
             discovery_state='unknown',snapshot_fingerprint=NULL,snapshot_json='{}',last_checked_at=NULL,updated_at=excluded.updated_at, \
             protocol_family=excluded.protocol_family,allow_loopback_http=excluded.allow_loopback_http,version=excluded.version",
            params![endpoint.service_id,endpoint.endpoint,endpoint.credential_ref,auth_style(endpoint.auth_style),created_at,updated_at,
                protocol_family(endpoint.protocol_family),endpoint.allow_loopback_http,version],
        ).map_err(storage_error)?;
        transaction.commit().map_err(storage_error)?;
        Ok(ModelServiceRecord {
            endpoint: endpoint.clone(),
            enabled: true,
            discovery_state: "unknown".into(),
            catalog: None,
            last_checked_at: None,
            version,
            created_at,
            updated_at: updated_at.into(),
        })
    }

    pub fn model_services(&self) -> CoreResult<Vec<ModelServiceRecord>> {
        let mut statement = self.connection.prepare(
            "SELECT service_id,endpoint,credential_ref,auth_style,protocol_family,allow_loopback_http,enabled,version,created_at,updated_at,discovery_state,snapshot_json,last_checked_at \
             FROM model_services ORDER BY created_at,service_id"
        ).map_err(storage_error)?;
        let rows = statement
            .query_map([], model_service_row)
            .map_err(storage_error)?
            .collect::<Result<Vec<_>, _>>()
            .map_err(storage_error)?;
        Ok(rows)
    }

    pub fn model_service(&self, service_id: &str) -> CoreResult<Option<ModelServiceRecord>> {
        self.connection.query_row(
            "SELECT service_id,endpoint,credential_ref,auth_style,protocol_family,allow_loopback_http,enabled,version,created_at,updated_at,discovery_state,snapshot_json,last_checked_at \
             FROM model_services WHERE service_id=?1",[service_id],model_service_row,
        ).optional().map_err(storage_error)
    }

    pub fn model_service_by_endpoint(
        &self,
        endpoint: &str,
    ) -> CoreResult<Option<ModelServiceRecord>> {
        self.connection.query_row(
            "SELECT service_id,endpoint,credential_ref,auth_style,protocol_family,allow_loopback_http,enabled,version,created_at,updated_at,discovery_state,snapshot_json,last_checked_at \
             FROM model_services WHERE endpoint=?1",[endpoint],model_service_row,
        ).optional().map_err(storage_error)
    }

    pub fn delete_model_service(&mut self, service_id: &str) -> CoreResult<bool> {
        self.connection
            .execute(
                "DELETE FROM model_services WHERE service_id=?1",
                [service_id],
            )
            .map(|changed| changed == 1)
            .map_err(storage_error)
    }

    pub fn record_model_catalog(
        &mut self,
        service_id: &str,
        catalog: &ModelCatalog,
        checked_at: &str,
    ) -> CoreResult<()> {
        timestamp(checked_at)?;
        catalog.validate()?;
        if catalog.service_id != service_id {
            return Err(CoreError::AuthorityConflict(
                "model catalog service binding changed".into(),
            ));
        }
        let snapshot = serde_json::to_string(catalog)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let changed = self
            .connection
            .execute(
                "UPDATE model_services SET discovery_state='connected',snapshot_json=?2, \
                 snapshot_fingerprint=?3,last_checked_at=?4 WHERE service_id=?1 AND enabled=1",
                params![service_id, snapshot, catalog.fingerprint, checked_at],
            )
            .map_err(storage_error)?;
        if changed != 1 {
            return Err(CoreError::AuthorityConflict(
                "model service is unavailable for discovery".into(),
            ));
        }
        Ok(())
    }

    pub fn connection(&self) -> &Connection {
        &self.connection
    }

    pub fn path(&self) -> &Path {
        &self.path
    }
}

fn model_service_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<ModelServiceRecord> {
    let auth: String = row.get(3)?;
    let protocol: String = row.get(4)?;
    let snapshot: String = row.get(11)?;
    let catalog = if snapshot == "{}" {
        None
    } else {
        serde_json::from_str::<ModelCatalog>(&snapshot).ok()
    };
    Ok(ModelServiceRecord {
        endpoint: ServiceEndpoint {
            service_id: row.get(0)?,
            endpoint: row.get(1)?,
            credential_ref: row.get(2)?,
            auth_style: match auth.as_str() {
                "bearer" => AuthStyle::Bearer,
                "x_api_key" => AuthStyle::XApiKey,
                _ => AuthStyle::None,
            },
            protocol_family: match protocol.as_str() {
                "openai_responses" => ProtocolFamily::OpenaiResponses,
                "anthropic_messages" => ProtocolFamily::AnthropicMessages,
                _ => ProtocolFamily::OpenaiChatCompletions,
            },
            allow_loopback_http: row.get(5)?,
        },
        enabled: row.get(6)?,
        discovery_state: row.get(10)?,
        catalog,
        last_checked_at: row.get(12)?,
        version: row.get(7)?,
        created_at: row.get(8)?,
        updated_at: row.get(9)?,
    })
}

fn auth_style(value: AuthStyle) -> &'static str {
    match value {
        AuthStyle::Bearer => "bearer",
        AuthStyle::XApiKey => "x_api_key",
        AuthStyle::None => "none",
    }
}
fn protocol_family(value: ProtocolFamily) -> &'static str {
    match value {
        ProtocolFamily::OpenaiChatCompletions => "openai_chat_completions",
        ProtocolFamily::OpenaiResponses => "openai_responses",
        ProtocolFamily::AnthropicMessages => "anthropic_messages",
    }
}

fn open(path: &Path) -> CoreResult<Connection> {
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

fn timestamp(value: &str) -> CoreResult<()> {
    if value.trim().is_empty() || value != value.trim() {
        return Err(CoreError::Storage("timestamp is required".into()));
    }
    Ok(())
}

fn storage_error(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

fn native_error(error: quillframe_native::NativeError) -> CoreError {
    CoreError::Storage(error.to_string())
}

#[cfg(all(test, any(windows, target_os = "linux")))]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    fn root() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("qf-global-{}-{nonce}", std::process::id()))
    }

    #[test]
    fn global_registry_is_strict_and_survives_restart() {
        let root = root();
        let project_root = root.join("projects").join("BOOK");
        guard_directory(&project_root, true).unwrap();
        let manifest = ProjectManifest::new("BOOK", "长篇", "zh-CN").unwrap();
        let mut global =
            GlobalDatabase::create(&root.join("state"), "2026-08-31T00:00:00Z").unwrap();
        global
            .register_project(&manifest, &project_root, "2026-08-31T00:00:01Z")
            .unwrap();
        let service = ServiceEndpoint {
            service_id: "SERVICE1".into(),
            endpoint: "https://api.example.com/".into(),
            credential_ref: None,
            auth_style: AuthStyle::None,
            protocol_family: ProtocolFamily::OpenaiChatCompletions,
            allow_loopback_http: false,
        };
        assert_eq!(
            global
                .save_model_service(&service, 0, "2026-08-31T00:00:02Z")
                .unwrap()
                .version,
            1
        );
        assert_eq!(global.projects().unwrap().len(), 1);
        drop(global);
        let reopened = GlobalDatabase::open(&root.join("state")).unwrap();
        assert_eq!(reopened.projects().unwrap()[0].project_id, "BOOK");
        assert_eq!(reopened.model_services().unwrap()[0].endpoint, service);
        drop(reopened);
        std::fs::remove_dir_all(root).unwrap();
    }
}
