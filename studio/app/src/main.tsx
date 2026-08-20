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
const Manuscript = lazy(() => import("./routes/Manuscript"));
const Plan = lazy(() => import("./routes/Plan"));
const Story = lazy(() => import("./routes/Story"));
const Review = lazy(() => import("./routes/Review"));
const Research = lazy(() => import("./routes/Research"));
const Learning = lazy(() => import("./routes/Learning"));
const Architecture = lazy(() => import("./routes/Architecture"));
const Publication = lazy(() => import("./routes/Publication"));
const Workspace = lazy(() => import("./routes/Workspace"));
const Agents = lazy(() => import("./routes/Agents"));
const RuntimeRoute = lazy(() => import("./routes/Runtime"));
const ContextRoute = lazy(() => import("./routes/Context"));
const Capabilities = lazy(() => import("./routes/Capabilities"));
const Semantic = lazy(() => import("./routes/Semantic"));
const Diagnostics = lazy(() => import("./routes/Diagnostics"));
const Settings = lazy(() => import("./routes/Settings"));

const root = document.getElementById("app");
if (!root) throw new Error("#app mount point is missing");

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";
document.documentElement.dataset.productLanguage = "quillframe-kawaii-v1";
document.documentElement.dataset.writerMode = "authoring-first-v1";

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
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined);
  }, { once: true });
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
            <Route path="/manuscript" component={Manuscript} />
            <Route path="/plan" component={Plan} />
            <Route path="/story" component={Story} />
            <Route path="/review" component={Review} />
            <Route path="/research" component={Research} />
            <Route path="/learning" component={Learning} />
            <Route path="/publication" component={Publication} />
            <Route path="/architecture" component={Architecture} />
            <Route path="/workspace" component={Workspace} />
            <Route path="/agents" component={Agents} />
            <Route path="/runtime" component={RuntimeRoute} />
            <Route path="/context" component={ContextRoute} />
            <Route path="/capabilities" component={Capabilities} />
            <Route path="/semantic" component={Semantic} />
            <Route path="/diagnostics" component={Diagnostics} />
            <Route path="/settings" component={Settings} />
            <Route path="*404" component={StudioNotFound} />
          </Router>
        </StudioFailureBoundary>
      </StudioProvider>
    </I18nProvider>
  ),
  root,
);
