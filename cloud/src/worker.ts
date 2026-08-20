import { Container } from "@cloudflare/containers";
import worker from "./index.js";
import { strictProofKey } from "./core-provenance.js";
import { CoreBoundaryError, safeCoreForwardHeaders, validateCoreContainerRequest } from "./core-container.js";

type CoreProofEnv = { CORE_PROOF_KEY_B64: string; CORE_PROOF_KEY_ID: string; CORE_PROOF_PREVIOUS_KEY_B64?: string; CORE_PROOF_PREVIOUS_KEY_ID?: string };
export { SessionVault } from "./session-vault.js";
export { WorkspaceCoordinator } from "./workspace-coordinator.js";

export class QuillframeCoreContainer extends Container<CoreProofEnv> {
  defaultPort = 8080;
  sleepAfter = "10m";

  private readonly proofKeys: Map<string, Uint8Array>;
  private readonly expectedWorkspaceId: string;

  constructor(ctx: DurableObjectState<CoreProofEnv>, env: CoreProofEnv) {
    super(ctx, env);
    const instanceName = ctx.id.name;
    if (!instanceName || !/^[A-Za-z0-9._:-]{1,128}$/.test(instanceName)) throw new Error("Core container identity is invalid");
    this.expectedWorkspaceId = `workspace_${instanceName}`;
    if (!/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_KEY_ID) || !env.CORE_PROOF_KEY_B64 || ((env.CORE_PROOF_PREVIOUS_KEY_ID !== undefined) !== (env.CORE_PROOF_PREVIOUS_KEY_B64 !== undefined))) throw new Error("Core proof key configuration is invalid");
    if (env.CORE_PROOF_PREVIOUS_KEY_ID === env.CORE_PROOF_KEY_ID) throw new Error("Core proof key configuration is invalid");
    this.proofKeys = new Map([[env.CORE_PROOF_KEY_ID, strictProofKey(env.CORE_PROOF_KEY_B64)]]);
    if (env.CORE_PROOF_PREVIOUS_KEY_ID && env.CORE_PROOF_PREVIOUS_KEY_B64) {
      if (!/^[A-Za-z0-9._:-]{1,128}$/.test(env.CORE_PROOF_PREVIOUS_KEY_ID)) throw new Error("Core proof previous key configuration is invalid");
      this.proofKeys.set(env.CORE_PROOF_PREVIOUS_KEY_ID, strictProofKey(env.CORE_PROOF_PREVIOUS_KEY_B64, "previous proof key"));
    }
    this.envVars = {
      QUILLFRAME_CORE_PROOF_KEY_ID: env.CORE_PROOF_KEY_ID,
      QUILLFRAME_CORE_PROOF_KEY_B64: env.CORE_PROOF_KEY_B64,
      ...(env.CORE_PROOF_PREVIOUS_KEY_ID && env.CORE_PROOF_PREVIOUS_KEY_B64 ? {
        QUILLFRAME_CORE_PROOF_PREVIOUS_KEY_ID: env.CORE_PROOF_PREVIOUS_KEY_ID,
        QUILLFRAME_CORE_PROOF_PREVIOUS_KEY_B64: env.CORE_PROOF_PREVIOUS_KEY_B64,
      } : {}),
    };
  }

  override async fetch(request: Request): Promise<Response> {
    const source = new URL(request.url);
    let validated: { body: Uint8Array; proof: string };
    try {
      validated = await validateCoreContainerRequest(request, this.proofKeys, this.expectedWorkspaceId);
    } catch (error) {
      const code = error instanceof CoreBoundaryError ? error.code : "container_boundary_invalid";
      return Response.json({ schema: "quillframe_cloud_error_v1", code, authority: false }, { status: 403 });
    }
    const { body, proof } = validated;
    const forwardedHeaders = safeCoreForwardHeaders(request, proof);
    forwardedHeaders.set("content-length", String(body.byteLength));
    const forwarded = new Request(`http://core.internal${source.pathname}${source.search}`, { method: request.method, headers: forwardedHeaders, body: new Uint8Array(body) });
    return this.containerFetch(forwarded);
  }
}

export default worker;
