import { Suspense, lazy, type JSX } from "solid-js";
import { render } from "solid-js/web";
import { Route, Router } from "@solidjs/router";
import { AppShell } from "./AppShell";
import { StudioFailureBoundary, StudioNotFound, StudioRouteLoading, StudioSkipLink } from "./StudioResilience";
import { bridgeTransportAvailable } from "./bridge";
import { I18nProvider } from "./i18n";
import { StudioProvider } from "./studio";
import "./styles/index.css";

const Desk = lazy(() => import("./routes/Desk"));
const Start = lazy(() => import("./routes/Start"));
const Project = lazy(() => import("./routes/Project"));
const Workspace = lazy(() => import("./routes/Workspace"));
const Agents = lazy(() => import("./routes/Agents"));
const RuntimeRoute = lazy(() => import("./routes/Runtime"));
const ContextRoute = lazy(() => import("./routes/Context"));
const Capabilities = lazy(() => import("./routes/Capabilities"));
const Semantic = lazy(() => import("./routes/Semantic"));
const Diagnostics = lazy(() => import("./routes/Diagnostics"));

const root = document.getElementById("app");
if (!root) throw new Error("#app mount point is missing");

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";
document.documentElement.dataset.productLanguage = "novelforge-kawaii-v1";

function StudioShellRoot(props: { children?: JSX.Element }) {
  return (
    <AppShell>
      <Suspense fallback={<StudioRouteLoading />}>{props.children}</Suspense>
    </AppShell>
  );
}

async function configureOfflineShell() {
  if (!("serviceWorker" in navigator)) return;

  if (bridgeTransportAvailable()) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(
      registrations
        .filter((registration) => {
          const scriptUrl = registration.active?.scriptURL ?? registration.waiting?.scriptURL ?? registration.installing?.scriptURL;
          return scriptUrl ? new URL(scriptUrl).pathname === "/sw.js" : false;
        })
        .map((registration) => registration.unregister()),
    );
    return;
  }

  window.addEventListener(
    "load",
    () => {
      void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined);
    },
    { once: true },
  );
}

void configureOfflineShell().catch(() => undefined);

render(
  () => (
    <I18nProvider>
      <StudioProvider>
        <StudioFailureBoundary>
          <StudioSkipLink />
          <Router root={StudioShellRoot}>
            <Route path="/" component={Desk} />
            <Route path="/start" component={Start} />
            <Route path="/project" component={Project} />
            <Route path="/workspace" component={Workspace} />
            <Route path="/agents" component={Agents} />
            <Route path="/runtime" component={RuntimeRoute} />
            <Route path="/context" component={ContextRoute} />
            <Route path="/capabilities" component={Capabilities} />
            <Route path="/semantic" component={Semantic} />
            <Route path="/diagnostics" component={Diagnostics} />
            <Route path="*404" component={StudioNotFound} />
          </Router>
        </StudioFailureBoundary>
      </StudioProvider>
    </I18nProvider>
  ),
  root,
);
