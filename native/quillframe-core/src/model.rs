use std::{
    collections::BTreeSet,
    net::{IpAddr, Ipv4Addr, Ipv6Addr},
    time::Duration,
};

use reqwest::{redirect::Policy, Client};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use url::Url;

use crate::{fingerprint::sha256_fingerprint, CoreError, CoreResult};

const MAX_MODEL_RESPONSE_BYTES: usize = 2 * 1024 * 1024;

pub trait SecretStore: Send + Sync {
    fn read_secret(&self, credential_ref: &str) -> CoreResult<Option<String>>;
    fn write_secret(&self, credential_ref: &str, secret: &str) -> CoreResult<()>;
    fn delete_secret(&self, credential_ref: &str) -> CoreResult<()>;
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AuthStyle {
    Bearer,
    XApiKey,
    None,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProtocolFamily {
    OpenaiChatCompletions,
    OpenaiResponses,
    AnthropicMessages,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ServiceEndpoint {
    pub service_id: String,
    pub endpoint: String,
    pub credential_ref: Option<String>,
    pub auth_style: AuthStyle,
    pub protocol_family: ProtocolFamily,
    pub allow_loopback_http: bool,
}

impl ServiceEndpoint {
    pub fn validate_url(&self) -> CoreResult<Url> {
        if self.service_id.trim().is_empty() {
            return Err(runtime("service id is required"));
        }
        let url = Url::parse(&self.endpoint)
            .map_err(|_| runtime("model endpoint is not a valid absolute URL"))?;
        if url.username() != ""
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
        {
            return Err(runtime(
                "model endpoint cannot contain credentials, query or fragment",
            ));
        }
        let host = url
            .host_str()
            .ok_or_else(|| runtime("model endpoint requires a host"))?;
        let loopback_host = host.eq_ignore_ascii_case("localhost")
            || host.parse::<IpAddr>().is_ok_and(|ip| ip.is_loopback());
        if url.scheme() != "https"
            && !(url.scheme() == "http" && self.allow_loopback_http && loopback_host)
        {
            return Err(runtime(
                "model endpoint must use HTTPS; HTTP is limited to explicit loopback development",
            ));
        }
        if matches!(self.auth_style, AuthStyle::None) && self.credential_ref.is_some()
            || !matches!(self.auth_style, AuthStyle::None)
                && self.credential_ref.as_deref().is_none_or(str::is_empty)
        {
            return Err(runtime(
                "credential reference does not match model authentication style",
            ));
        }
        Ok(url)
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelRequest {
    pub request_id: String,
    pub model: String,
    pub system: String,
    pub user: String,
    pub temperature: Option<f32>,
    pub max_output_tokens: Option<u32>,
    pub absolute_deadline_ms: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelUsage {
    pub input_tokens: Option<u64>,
    pub output_tokens: Option<u64>,
    pub total_tokens: Option<u64>,
    pub cost_micros: Option<u64>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelResult {
    pub schema: String,
    pub request_id: String,
    pub service_id: String,
    pub model: String,
    pub content: String,
    pub provider_response_id: Option<String>,
    pub usage: ModelUsage,
    pub fingerprint: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelDescriptor {
    pub model_id: String,
    pub display_name: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ModelCatalog {
    pub schema: String,
    pub service_id: String,
    pub models: Vec<ModelDescriptor>,
    pub fingerprint: String,
}

impl ModelCatalog {
    fn create(service_id: impl Into<String>, mut models: Vec<ModelDescriptor>) -> CoreResult<Self> {
        models.sort_by(|left, right| left.model_id.cmp(&right.model_id));
        models.dedup_by(|left, right| left.model_id == right.model_id);
        if models.is_empty()
            || models.iter().any(|model| {
                model.model_id.trim().is_empty() || model.display_name.trim().is_empty()
            })
        {
            return Err(runtime("model discovery returned no usable models"));
        }
        let mut value = Self {
            schema: "quillframe_model_catalog_v1".into(),
            service_id: service_id.into(),
            models,
            fingerprint: String::new(),
        };
        let bytes = serde_json::to_vec(&value)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        value.fingerprint = sha256_fingerprint(bytes);
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        if self.schema != "quillframe_model_catalog_v1"
            || self.service_id.trim().is_empty()
            || self.models.is_empty()
            || self.models.iter().any(|model| {
                model.model_id.trim().is_empty() || model.display_name.trim().is_empty()
            })
        {
            return Err(runtime("model catalog is incomplete"));
        }
        let mut projection = self.clone();
        projection.fingerprint.clear();
        let expected = serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if expected != self.fingerprint {
            return Err(runtime("model catalog fingerprint changed"));
        }
        Ok(())
    }
}

impl ModelResult {
    pub fn record(
        request_id: impl Into<String>,
        service_id: impl Into<String>,
        model: impl Into<String>,
        content: impl Into<String>,
        provider_response_id: Option<String>,
        usage: ModelUsage,
    ) -> CoreResult<Self> {
        let mut value = Self {
            schema: "quillframe_model_result_v1".into(),
            request_id: request_id.into(),
            service_id: service_id.into(),
            model: model.into(),
            content: content.into(),
            provider_response_id,
            usage,
            fingerprint: String::new(),
        };
        let mut projection = value.clone();
        projection.fingerprint.clear();
        value.fingerprint = serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        value.validate()?;
        Ok(value)
    }

    pub fn validate(&self) -> CoreResult<()> {
        if self.schema != "quillframe_model_result_v1"
            || self.request_id.trim().is_empty()
            || self.service_id.trim().is_empty()
            || self.model.trim().is_empty()
            || self.content.trim().is_empty()
        {
            return Err(runtime("model result is incomplete"));
        }
        let mut projection = self.clone();
        projection.fingerprint.clear();
        let expected = serde_json::to_vec(&projection)
            .map(sha256_fingerprint)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        if expected != self.fingerprint {
            return Err(runtime("model result fingerprint changed"));
        }
        Ok(())
    }
}

pub struct ModelRuntime<'a> {
    secrets: &'a dyn SecretStore,
}

impl<'a> ModelRuntime<'a> {
    pub fn new(secrets: &'a dyn SecretStore) -> Self {
        Self { secrets }
    }

    pub async fn execute(
        &self,
        service: &ServiceEndpoint,
        request: &ModelRequest,
    ) -> CoreResult<ModelResult> {
        validate_request(request)?;
        let endpoint = service.validate_url()?;
        let (client, endpoint) = pinned_client(&endpoint, request.absolute_deadline_ms).await?;
        let secret = match &service.credential_ref {
            Some(reference) => self
                .secrets
                .read_secret(reference)?
                .ok_or_else(|| runtime("credential reference is unavailable"))?,
            None => String::new(),
        };
        let mut builder = match service.protocol_family {
            ProtocolFamily::OpenaiChatCompletions => client.post(endpoint.join("v1/chat/completions").map_err(|_|runtime("invalid OpenAI endpoint base"))?).json(&json!({
                "model":request.model,"messages":[{"role":"system","content":request.system},{"role":"user","content":request.user}],
                "temperature":request.temperature,"max_tokens":request.max_output_tokens
            })),
            ProtocolFamily::OpenaiResponses => client.post(endpoint.join("v1/responses").map_err(|_|runtime("invalid OpenAI endpoint base"))?).json(&json!({
                "model":request.model,"instructions":request.system,"input":request.user,"temperature":request.temperature,
                "max_output_tokens":request.max_output_tokens,"store":false
            })),
            ProtocolFamily::AnthropicMessages => client.post(endpoint.join("v1/messages").map_err(|_|runtime("invalid Anthropic endpoint base"))?)
                .header("anthropic-version","2023-06-01").json(&json!({"model":request.model,"system":request.system,
                    "messages":[{"role":"user","content":request.user}],"temperature":request.temperature,
                    "max_tokens":request.max_output_tokens.unwrap_or(4096)})),
        };
        builder = match service.auth_style {
            AuthStyle::Bearer => builder.bearer_auth(&secret),
            AuthStyle::XApiKey => builder.header("x-api-key", &secret),
            AuthStyle::None => builder,
        };
        let deadline = Duration::from_millis(request.absolute_deadline_ms);
        let response = tokio::time::timeout(deadline, builder.send())
            .await
            .map_err(|_| runtime("model request exceeded its absolute deadline"))?
            .map_err(|error| runtime(format!("model transport failed: {error}")))?;
        if !response.status().is_success() {
            return Err(runtime(format!(
                "model provider returned HTTP {}",
                response.status()
            )));
        }
        if response
            .content_length()
            .is_some_and(|length| length > MAX_MODEL_RESPONSE_BYTES as u64)
        {
            return Err(runtime("model response exceeds the byte limit"));
        }
        let mut response = response;
        let mut bytes = Vec::new();
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|error| runtime(format!("model response read failed: {error}")))?
        {
            if bytes.len().saturating_add(chunk.len()) > MAX_MODEL_RESPONSE_BYTES {
                return Err(runtime("model response exceeds the byte limit"));
            }
            bytes.extend_from_slice(&chunk);
        }
        let value: Value = serde_json::from_slice(&bytes)
            .map_err(|_| runtime("model provider response is not valid JSON"))?;
        match service.protocol_family {
            ProtocolFamily::OpenaiChatCompletions => normalize_openai_chat(service, request, value),
            ProtocolFamily::OpenaiResponses => normalize_openai_responses(service, request, value),
            ProtocolFamily::AnthropicMessages => normalize_anthropic(service, request, value),
        }
    }

    pub async fn discover_models(&self, service: &ServiceEndpoint) -> CoreResult<ModelCatalog> {
        let endpoint = service.validate_url()?;
        let (client, endpoint) = pinned_client(&endpoint, 30_000).await?;
        let secret = match &service.credential_ref {
            Some(reference) => self
                .secrets
                .read_secret(reference)?
                .ok_or_else(|| runtime("credential reference is unavailable"))?,
            None => String::new(),
        };
        let url = endpoint
            .join("v1/models")
            .map_err(|_| runtime("invalid model discovery endpoint base"))?;
        let mut builder = client.get(url);
        if service.protocol_family == ProtocolFamily::AnthropicMessages {
            builder = builder.header("anthropic-version", "2023-06-01");
        }
        builder = match service.auth_style {
            AuthStyle::Bearer => builder.bearer_auth(&secret),
            AuthStyle::XApiKey => builder.header("x-api-key", &secret),
            AuthStyle::None => builder,
        };
        let response = tokio::time::timeout(Duration::from_secs(30), builder.send())
            .await
            .map_err(|_| runtime("model discovery exceeded its absolute deadline"))?
            .map_err(|error| runtime(format!("model discovery transport failed: {error}")))?;
        if !response.status().is_success() {
            return Err(runtime(format!(
                "model discovery returned HTTP {}",
                response.status()
            )));
        }
        if response
            .content_length()
            .is_some_and(|length| length > MAX_MODEL_RESPONSE_BYTES as u64)
        {
            return Err(runtime("model discovery response exceeds the byte limit"));
        }
        let mut response = response;
        let mut bytes = Vec::new();
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|error| runtime(format!("model discovery read failed: {error}")))?
        {
            if bytes.len().saturating_add(chunk.len()) > MAX_MODEL_RESPONSE_BYTES {
                return Err(runtime("model discovery response exceeds the byte limit"));
            }
            bytes.extend_from_slice(&chunk);
        }
        let value: Value = serde_json::from_slice(&bytes)
            .map_err(|_| runtime("model discovery response is not valid JSON"))?;
        let models = value
            .get("data")
            .and_then(Value::as_array)
            .ok_or_else(|| runtime("model discovery response has no data array"))?
            .iter()
            .filter_map(|item| {
                let id = item.get("id")?.as_str()?.trim();
                if id.is_empty() {
                    return None;
                }
                Some(ModelDescriptor {
                    model_id: id.into(),
                    display_name: item
                        .get("display_name")
                        .and_then(Value::as_str)
                        .filter(|name| !name.trim().is_empty())
                        .unwrap_or(id)
                        .into(),
                })
            })
            .collect();
        ModelCatalog::create(&service.service_id, models)
    }
}

async fn pinned_client(endpoint: &Url, deadline_ms: u64) -> CoreResult<(Client, Url)> {
    let host = endpoint
        .host_str()
        .ok_or_else(|| runtime("model endpoint requires a host"))?;
    let port = endpoint
        .port_or_known_default()
        .ok_or_else(|| runtime("model endpoint has no port"))?;
    let addresses = tokio::net::lookup_host((host, port))
        .await
        .map_err(|error| runtime(format!("model endpoint DNS failed: {error}")))?
        .collect::<BTreeSet<_>>();
    if addresses.is_empty() {
        return Err(runtime("model endpoint DNS returned no addresses"));
    }
    let allow_loopback = endpoint.scheme() == "http";
    if addresses
        .iter()
        .any(|address| !allowed_address(address.ip(), allow_loopback))
    {
        return Err(runtime(
            "model endpoint DNS resolved to a forbidden network",
        ));
    }
    let pinned = *addresses.iter().next().unwrap();
    let client = Client::builder()
        .redirect(Policy::none())
        .no_proxy()
        .use_rustls_tls()
        .connect_timeout(Duration::from_secs(10))
        .timeout(Duration::from_millis(deadline_ms))
        .resolve(host, pinned)
        .user_agent("Quillframe-Rust-Core/1")
        .build()
        .map_err(|error| runtime(format!("model client build failed: {error}")))?;
    Ok((client, endpoint.clone()))
}

fn allowed_address(ip: IpAddr, allow_loopback: bool) -> bool {
    match ip {
        IpAddr::V4(ip) => {
            allow_loopback && ip.is_loopback()
                || !(ip.is_private()
                    || ip.is_loopback()
                    || ip.is_link_local()
                    || ip.is_multicast()
                    || ip.is_unspecified()
                    || ip == Ipv4Addr::BROADCAST)
        }
        IpAddr::V6(ip) => {
            allow_loopback && ip.is_loopback()
                || !(ip.is_loopback()
                    || ip.is_unspecified()
                    || ip.is_multicast()
                    || ipv6_unique_local(ip)
                    || ipv6_link_local(ip))
        }
    }
}

fn ipv6_unique_local(ip: Ipv6Addr) -> bool {
    ip.octets()[0] & 0xfe == 0xfc
}
fn ipv6_link_local(ip: Ipv6Addr) -> bool {
    ip.octets()[0] == 0xfe && ip.octets()[1] & 0xc0 == 0x80
}

fn validate_request(request: &ModelRequest) -> CoreResult<()> {
    if request.request_id.trim().is_empty()
        || request.model.trim().is_empty()
        || request.system.trim().is_empty()
        || request.user.trim().is_empty()
        || request.absolute_deadline_ms == 0
    {
        return Err(runtime("model request is incomplete"));
    }
    if request
        .temperature
        .is_some_and(|value| !value.is_finite() || !(0.0..=2.0).contains(&value))
    {
        return Err(runtime("model temperature is out of range"));
    }
    Ok(())
}

fn normalize_openai_chat(
    service: &ServiceEndpoint,
    request: &ModelRequest,
    value: Value,
) -> CoreResult<ModelResult> {
    let content = value
        .pointer("/choices/0/message/content")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| runtime("model response has no assistant content"))?
        .to_owned();
    let usage = value.get("usage").unwrap_or(&Value::Null);
    let mut result = ModelResult {
        schema: "quillframe_model_result_v1".into(),
        request_id: request.request_id.clone(),
        service_id: service.service_id.clone(),
        model: value
            .get("model")
            .and_then(Value::as_str)
            .unwrap_or(&request.model)
            .into(),
        content,
        provider_response_id: value.get("id").and_then(Value::as_str).map(str::to_owned),
        usage: ModelUsage {
            input_tokens: usage.get("prompt_tokens").and_then(Value::as_u64),
            output_tokens: usage.get("completion_tokens").and_then(Value::as_u64),
            total_tokens: usage.get("total_tokens").and_then(Value::as_u64),
            cost_micros: None,
        },
        fingerprint: String::new(),
    };
    let mut projection = result.clone();
    projection.fingerprint.clear();
    result.fingerprint = serde_json::to_vec(&projection)
        .map(sha256_fingerprint)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    result.validate()?;
    Ok(result)
}

fn normalize_openai_responses(
    service: &ServiceEndpoint,
    request: &ModelRequest,
    value: Value,
) -> CoreResult<ModelResult> {
    let content = value
        .get("output")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter(|item| item.get("type").and_then(Value::as_str) == Some("message"))
        .filter_map(|item| item.get("content").and_then(Value::as_array))
        .flatten()
        .filter(|item| item.get("type").and_then(Value::as_str) == Some("output_text"))
        .filter_map(|item| item.get("text").and_then(Value::as_str))
        .collect::<Vec<_>>()
        .join("");
    if content.trim().is_empty() {
        return Err(runtime("Responses API returned no output_text"));
    }
    normalized_result(
        service,
        request,
        &value,
        content,
        value.pointer("/usage/input_tokens").and_then(Value::as_u64),
        value
            .pointer("/usage/output_tokens")
            .and_then(Value::as_u64),
        value.pointer("/usage/total_tokens").and_then(Value::as_u64),
    )
}

fn normalize_anthropic(
    service: &ServiceEndpoint,
    request: &ModelRequest,
    value: Value,
) -> CoreResult<ModelResult> {
    let content = value
        .get("content")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter(|item| item.get("type").and_then(Value::as_str) == Some("text"))
        .filter_map(|item| item.get("text").and_then(Value::as_str))
        .collect::<Vec<_>>()
        .join("");
    if content.trim().is_empty() {
        return Err(runtime("Anthropic Messages returned no text content"));
    }
    let input = value.pointer("/usage/input_tokens").and_then(Value::as_u64);
    let output = value
        .pointer("/usage/output_tokens")
        .and_then(Value::as_u64);
    normalized_result(
        service,
        request,
        &value,
        content,
        input,
        output,
        input.zip(output).map(|(left, right)| left + right),
    )
}

fn normalized_result(
    service: &ServiceEndpoint,
    request: &ModelRequest,
    value: &Value,
    content: String,
    input_tokens: Option<u64>,
    output_tokens: Option<u64>,
    total_tokens: Option<u64>,
) -> CoreResult<ModelResult> {
    ModelResult::record(
        request.request_id.clone(),
        service.service_id.clone(),
        value
            .get("model")
            .and_then(Value::as_str)
            .unwrap_or(&request.model),
        content,
        value.get("id").and_then(Value::as_str).map(str::to_owned),
        ModelUsage {
            input_tokens,
            output_tokens,
            total_tokens,
            cost_micros: None,
        },
    )
}

fn runtime(message: impl Into<String>) -> CoreError {
    CoreError::ModelRuntime(message.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn endpoint_policy_rejects_credentials_plaintext_and_private_networks() {
        let service = ServiceEndpoint {
            service_id: "S".into(),
            endpoint: "http://api.example.test".into(),
            credential_ref: None,
            auth_style: AuthStyle::None,
            protocol_family: ProtocolFamily::OpenaiChatCompletions,
            allow_loopback_http: false,
        };
        assert!(service.validate_url().is_err());
        assert!(!allowed_address("10.0.0.1".parse().unwrap(), false));
        assert!(!allowed_address("::1".parse().unwrap(), false));
        assert!(allowed_address("127.0.0.1".parse().unwrap(), true));
        assert!(allowed_address("1.1.1.1".parse().unwrap(), false));
    }

    fn request() -> ModelRequest {
        ModelRequest {
            request_id: "REQ".into(),
            model: "model".into(),
            system: "system".into(),
            user: "user".into(),
            temperature: Some(0.2),
            max_output_tokens: Some(100),
            absolute_deadline_ms: 1_000,
        }
    }
    fn service(protocol_family: ProtocolFamily) -> ServiceEndpoint {
        ServiceEndpoint {
            service_id: "S".into(),
            endpoint: "https://api.example.test".into(),
            credential_ref: Some("credential".into()),
            auth_style: AuthStyle::Bearer,
            protocol_family,
            allow_loopback_http: false,
        }
    }

    #[test]
    fn supported_protocols_normalize_text_and_usage_into_one_receipt() {
        let responses=normalize_openai_responses(&service(ProtocolFamily::OpenaiResponses),&request(),json!({
            "id":"resp_1","model":"gpt","output":[{"type":"message","content":[{"type":"output_text","text":"{\"ok\":true}"}]}],
            "usage":{"input_tokens":10,"output_tokens":5,"total_tokens":15}})).unwrap();
        assert_eq!(responses.content, "{\"ok\":true}");
        assert_eq!(responses.usage.total_tokens, Some(15));
        let anthropic=normalize_anthropic(&service(ProtocolFamily::AnthropicMessages),&request(),json!({
            "id":"msg_1","model":"claude","content":[{"type":"text","text":"first"},{"type":"text","text":" second"}],
            "usage":{"input_tokens":7,"output_tokens":3}})).unwrap();
        assert_eq!(anthropic.content, "first second");
        assert_eq!(anthropic.usage.total_tokens, Some(10));
    }
}
