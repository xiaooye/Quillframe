use std::{
    env,
    io::{self, BufRead},
    net::{IpAddr, Ipv4Addr, SocketAddr},
    path::{Component, Path, PathBuf},
    sync::Arc,
};

use axum::{
    body::Body,
    extract::{DefaultBodyLimit, Request, State},
    http::{header, HeaderValue, Method, StatusCode, Uri},
    response::{IntoResponse, Response},
    routing::{any, post},
    Json, Router,
};
use quillframe_core::HostBridgeRuntime;
use quillframe_secrets::OsSecretStore;
use serde_json::{json, Value};
use tokio::net::TcpListener;

const MAX_REQUEST_BYTES: usize = 128 * 1024;
const TOKEN_PLACEHOLDER: &str = "__QUILLFRAME_STUDIO_TOKEN__";

#[derive(Clone)]
struct AppState {
    global_root: Arc<PathBuf>,
    dist: Arc<PathBuf>,
    token: Arc<String>,
    port: u16,
}

#[tokio::main]
async fn main() {
    if let Err(error) = run().await {
        eprintln!("quillframe-host: {error}");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let command = args.next().unwrap_or_else(|| "help".into());
    let rest = args.collect::<Vec<_>>();
    match command.as_str() {
        "invoke" => {
            let root = required_option(&rest, "--core-root")?;
            let request = required_option(&rest, "--request")?;
            let runtime = HostBridgeRuntime::open_with_secret_store(root, Arc::new(OsSecretStore))
                .map_err(|error| error.to_string())?;
            let value = serde_json::from_str(request).map_err(|error| error.to_string())?;
            println!("{}", runtime.invoke_value_async(value).await);
            Ok(())
        }
        "invoke-file" => {
            let root = required_option(&rest, "--core-root")?;
            let request_path = required_option(&rest, "--request-file")?;
            let runtime = HostBridgeRuntime::open_with_secret_store(root, Arc::new(OsSecretStore))
                .map_err(|error| error.to_string())?;
            let request = std::fs::read_to_string(request_path)
                .map_err(|error| format!("request file read failed: {error}"))?;
            let value = serde_json::from_str(&request).map_err(|error| error.to_string())?;
            println!("{}", runtime.invoke_value_async(value).await);
            Ok(())
        }
        "book-setup-propose-file" => {
            let root = required_option(&rest, "--core-root")?;
            let project_id = required_option(&rest, "--project-id")?;
            let expected_version = required_option(&rest, "--expected-version")?
                .parse::<u64>()
                .map_err(|error| format!("invalid expected version: {error}"))?;
            let setup_path = required_option(&rest, "--setup-file")?;
            let idempotency_key = required_option(&rest, "--idempotency-key")?;
            let typed_setup = serde_json::from_str::<serde_json::Value>(
                &std::fs::read_to_string(setup_path)
                    .map_err(|error| format!("setup file read failed: {error}"))?,
            )
            .map_err(|error| format!("setup file is not valid JSON: {error}"))?;
            let runtime = HostBridgeRuntime::open_with_secret_store(root, Arc::new(OsSecretStore))
                .map_err(|error| error.to_string())?;
            let request = json!({
                "schema":"quillframe_host_bridge_request_v11",
                "bridge_version":"11",
                "request_id":format!("book-setup-propose-file-{}", uuid::Uuid::new_v4()),
                "operation":"book.setup.propose",
                "surface":"cli",
                "args":{
                    "project_id":project_id,
                    "expected_version":expected_version,
                    "typed_setup":typed_setup,
                    "idempotency_key":idempotency_key,
                },
                "authority":false,
            });
            println!("{}", runtime.invoke_value_async(request).await);
            Ok(())
        }
        "stdio" => {
            let root = required_option(&rest, "--core-root")?;
            let runtime = HostBridgeRuntime::open_with_secret_store(root, Arc::new(OsSecretStore))
                .map_err(|error| error.to_string())?;
            for line in io::stdin().lock().lines() {
                let line = line.map_err(|error| error.to_string())?;
                if line.trim().is_empty() {
                    continue;
                }
                let value = serde_json::from_str(&line)
                    .unwrap_or_else(|error| json!({"invalid_json":error.to_string()}));
                println!("{}", runtime.invoke_value_async(value).await);
            }
            Ok(())
        }
        "serve" => serve(rest).await,
        _ => Err(
            "usage: quillframe-host <invoke|invoke-file|book-setup-propose-file|stdio|serve> [options]".into(),
        ),
    }
}

async fn serve(args: Vec<String>) -> Result<(), String> {
    let root = PathBuf::from(required_option(&args, "--core-root")?);
    let dist = PathBuf::from(required_option(&args, "--dist")?)
        .canonicalize()
        .map_err(|error| format!("invalid Studio dist: {error}"))?;
    if !dist.join("index.html").is_file() {
        return Err("Studio dist/index.html is unavailable".into());
    }
    let port = optional_option(&args, "--port")
        .unwrap_or("0")
        .parse::<u16>()
        .map_err(|_| "--port must be 0..65535".to_string())?;
    let token = optional_option(&args, "--token")
        .map(ToOwned::to_owned)
        .unwrap_or_else(|| uuid::Uuid::new_v4().simple().to_string());
    if token.len() < 32 || token.bytes().any(|byte| !byte.is_ascii_alphanumeric()) {
        return Err("--token must contain at least 32 ASCII alphanumeric characters".into());
    }
    HostBridgeRuntime::open_with_secret_store(&root, Arc::new(OsSecretStore))
        .map_err(|error| error.to_string())?;
    let listener = TcpListener::bind(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port))
        .await
        .map_err(|error| error.to_string())?;
    let address = listener.local_addr().map_err(|error| error.to_string())?;
    let state = AppState {
        global_root: Arc::new(root),
        dist: Arc::new(dist),
        token: Arc::new(token.clone()),
        port: address.port(),
    };
    let app = router(state);
    println!(
        "{}",
        json!({
            "schema":"quillframe_launch_receipt_v1",
            "status":"ready",
            "profile":"local",
            "url":format!("http://127.0.0.1:{}",address.port()),
            "storage_boundary":"project_local_sqlite",
            "cloud_upload_started":false,
            "runtime":"rust_core",
            "authority":false
        })
    );
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .map_err(|error| error.to_string())
}

fn router(state: AppState) -> Router {
    Router::new()
        .route("/api/bridge/invoke", post(invoke))
        .fallback(any(static_or_reject))
        .layer(DefaultBodyLimit::max(MAX_REQUEST_BYTES))
        .with_state(state)
}

async fn invoke(State(state): State<AppState>, request: Request) -> Response {
    if let Err(response) = validate_transport(&state, &request) {
        return *response;
    }
    let raw = match axum::body::to_bytes(request.into_body(), MAX_REQUEST_BYTES).await {
        Ok(raw) if !raw.is_empty() => raw,
        Ok(_) => {
            return transport_error(
                StatusCode::BAD_REQUEST,
                "request_size_rejected",
                "request body is empty",
            )
        }
        Err(_) => {
            return transport_error(
                StatusCode::PAYLOAD_TOO_LARGE,
                "request_size_rejected",
                "request body is too large",
            )
        }
    };
    let value: Value = match serde_json::from_slice(&raw) {
        Ok(Value::Object(values)) => Value::Object(values),
        Ok(_) => {
            return transport_error(
                StatusCode::BAD_REQUEST,
                "invalid_request",
                "Bridge request root must be an object",
            )
        }
        Err(_) => {
            return transport_error(
                StatusCode::BAD_REQUEST,
                "invalid_json",
                "request body must be valid JSON",
            )
        }
    };
    let root = state.global_root.clone();
    let handle = tokio::runtime::Handle::current();
    let result = match tokio::task::spawn_blocking(move || {
        let runtime =
            HostBridgeRuntime::open_with_secret_store(root.as_path(), Arc::new(OsSecretStore))?;
        Ok::<_, quillframe_core::CoreError>(handle.block_on(runtime.invoke_value_async(value)))
    })
    .await
    {
        Ok(Ok(result)) => result,
        Ok(Err(error)) => {
            return transport_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "core_open_failed",
                &error.to_string(),
            )
        }
        Err(_) => {
            return transport_error(
                StatusCode::INTERNAL_SERVER_ERROR,
                "core_task_failed",
                "Rust Core task did not complete",
            )
        }
    };
    secured((StatusCode::OK, Json(result)).into_response())
}

fn validate_transport(state: &AppState, request: &Request) -> Result<(), Box<Response>> {
    let expected_host = format!("127.0.0.1:{}", state.port);
    let localhost = format!("localhost:{}", state.port);
    let host = request
        .headers()
        .get(header::HOST)
        .and_then(|value| value.to_str().ok());
    if !matches!(host, Some(value) if value == expected_host || value == localhost) {
        return Err(Box::new(transport_error(
            StatusCode::FORBIDDEN,
            "invalid_host",
            "Host is not the loopback Studio origin",
        )));
    }
    if request
        .headers()
        .get(header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.split(';').next())
        != Some("application/json")
    {
        return Err(Box::new(transport_error(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "content_type_rejected",
            "Content-Type must be application/json",
        )));
    }
    let allowed_origins = [
        format!("http://{expected_host}"),
        format!("http://{localhost}"),
    ];
    if let Some(origin) = request
        .headers()
        .get(header::ORIGIN)
        .and_then(|value| value.to_str().ok())
    {
        if !allowed_origins
            .iter()
            .any(|allowed| constant_time_eq(origin, allowed))
        {
            return Err(Box::new(transport_error(
                StatusCode::FORBIDDEN,
                "origin_rejected",
                "request is not from the loopback Studio origin",
            )));
        }
    }
    if let Some(site) = request
        .headers()
        .get("sec-fetch-site")
        .and_then(|value| value.to_str().ok())
    {
        if site != "same-origin" && site != "none" {
            return Err(Box::new(transport_error(
                StatusCode::FORBIDDEN,
                "origin_rejected",
                "cross-origin access is disabled",
            )));
        }
    }
    let supplied = request
        .headers()
        .get("x-quillframe-studio-token")
        .and_then(|value| value.to_str().ok())
        .unwrap_or("");
    if !constant_time_eq(supplied, &state.token) {
        return Err(Box::new(transport_error(
            StatusCode::FORBIDDEN,
            "token_rejected",
            "Studio transport token is missing or invalid",
        )));
    }
    Ok(())
}

async fn static_or_reject(State(state): State<AppState>, method: Method, uri: Uri) -> Response {
    if method != Method::GET {
        return transport_error(
            StatusCode::METHOD_NOT_ALLOWED,
            "method_rejected",
            "method is not supported",
        );
    }
    if uri.path().starts_with("/api/") {
        return transport_error(
            StatusCode::NOT_FOUND,
            "api_not_found",
            "unknown Studio API endpoint",
        );
    }
    let relative = uri.path().trim_start_matches('/');
    let candidate = Path::new(relative);
    if candidate
        .components()
        .any(|part| !matches!(part, Component::Normal(_)))
        && !relative.is_empty()
    {
        return transport_error(
            StatusCode::BAD_REQUEST,
            "path_rejected",
            "static path is unsafe",
        );
    }
    let file = state.dist.join(candidate);
    if !relative.is_empty()
        && file.is_file()
        && file.file_name().and_then(|name| name.to_str()) != Some("index.html")
    {
        match tokio::fs::read(&file).await {
            Ok(body) => return secured(binary(StatusCode::OK, body, media_type(&file))),
            Err(_) => {
                return transport_error(
                    StatusCode::NOT_FOUND,
                    "asset_not_found",
                    "asset is unavailable",
                )
            }
        }
    }
    match tokio::fs::read_to_string(state.dist.join("index.html")).await {
        Ok(index) => secured(binary(
            StatusCode::OK,
            index.replace(TOKEN_PLACEHOLDER, &state.token).into_bytes(),
            "text/html; charset=utf-8",
        )),
        Err(_) => transport_error(
            StatusCode::SERVICE_UNAVAILABLE,
            "app_not_built",
            "Studio dist/index.html is unavailable",
        ),
    }
}

fn transport_error(status: StatusCode, code: &str, message: &str) -> Response {
    secured((status, Json(json!({"schema":"quillframe_studio_transport_error_v1","code":code,"message":message,"authority":false}))).into_response())
}

fn binary(status: StatusCode, body: Vec<u8>, content_type: &'static str) -> Response {
    let mut response = Response::new(Body::from(body));
    *response.status_mut() = status;
    response
        .headers_mut()
        .insert(header::CONTENT_TYPE, HeaderValue::from_static(content_type));
    response
}

fn secured(mut response: Response) -> Response {
    let headers = response.headers_mut();
    headers.insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    headers.insert(
        "x-content-type-options",
        HeaderValue::from_static("nosniff"),
    );
    headers.insert(
        header::REFERRER_POLICY,
        HeaderValue::from_static("no-referrer"),
    );
    headers.insert(
        "cross-origin-opener-policy",
        HeaderValue::from_static("same-origin"),
    );
    headers.insert(header::CONTENT_SECURITY_POLICY, HeaderValue::from_static("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"));
    response
}

fn media_type(path: &Path) -> &'static str {
    match path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("")
    {
        "css" => "text/css; charset=utf-8",
        "html" => "text/html; charset=utf-8",
        "js" | "mjs" => "application/javascript; charset=utf-8",
        "json" => "application/json; charset=utf-8",
        "svg" => "image/svg+xml; charset=utf-8",
        "png" => "image/png",
        "ico" => "image/x-icon",
        "woff2" => "font/woff2",
        _ => "application/octet-stream",
    }
}

fn constant_time_eq(left: &str, right: &str) -> bool {
    let mut difference = left.len() ^ right.len();
    for index in 0..left.len().max(right.len()) {
        difference |= usize::from(
            left.as_bytes().get(index).copied().unwrap_or(0)
                ^ right.as_bytes().get(index).copied().unwrap_or(0),
        );
    }
    difference == 0
}

fn required_option<'a>(args: &'a [String], name: &str) -> Result<&'a str, String> {
    optional_option(args, name).ok_or_else(|| format!("{name} is required"))
}

fn optional_option<'a>(args: &'a [String], name: &str) -> Option<&'a str> {
    args.windows(2)
        .find(|pair| pair[0] == name)
        .map(|pair| pair[1].as_str())
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::to_bytes;
    use tower::ServiceExt;

    fn request(body: &'static str, token: &'static str) -> Request {
        Request::builder()
            .method(Method::POST)
            .uri("/api/bridge/invoke")
            .header(header::HOST, "127.0.0.1:43119")
            .header(header::ORIGIN, "http://127.0.0.1:43119")
            .header(header::CONTENT_TYPE, "application/json")
            .header("x-quillframe-studio-token", token)
            .body(Body::from(body))
            .unwrap()
    }

    #[tokio::test]
    async fn loopback_transport_requires_token_and_returns_rust_bridge() {
        let root = env::temp_dir().join(format!("qf-host-test-{}", uuid::Uuid::new_v4()));
        let dist = root.join("dist");
        std::fs::create_dir_all(&dist).unwrap();
        std::fs::write(dist.join("index.html"), TOKEN_PLACEHOLDER).unwrap();
        let state = AppState {
            global_root: Arc::new(root.join("core")),
            dist: Arc::new(dist),
            token: Arc::new("0123456789abcdef0123456789abcdef".into()),
            port: 43119,
        };
        let app = router(state);
        let denied = app.clone().oneshot(request("{}", "wrong")).await.unwrap();
        assert_eq!(denied.status(), StatusCode::FORBIDDEN);
        let body = r#"{"schema":"quillframe_host_bridge_request_v11","bridge_version":"11","request_id":"R1","operation":"bridge.describe","surface":"local_app","args":{},"authority":false}"#;
        let accepted = app
            .oneshot(request(body, "0123456789abcdef0123456789abcdef"))
            .await
            .unwrap();
        assert_eq!(accepted.status(), StatusCode::OK);
        let value: Value = serde_json::from_slice(
            &to_bytes(accepted.into_body(), MAX_REQUEST_BYTES)
                .await
                .unwrap(),
        )
        .unwrap();
        assert_eq!(value["status"], "ok");
        assert_eq!(value["authority"], false);
        std::fs::remove_dir_all(root).unwrap();
    }
}
