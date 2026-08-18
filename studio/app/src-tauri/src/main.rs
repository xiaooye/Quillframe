use keyring::{Entry, Error as KeyringError};
use serde_json::{json, Value};
use tauri::AppHandle;
use tauri_plugin_shell::{process::CommandEvent, ShellExt};
use uuid::Uuid;

const KEYRING_SERVICE: &str = "com.quillframe.studio.model-service";
const SECRET_REF_PREFIX: &str = "keyring:qf:";

fn entry(reference: &str) -> Result<Entry, String> {
    Entry::new(KEYRING_SERVICE, reference).map_err(|error| format!("credential store unavailable: {error}"))
}

fn vault_set(reference: &str, secret: &str) -> Result<(), String> {
    entry(reference)?
        .set_password(secret)
        .map_err(|error| format!("credential write failed: {error}"))
}

fn vault_get(reference: &str) -> Result<Option<String>, String> {
    match entry(reference)?.get_password() {
        Ok(secret) => Ok(Some(secret)),
        Err(KeyringError::NoEntry) => Ok(None),
        Err(error) => Err(format!("credential read failed: {error}")),
    }
}

fn vault_delete(reference: &str) -> Result<(), String> {
    match entry(reference)?.delete_credential() {
        Ok(()) | Err(KeyringError::NoEntry) => Ok(()),
        Err(error) => Err(format!("credential delete failed: {error}")),
    }
}

fn access_token(request: &Value) -> Option<String> {
    request
        .get("args")
        .and_then(Value::as_object)
        .and_then(|args| args.get("access_token"))
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
}

fn scrub(mut text: String, secrets: &[String]) -> String {
    let mut ordered = secrets.iter().filter(|value| !value.is_empty()).cloned().collect::<Vec<_>>();
    ordered.sort_by_key(|value| std::cmp::Reverse(value.len()));
    ordered.dedup();
    for secret in ordered {
        text = text.replace(&secret, "<redacted>");
    }
    text
}

async fn run_sidecar(app: &AppHandle, args: &[&str], input: Option<&Value>, secrets: &[String]) -> Result<Value, String> {
    let command = app
        .shell()
        .sidecar("quillframe-core")
        .map_err(|error| scrub(format!("sidecar configuration failed: {error}"), secrets))?
        .args(args);
    let (mut rx, mut child) = command
        .spawn()
        .map_err(|error| scrub(format!("sidecar spawn failed: {error}"), secrets))?;

    if let Some(payload) = input {
        let mut bytes = serde_json::to_vec(payload).map_err(|error| format!("sidecar payload serialization failed: {error}"))?;
        bytes.push(b'\n');
        child
            .write(&bytes)
            .map_err(|error| scrub(format!("sidecar stdin write failed: {error}"), secrets))?;
    }
    drop(child);

    let mut stdout = Vec::<u8>::new();
    let mut stderr = Vec::<u8>::new();
    let mut process_error: Option<String> = None;
    let mut terminated = false;

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => stdout.extend(bytes),
            CommandEvent::Stderr(bytes) => stderr.extend(bytes),
            CommandEvent::Error(message) => process_error = Some(scrub(message, secrets)),
            CommandEvent::Terminated(_) => {
                terminated = true;
                break;
            }
            _ => {}
        }
    }

    if let Some(message) = process_error {
        return Err(message);
    }
    if !terminated {
        return Err("Core sidecar ended without a termination event".to_string());
    }
    let stdout_text = scrub(String::from_utf8_lossy(&stdout).trim().to_string(), secrets);
    if stdout_text.is_empty() {
        let stderr_text = scrub(String::from_utf8_lossy(&stderr).trim().to_string(), secrets);
        return Err(if stderr_text.is_empty() {
            "Core sidecar returned no JSON result".to_string()
        } else {
            format!("Core sidecar returned no JSON result: {stderr_text}")
        });
    }
    serde_json::from_str::<Value>(&stdout_text)
        .map_err(|error| format!("Core sidecar returned invalid JSON: {error}"))
}

async fn credential_refs(app: &AppHandle) -> Result<Vec<String>, String> {
    let value = run_sidecar(app, &["credential-refs"], None, &[]).await?;
    if value.get("schema").and_then(Value::as_str) != Some("quillframe_tauri_credential_refs_v1") {
        return Err("Core sidecar credential reference schema mismatch".to_string());
    }
    let refs = value
        .get("credential_refs")
        .and_then(Value::as_array)
        .ok_or_else(|| "Core sidecar credential_refs must be an array".to_string())?;
    let mut out = Vec::new();
    for reference in refs {
        let reference = reference
            .as_str()
            .ok_or_else(|| "Core sidecar returned a non-string credential reference".to_string())?;
        if !reference.starts_with(SECRET_REF_PREFIX) {
            return Err("Core sidecar returned a credential reference outside the Tauri keyring namespace".to_string());
        }
        out.push(reference.to_string());
    }
    Ok(out)
}

async fn committed_refs_contains(app: &AppHandle, reference: &str) -> bool {
    credential_refs(app)
        .await
        .map(|refs| refs.iter().any(|candidate| candidate == reference))
        .unwrap_or(true)
}

async fn invoke_inner(app: &AppHandle, mut request: Value) -> Result<Value, String> {
    let object = request
        .as_object_mut()
        .ok_or_else(|| "bridge request must be an object".to_string())?;
    object.insert("surface".into(), Value::String("local_app".into()));
    object.insert("authority".into(), Value::Bool(false));

    let mut credential_secrets = serde_json::Map::new();
    for reference in credential_refs(app).await? {
        if let Some(secret) = vault_get(&reference)? {
            credential_secrets.insert(reference, Value::String(secret));
        }
    }

    let request_token = access_token(&request);
    let mut redactions = credential_secrets
        .values()
        .filter_map(Value::as_str)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .collect::<Vec<_>>();
    if let Some(secret) = request_token.as_ref() {
        redactions.push(secret.clone());
    }

    let prepared_ref = request_token
        .as_ref()
        .map(|_| format!("{SECRET_REF_PREFIX}{}", Uuid::new_v4().simple()));
    if let (Some(reference), Some(secret)) = (prepared_ref.as_ref(), request_token.as_ref()) {
        vault_set(reference, secret)?;
    }

    let envelope = json!({
        "request": request,
        "credential_secrets": Value::Object(credential_secrets),
        "prepared_secret_ref": prepared_ref,
    });
    let sidecar_result = run_sidecar(app, &["invoke"], Some(&envelope), &redactions).await;
    let value = match sidecar_result {
        Ok(value) => value,
        Err(error) => {
            if let Some(reference) = prepared_ref.as_ref() {
                if !committed_refs_contains(app, reference).await {
                    let _ = vault_delete(reference);
                }
            }
            return Err(scrub(error, &redactions));
        }
    };

    if value.get("schema").and_then(Value::as_str) != Some("quillframe_tauri_sidecar_result_v1") {
        if let Some(reference) = prepared_ref.as_ref() {
            if !committed_refs_contains(app, reference).await {
                let _ = vault_delete(reference);
            }
        }
        return Err("Core sidecar result schema mismatch".to_string());
    }
    let bridge_result = value
        .get("bridge_result")
        .cloned()
        .ok_or_else(|| "Core sidecar omitted bridge_result".to_string())?;
    let bridge_ok = bridge_result.get("status").and_then(Value::as_str) == Some("ok");

    if let Some(reference) = prepared_ref.as_ref() {
        let consumed = value
            .get("prepared_secret_consumed")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let committed = committed_refs_contains(app, reference).await;
        if !bridge_ok || !consumed {
            if !committed {
                let _ = vault_delete(reference);
            }
            if bridge_ok && !consumed {
                return Err("Core succeeded without consuming the preallocated durable credential reference".to_string());
            }
        }
    }

    if bridge_ok {
        if let Some(actions) = value.get("secret_actions").and_then(Value::as_array) {
            for action in actions {
                if action.get("kind").and_then(Value::as_str) != Some("delete") {
                    continue;
                }
                if let Some(reference) = action.get("credential_ref").and_then(Value::as_str) {
                    if reference.starts_with(SECRET_REF_PREFIX) {
                        if let Err(error) = vault_delete(reference) {
                            eprintln!("Quillframe credential cleanup warning for {reference}: {error}");
                        }
                    }
                }
            }
        }
    } else if let Some(reference) = prepared_ref.as_ref() {
        if !committed_refs_contains(app, reference).await {
            let _ = vault_delete(reference);
        }
    }

    Ok(bridge_result)
}

#[tauri::command]
async fn bridge_invoke(app: AppHandle, request: Value) -> Result<Value, String> {
    let request_secret = access_token(&request).into_iter().collect::<Vec<_>>();
    invoke_inner(&app, request)
        .await
        .map_err(|error| scrub(error, &request_secret))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![bridge_invoke])
        .run(tauri::generate_context!())
        .expect("error while running Quillframe Studio");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_secret_scrub_is_exact_and_business_fields_survive() {
        let request = json!({"args": {"access_token": "SECRET", "authorization": {"token_budget": "not-a-secret"}}});
        assert_eq!(access_token(&request).as_deref(), Some("SECRET"));
        let scrubbed = scrub(
            "provider echoed SECRET and EXISTING; token_budget survives".to_string(),
            &["SECRET".to_string(), "EXISTING".to_string()],
        );
        assert!(!scrubbed.contains("SECRET"));
        assert!(!scrubbed.contains("EXISTING"));
        assert!(scrubbed.contains("token_budget survives"));
    }

    #[test]
    fn durable_reference_namespace_is_not_a_secret_value() {
        let reference = format!("{SECRET_REF_PREFIX}{}", Uuid::nil().simple());
        assert!(reference.starts_with(SECRET_REF_PREFIX));
        assert!(!reference.contains("access_token"));
    }

    #[test]
    #[ignore = "requires a real OS credential store session"]
    fn os_keyring_roundtrip() {
        let reference = format!("{SECRET_REF_PREFIX}test-{}", Uuid::new_v4().simple());
        let secret = format!("test-secret-{}", Uuid::new_v4().simple());
        vault_set(&reference, &secret).expect("OS keyring set");
        assert_eq!(vault_get(&reference).expect("OS keyring get"), Some(secret));
        vault_delete(&reference).expect("OS keyring delete");
        assert_eq!(vault_get(&reference).expect("OS keyring missing"), None);
    }
}
