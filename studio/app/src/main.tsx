import { lazy } from "solid-js";
import { render } from "solid-js/web";
import { Route, Router } from "@solidjs/router";
import { AppShell } from "./AppShell";
import { bridgeTransportAvailable } from "./bridge";
import { I18nProvider } from "./i18n";
import { StudioProvider } from "./studio";
import "./styles/vendor/weiui.tokens.generated.css";
import "./styles/vendor/weiui.generated.css";
import "../../../assets/brand/story-loom.weiui.css";
import "./styles/app.css";
import "./styles/observability.css";
import "./styles/host.css";
import "./styles/atelier-workbench.css";
import "./styles/visual-fixes.css";
import "./styles/product-surfaces.css";
import "./styles/onboarding.css";
import "./styles/integrations.css";

const Desk = lazy(() => import("./routes/Desk"));
const Start = lazy(() => import("./routes/Start"));
const Project = lazy(() => import("./routes/Project"));
const Workspace = lazy(() => import("./routes/Workspace"));
const Agents = lazy(() => import("./routes/Agents"));
const ContextRoute = lazy(() => import("./routes/Context"));
const Capabilities = lazy(() => import("./routes/Capabilities"));
const Semantic = lazy(() => import("./routes/Semantic"));
const Diagnostics = lazy(() => import("./routes/Diagnostics"));

const root = document.getElementById("app");
if (!root) throw new Error("#app mount point is missing");

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";

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

void configureOfflineShell();

render(
  () => (
    <I18nProvider>
      <StudioProvider>
        <Router root={AppShell}>
          <Route path="/" component={Desk} />
          <Route path="/start" component={Start} />
          <Route path="/project" component={Project} />
          <Route path="/workspace" component={Workspace} />
          <Route path="/agents" component={Agents} />
          <Route path="/context" component={ContextRoute} />
          <Route path="/capabilities" component={Capabilities} />
          <Route path="/semantic" component={Semantic} />
          <Route path="/diagnostics" component={Diagnostics} />
        </Router>
      </StudioProvider>
    </I18nProvider>
  ),
  root,
);
