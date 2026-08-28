import { Show, createContext, createSignal, onCleanup, onMount, useContext, type ParentComponent } from "solid-js";
import { activateHostedSession, bridgeTransportName, invalidateHostedSession, subscribeToHostedSessionExpiry } from "./bridge";
import { hostedSignInUrl, loadHostedSession, logoutHostedSession } from "./hostedSession";
import { useI18n } from "./i18n";

const HostedSessionContext = createContext<{ logout: () => void }>();
type Phase = "checking" | "signed_out" | "ready" | "logging_out" | "error";

/** Local/Tauri and unbound static previews never acquire a cloud session. */
export const HostedSessionBoundary: ParentComponent = (props) => {
  if (bridgeTransportName() !== "hosted-http") return props.children;
  const { locale } = useI18n();
  const zh = () => locale() === "zh-CN";
  const [phase, setPhase] = createSignal<Phase>("checking");
  const [failedAction, setFailedAction] = createSignal<"check" | "logout">("check");
  let pending: AbortController | undefined;
  let generation = 0;
  let disposed = false;
  let unsubscribe: (() => void) | undefined;

  const begin = (next: Phase) => {
    const epoch = invalidateHostedSession();
    pending?.abort();
    pending = new AbortController();
    generation += 1;
    setPhase(next);
    return { controller: pending, generation, epoch };
  };
  const current = (attempt: ReturnType<typeof begin>) => !disposed && attempt.generation === generation && !attempt.controller.signal.aborted;

  async function checkSession() {
    if (disposed) return;
    const attempt = begin("checking");
    try {
      const session = await loadHostedSession(attempt.controller.signal);
      if (current(attempt)) setPhase(session && activateHostedSession(attempt.epoch) ? "ready" : "signed_out");
    } catch {
      if (current(attempt)) { setFailedAction("check"); setPhase("error"); }
    }
  }

  async function endSession() {
    if (disposed) return;
    const attempt = begin("logging_out");
    try {
      const logoutUrl = await logoutHostedSession(attempt.controller.signal);
      if (!current(attempt)) return;
      setPhase("signed_out");
      if (logoutUrl) window.location.assign(logoutUrl);
    } catch {
      if (current(attempt)) { setFailedAction("logout"); setPhase("error"); }
    }
  }

  onMount(() => {
    unsubscribe = subscribeToHostedSessionExpiry(() => {
      invalidateHostedSession();
      pending?.abort();
      generation += 1;
      setPhase("signed_out");
    });
    void checkSession();
  });
  onCleanup(() => { disposed = true; generation += 1; invalidateHostedSession(); pending?.abort(); unsubscribe?.(); });

  const busy = () => phase() === "checking" || phase() === "logging_out";
  const heading = () => phase() === "checking" ? (zh() ? "正在验证登录…" : "Checking your session…")
    : phase() === "logging_out" ? (zh() ? "正在退出…" : "Signing out…")
    : phase() === "error" ? (zh() ? "暂时无法确认云端会话" : "Your cloud session could not be verified")
    : (zh() ? "登录云端工作区" : "Sign in to your cloud workspace");

  return (
    <HostedSessionContext.Provider value={{ logout: () => void endSession() }}>
      <Show when={phase() === "ready"} fallback={
        <main id="main-content" class="nf-studio-resilience" aria-busy={busy()} tabIndex={-1}>
          <section class="nf-studio-resilience-card" aria-labelledby="hosted-session-heading">
            <small>Quillframe Studio · Cloud</small>
            <h1 id="hosted-session-heading" aria-live="polite">{heading()}</h1>
            <Show when={!busy()}>
              <p>{phase() === "error"
                ? (failedAction() === "logout"
                  ? (zh() ? "退出尚未确认。请重试退出，或重新检查会话。" : "Sign-out has not been confirmed. Retry sign-out or check your session again.")
                  : (zh() ? "请检查网络与浏览器 Cookie 设置后重试。未经验证的会话不会打开工作区。" : "Check your connection and browser cookie settings, then retry. The workspace stays closed until your session is verified."))
                : (zh() ? "通过安全登录访问你的云端项目，无需在本机安装 Core 或 Linux。" : "Sign in to access your cloud projects. No local Core or Linux installation is required.")}</p>
              <div>
                <Show when={phase() === "error"}>
                  <button type="button" class="wui-button wui-button--solid" onClick={() => void (failedAction() === "logout" ? endSession() : checkSession())}>{zh() ? "重试" : "Retry"}</button>
                </Show>
                <a class="wui-button wui-button--solid" href={hostedSignInUrl()}>{zh() ? "安全登录" : "Sign in securely"}</a>
                <button type="button" class="wui-button wui-button--soft" onClick={() => void checkSession()}>{zh() ? "重新检查会话" : "Check session again"}</button>
              </div>
            </Show>
          </section>
        </main>
      }>{props.children}</Show>
    </HostedSessionContext.Provider>
  );
};

export function HostedAccountButton() {
  const session = useContext(HostedSessionContext);
  const { locale } = useI18n();
  return <Show when={session}><button type="button" class="wui-button wui-button--ghost" onClick={() => session?.logout()}>{locale() === "zh-CN" ? "退出登录" : "Sign out"}</button></Show>;
}
