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

const FRAGMENTS: [(u32, &str, &str); 3] = [
    (
        1,
        "001_initial.sql",
        include_str!("../../../persistence/schema/global/001_initial.sql"),
    ),
    (
        2,
        "002_model_runtime.sql",
        include_str!("../../../persistence/schema/global/002_model_runtime.sql"),
    ),
    (
        3,
        "003_model_service_contract.sql",
        include_str!("../../../persistence/schema/global/003_model_service_contract.sql"),
    ),
];

pub fn apply_fresh_global_schema(connection: &mut Connection, applied_at: &str) -> CoreResult<()> {
    if applied_at.trim().is_empty() || !schema_objects(connection)?.is_empty() {
        return Err(CoreError::Storage(
            "fresh global schema requires an empty database and timestamp".into(),
        ));
    }
    let transaction = connection
        .transaction_with_behavior(TransactionBehavior::Immediate)
        .map_err(storage_error)?;
    transaction
        .execute_batch(SCHEMA_LEDGER_DDL)
        .map_err(storage_error)?;
    for (version, name, sql) in FRAGMENTS {
        transaction.execute_batch(sql).map_err(storage_error)?;
        transaction
            .execute(
                "INSERT INTO schema_fragments(scope,version,name,checksum,applied_at) \
                 VALUES('global',?1,?2,?3,?4)",
                params![version, name, checksum(sql), applied_at],
            )
            .map_err(storage_error)?;
    }
    transaction.commit().map_err(storage_error)?;
    validate_current_global_schema(connection)
}

pub fn validate_current_global_schema(connection: &Connection) -> CoreResult<()> {
    let identity = connection
        .query_row(
            "SELECT scope,release FROM quillframe_schema_identity",
            [],
            |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?)),
        )
        .map_err(storage_error)?;
    if identity != ("global".to_owned(), "1.0".to_owned()) {
        return Err(CoreError::Storage(
            "global database identity is not exact 1.0".into(),
        ));
    }
    let mut statement = connection
        .prepare(
            "SELECT version,name,checksum FROM schema_fragments \
             WHERE scope='global' ORDER BY version",
        )
        .map_err(storage_error)?;
    let ledger = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, u32>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })
        .map_err(storage_error)?
        .collect::<Result<Vec<_>, _>>()
        .map_err(storage_error)?;
    let expected_ledger = FRAGMENTS
        .iter()
        .map(|(version, name, sql)| (*version, (*name).to_owned(), checksum(sql)))
        .collect::<Vec<_>>();
    if ledger != expected_ledger {
        return Err(CoreError::Storage(
            "global schema ledger is not exact current 1.0".into(),
        ));
    }
    let expected = Connection::open_in_memory().map_err(storage_error)?;
    expected
        .execute_batch(SCHEMA_LEDGER_DDL)
        .map_err(storage_error)?;
    for (_, _, sql) in FRAGMENTS {
        expected.execute_batch(sql).map_err(storage_error)?;
    }
    if schema_objects(connection)? != schema_objects(&expected)? {
        return Err(CoreError::Storage(
            "global SQLite objects differ from exact current schema".into(),
        ));
    }
    let quick: String = connection
        .query_row("PRAGMA quick_check", [], |row| row.get(0))
        .map_err(storage_error)?;
    if quick != "ok" {
        return Err(CoreError::Storage(format!(
            "global SQLite quick_check failed: {quick}"
        )));
    }
    Ok(())
}

fn schema_objects(connection: &Connection) -> CoreResult<BTreeMap<String, String>> {
    let mut statement = connection
        .prepare(
            "SELECT name,sql FROM sqlite_master \
             WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL ORDER BY name",
        )
        .map_err(storage_error)?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(storage_error)?;
    let mut objects = BTreeMap::new();
    for row in rows {
        let (name, sql) = row.map_err(storage_error)?;
        objects.insert(name, sql.split_whitespace().collect::<Vec<_>>().join(" "));
    }
    Ok(objects)
}

fn checksum(sql: &str) -> String {
    sha256_fingerprint(sql.replace("\r\n", "\n").as_bytes())
}

fn storage_error(error: rusqlite::Error) -> CoreError {
    CoreError::Storage(error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn global_schema_is_exact_and_rejects_drift() {
        let mut connection = Connection::open_in_memory().unwrap();
        apply_fresh_global_schema(&mut connection, "2026-08-31T00:00:00Z").unwrap();
        validate_current_global_schema(&connection).unwrap();
        connection
            .execute("CREATE TABLE injected(value TEXT)", [])
            .unwrap();
        assert!(validate_current_global_schema(&connection).is_err());
    }
}
