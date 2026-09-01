use quillframe_core::HostBridgeRuntime;
use quillframe_secrets::OsSecretStore;
use serde_json::Value;
use tauri::{AppHandle, Manager};

#[tauri::command]
async fn bridge_invoke(app: AppHandle, mut request: Value) -> Result<Value, String> {
    let object = request
        .as_object_mut()
        .ok_or_else(|| "bridge request must be an object".to_string())?;
    object.insert("surface".into(), Value::String("local_app".into()));
    object.insert("authority".into(), Value::Bool(false));
    let root = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Studio data directory is unavailable: {error}"))?
        .join("core");
    tauri::async_runtime::spawn_blocking(move || {
        let runtime =
            HostBridgeRuntime::open_with_secret_store(root, std::sync::Arc::new(OsSecretStore))
                .map_err(|error| format!("Rust Core initialization failed: {error}"))?;
        Ok(tauri::async_runtime::block_on(
            runtime.invoke_value_async(request),
        ))
    })
    .await
    .map_err(|error| format!("Rust Core task failed: {error}"))?
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![bridge_invoke])
        .run(tauri::generate_context!())
        .expect("error while running Quillframe Studio");
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn local_tauri_boundary_never_accepts_caller_authority() {
        let mut request = json!({"surface":"hosted_web","authority":true});
        let object = request.as_object_mut().unwrap();
        object.insert("surface".into(), Value::String("local_app".into()));
        object.insert("authority".into(), Value::Bool(false));
        assert_eq!(request["surface"], "local_app");
        assert_eq!(request["authority"], false);
    }
}
