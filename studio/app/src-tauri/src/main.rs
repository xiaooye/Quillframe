use serde_json::Value;
use tauri::{AppHandle, State};
use tauri_plugin_shell::{process::{CommandChild, CommandEvent}, ShellExt};
use tokio::sync::Mutex;
use uuid::Uuid;

struct CoreHost { endpoint: String, token: String, _child: CommandChild }
struct CoreState(Mutex<Option<CoreHost>>);

async fn ensure_core(app: &AppHandle, state: &CoreState) -> Result<(String,String),String> {
    let mut guard=state.0.lock().await;
    if guard.is_none() {
        let token=Uuid::new_v4().simple().to_string();
        let command=app.shell().sidecar("quillframe-core").map_err(|e|e.to_string())?.args(["--port","0","--token",&token]);
        let (mut rx,child)=command.spawn().map_err(|e|e.to_string())?;
        let mut endpoint=None;
        while let Some(event)=rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes)=>{
                    let line=String::from_utf8_lossy(&bytes);
                    if let Ok(value)=serde_json::from_str::<Value>(&line) {
                        if value.get("schema").and_then(Value::as_str)==Some("quillframe_sidecar_ready_v1") {
                            if let Some(port)=value.get("port").and_then(Value::as_u64) { endpoint=Some(format!("http://127.0.0.1:{port}")); break; }
                        }
                    }
                }
                CommandEvent::Error(message)=>return Err(format!("Core sidecar error: {message}")),
                CommandEvent::Terminated(payload)=>return Err(format!("Core sidecar terminated during startup: {payload:?}")),
                _=>{}
            }
        }
        let endpoint=endpoint.ok_or_else(||"Core sidecar did not announce readiness".to_string())?;
        *guard=Some(CoreHost{endpoint,token,_child:child});
    }
    let host=guard.as_ref().unwrap(); Ok((host.endpoint.clone(),host.token.clone()))
}

#[tauri::command]
async fn bridge_invoke(app:AppHandle,state:State<'_,CoreState>,mut request:Value)->Result<Value,String>{
    let object=request.as_object_mut().ok_or_else(||"bridge request must be an object".to_string())?;
    object.insert("surface".into(),Value::String("tauri_local".into())); object.insert("authority".into(),Value::Bool(false));
    let (endpoint,token)=ensure_core(&app,&state).await?;
    let response=reqwest::Client::new().post(format!("{endpoint}/api/bridge/invoke")).header("X-Quillframe-Sidecar-Token",token).json(&request).send().await.map_err(|e|e.to_string())?;
    if !response.status().is_success(){return Err(format!("Core sidecar HTTP {}",response.status()))}
    response.json::<Value>().await.map_err(|e|e.to_string())
}

fn main(){
    tauri::Builder::default().plugin(tauri_plugin_shell::init()).manage(CoreState(Mutex::new(None))).invoke_handler(tauri::generate_handler![bridge_invoke]).run(tauri::generate_context!()).expect("error while running Quillframe");
}
