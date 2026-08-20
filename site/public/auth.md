# Quillframe authentication and secrets

The public Quillframe product site does not advertise a hosted Core API, model gateway, A2A server, MCP server, OAuth resource server, or other authenticated agent endpoint.

Model-service credentials belong to the Quillframe host runtime. Ordinary model setup uses `API Endpoint` and `Access Token`; the resolved token is a host secret and must not be sent to the product website, committed to the repository, stored in project SQLite, injected into prompts/Context, or exposed in browser bundles.

Quillframe Studio cloud UI is not authority by itself. Any future authenticated remote Core surface must publish its own versioned authentication and authority contract before clients rely on it.

Security policy: https://github.com/xiaooye/Quillframe/blob/main/SECURITY.md
