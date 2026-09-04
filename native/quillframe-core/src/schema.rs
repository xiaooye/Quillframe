use std::collections::BTreeMap;

use rusqlite::{params, Connection, TransactionBehavior};

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

const SCHEMA_LEDGER_DDL: &str = r#"CREATE TABLE schema_fragments (
    scope TEXT NOT NULL,
    version INTEGER NOT NULL,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    PRIMARY KEY(scope, version)
)"#;

#[derive(Clone, Copy)]
struct SchemaFragment {
    version: u32,
    name: &'static str,
    sql: &'static str,
}

macro_rules! fragment {
    ($version:literal, $name:literal) => {
        SchemaFragment {
            version: $version,
            name: $name,
            sql: include_str!(concat!("../../../persistence/schema/project/", $name)),
        }
    };
}

const PROJECT_FRAGMENTS: [SchemaFragment; 25] = [
    fragment!(1, "001_initial.sql"),
    fragment!(2, "002_semantic_context_runtime.sql"),
    fragment!(3, "003_native_independent_review.sql"),
    fragment!(4, "004_independent_review_processing_lease.sql"),
    fragment!(5, "005_publication_recovery.sql"),
    fragment!(6, "006_production_stage_journal.sql"),
    fragment!(7, "007_novel_plans_dependencies.sql"),
    fragment!(8, "008_publication_collection.sql"),
    fragment!(9, "009_reader_expectation_memory.sql"),
    fragment!(10, "010_narrative_state_sources.sql"),
    fragment!(11, "011_production_wake_index.sql"),
    fragment!(12, "012_production_billing_receipts.sql"),
    fragment!(13, "013_production_build_migrations.sql"),
    fragment!(14, "014_story_skill_production.sql"),
    fragment!(15, "015_revision_settlement.sql"),
    fragment!(16, "016_production_release.sql"),
    fragment!(17, "017_plan_editor_views.sql"),
    fragment!(18, "018_publication_native_contract.sql"),
    fragment!(19, "019_corpus_pack_activation.sql"),
    fragment!(20, "020_chapter_creation.sql"),
    fragment!(21, "021_hierarchical_plan_bindings.sql"),
    fragment!(22, "022_story_commit_log.sql"),
    fragment!(23, "023_learning_activation.sql"),
    fragment!(24, "024_ai_native_longform_planning.sql"),
    fragment!(25, "025_book_setup.sql"),
];

pub fn apply_fresh_project_schema(connection: &mut Connection, applied_at: &str) -> CoreResult<()> {
    if applied_at.trim().is_empty() {
        return Err(CoreError::Storage(
            "schema application timestamp is required".into(),
        ));
    }
    if !schema_objects(connection)?.is_empty() {
        return Err(CoreError::Storage(
            "fresh schema requires an empty database".into(),
        ));
    }
    let transaction = connection
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(storage_error)?;
    transaction
        .execute_batch(SCHEMA_LEDGER_DDL)
        .map_err(storage_error)?;
    for fragment in PROJECT_FRAGMENTS {
        transaction
            .execute_batch(fragment.sql)
            .map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO schema_fragments(scope,version,name,checksum,applied_at) \
                 VALUES('project',?1,?2,?3,?4)",
                params![
                    fragment.version,
                    fragment.name,
                    fragment_checksum(fragment),
                    applied_at
                ],
            )
            .map_err(storage_error)?;
    }
    transaction.commit().map_err(storage_error)?;
    validate_current_project_schema(connection)
}

pub fn validate_current_project_schema(connection: &Connection) -> CoreResult<()> {
    validate_identity(connection)?;
    validate_ledger(connection)?;
    validate_planning_contract(connection)?;

    let expected = Connection::open_in_memory().map_err(storage_error)?;
    expected
        .execute_batch(SCHEMA_LEDGER_DDL)
        .map_err(storage_error)?;
    for fragment in PROJECT_FRAGMENTS {
        expected
            .execute_batch(fragment.sql)
            .map_err(storage_error)?;
    }
    let actual_objects = schema_objects(connection)?;
    let base_objects = schema_objects(&expected)?;
    if actual_objects != base_objects {
        expected
            .execute_batch(
                "CREATE VIRTUAL TABLE search_trigram USING fts5( \
                 entity_type UNINDEXED, entity_id UNINDEXED, title, body, tokenize='trigram')",
            )
            .map_err(storage_error)?;
        if actual_objects != schema_objects(&expected)? {
            return Err(CoreError::Storage(
                "SQLite objects differ from the exact Project 1.0 schema".into(),
            ));
        }
    }

    let quick_check: String = connection
        .query_row("PRAGMA quick_check", [], |row| row.get(0))
        .map_err(storage_error)?;
    if quick_check != "ok" {
        return Err(CoreError::Storage(format!(
            "SQLite quick_check failed: {quick_check}"
        )));
    }
    let mut foreign_keys = connection
        .prepare("PRAGMA foreign_key_check")
        .map_err(storage_error)?;
    if foreign_keys
        .query([])
        .map_err(storage_error)?
        .next()
        .map_err(storage_error)?
        .is_some()
    {
        return Err(CoreError::Storage(
            "SQLite foreign_key_check reported a violation".into(),
        ));
    }
    Ok(())
}

fn validate_identity(connection: &Connection) -> CoreResult<()> {
    let mut statement = connection
        .prepare("SELECT scope,release FROM quillframe_schema_identity")
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    if rows != [("project".into(), "1.0".into())] {
        return Err(CoreError::Storage(
            "SQLite schema identity must be exactly project:1.0".into(),
        ));
    }
    Ok(())
}

fn validate_ledger(connection: &Connection) -> CoreResult<()> {
    let mut statement = connection
        .prepare(
            "SELECT scope,version,name,checksum FROM schema_fragments \
             ORDER BY scope,version",
        )
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, u32>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
            ))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    let expected = PROJECT_FRAGMENTS
        .into_iter()
        .map(|fragment| {
            (
                "project".into(),
                fragment.version,
                fragment.name.into(),
                fragment_checksum(fragment),
            )
        })
        .collect::<Vec<_>>();
    if rows != expected {
        return Err(CoreError::Storage(
            "SQLite schema ledger is not the exact current Project 1.0 release".into(),
        ));
    }
    Ok(())
}

fn validate_planning_contract(connection: &Connection) -> CoreResult<()> {
    let mut statement = connection
        .prepare("SELECT singleton,release FROM planning_contract_identity ORDER BY singleton")
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, u32>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    if rows != [(1, "ai-native-longform-v2".into())] {
        return Err(CoreError::Storage(
            "SQLite planning contract identity must be exactly ai-native-longform-v2".into(),
        ));
    }
    Ok(())
}

fn schema_objects(
    connection: &Connection,
) -> CoreResult<BTreeMap<String, (String, String, String)>> {
    let mut statement = connection
        .prepare(
            "SELECT type,name,COALESCE(tbl_name,''),COALESCE(sql,'') FROM sqlite_master \
             WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name",
        )
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
            ))
        })
        .map_err(storage_error)?;
    let mut objects = BTreeMap::new();
    for row in rows {
        let (kind, name, table, sql) = row.map_err(storage_error)?;
        objects.insert(name, (kind, table, normalize_sql(&sql)));
    }
    Ok(objects)
}

fn fragment_checksum(fragment: SchemaFragment) -> String {
    sha256_fingerprint(fragment.sql.replace("\r\n", "\n").as_bytes())
}

fn normalize_sql(value: &str) -> String {
    value.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn storage_error(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fresh_project_schema_is_exact_and_complete() {
        let mut connection = Connection::open_in_memory().unwrap();
        connection.execute_batch("PRAGMA foreign_keys=ON").unwrap();
        apply_fresh_project_schema(&mut connection, "2026-08-31T00:00:00Z").unwrap();
        let count: u32 = connection
            .query_row("SELECT COUNT(*) FROM schema_fragments", [], |row| {
                row.get(0)
            })
            .unwrap();
        assert_eq!(count, 25);
        let planning_release: String = connection
            .query_row(
                "SELECT release FROM planning_contract_identity WHERE singleton=1",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(planning_release, "ai-native-longform-v2");
        validate_current_project_schema(&connection).unwrap();
    }

    #[test]
    fn checksum_drift_and_extra_objects_fail_closed() {
        let mut connection = Connection::open_in_memory().unwrap();
        apply_fresh_project_schema(&mut connection, "2026-08-31T00:00:00Z").unwrap();
        connection
            .execute(
                "UPDATE schema_fragments SET checksum='sha256:bad' WHERE version=25",
                [],
            )
            .unwrap();
        assert!(validate_current_project_schema(&connection).is_err());

        connection
            .execute(
                "UPDATE schema_fragments SET checksum=?1 WHERE version=25",
                [fragment_checksum(PROJECT_FRAGMENTS[24])],
            )
            .unwrap();
        connection
            .execute("CREATE TABLE injected(value TEXT)", [])
            .unwrap();
        assert!(validate_current_project_schema(&connection).is_err());
    }

    #[test]
    fn exact_optional_trigram_search_group_is_accepted() {
        let mut connection = Connection::open_in_memory().unwrap();
        apply_fresh_project_schema(&mut connection, "2026-08-31T00:00:00Z").unwrap();
        connection
            .execute_batch(
                "CREATE VIRTUAL TABLE search_trigram USING fts5( \
                 entity_type UNINDEXED, entity_id UNINDEXED, title, body, tokenize='trigram')",
            )
            .unwrap();
        validate_current_project_schema(&connection).unwrap();
    }

    #[test]
    fn known_prefix_is_not_silently_migrated_on_open() {
        let mut connection = Connection::open_in_memory().unwrap();
        apply_fresh_project_schema(&mut connection, "2026-08-31T00:00:00Z").unwrap();
        connection
            .execute("DELETE FROM schema_fragments WHERE version=25", [])
            .unwrap();
        assert!(validate_current_project_schema(&connection).is_err());
    }

    #[test]
    fn planning_contract_marker_fails_closed_when_missing_or_tampered() {
        let mut missing = Connection::open_in_memory().unwrap();
        apply_fresh_project_schema(&mut missing, "2026-08-31T00:00:00Z").unwrap();
        missing
            .execute("DELETE FROM planning_contract_identity", [])
            .unwrap();
        assert!(validate_current_project_schema(&missing).is_err());

        let mut tampered = Connection::open_in_memory().unwrap();
        apply_fresh_project_schema(&mut tampered, "2026-08-31T00:00:00Z").unwrap();
        tampered
            .execute_batch(
                "PRAGMA ignore_check_constraints=ON; \
                 UPDATE planning_contract_identity SET release='unexpected-release'; \
                 PRAGMA ignore_check_constraints=OFF;",
            )
            .unwrap();
        assert!(validate_current_project_schema(&tampered).is_err());
    }
}
