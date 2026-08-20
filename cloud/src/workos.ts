export type WorkOSAuthResult = {
  user: { id: string; email?: string; first_name?: string; last_name?: string };
  access_token: string;
  refresh_token: string;
  session_id?: string;
  authentication_method?: string;
};

export class WorkOSError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

export class WorkOSClient {
  constructor(
    private readonly config: { clientId: string; apiKey: string; redirectUri: string },
    private readonly fetcher: (request: Request) => Promise<Response> = globalThis.fetch,
  ) {}

  authorizationUrl(input: { state: string; codeChallenge: string }): URL {
    const url = new URL("https://api.workos.com/user_management/authorize");
    url.search = new URLSearchParams({
      response_type: "code",
      client_id: this.config.clientId,
      redirect_uri: this.config.redirectUri,
      provider: "authkit",
      state: input.state,
      code_challenge: input.codeChallenge,
      code_challenge_method: "S256",
    }).toString();
    return url;
  }

  async authenticateCode(input: { code: string; codeVerifier: string; ipAddress?: string; userAgent?: string }): Promise<WorkOSAuthResult> {
    if (!input.code || !input.codeVerifier) throw new WorkOSError("auth_callback_invalid", "authorization code and verifier are required");
    const body: Record<string, string> = {
      client_id: this.config.clientId,
      client_secret: this.config.apiKey,
      grant_type: "authorization_code",
      code: input.code,
      code_verifier: input.codeVerifier,
    };
    if (input.ipAddress) body.ip_address = input.ipAddress;
    if (input.userAgent) body.user_agent = input.userAgent;
    const response = await this.fetcher(new Request("https://api.workos.com/user_management/authenticate", {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    }));
    if (!response.ok) throw new WorkOSError("auth_exchange_failed", "WorkOS authorization exchange failed");
    const result = await response.json() as Partial<WorkOSAuthResult>;
    if (!result.user?.id || !result.access_token || !result.refresh_token) throw new WorkOSError("auth_exchange_invalid", "WorkOS authorization response is incomplete");
    return result as WorkOSAuthResult;
  }

  logoutUrl(sessionId: string, returnTo: string): URL {
    const url = new URL("https://api.workos.com/user_management/sessions/logout");
    url.search = new URLSearchParams({ session_id: sessionId, return_to: returnTo }).toString();
    return url;
  }
}
