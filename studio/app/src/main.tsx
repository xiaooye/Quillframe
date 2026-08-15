import { lazy } from "solid-js";
import { render } from "solid-js/web";
import { Route, Router } from "@solidjs/router";
import { AppShell } from "./AppShell";
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

const Desk = lazy(() => import("./routes/Desk"));
const Project = lazy(() => import("./routes/Project"));
const Workspace = lazy(() => import("./routes/Workspace"));
const ContextRoute = lazy(() => import("./routes/Context"));
const Capabilities = lazy(() => import("./routes/Capabilities"));
const Semantic = lazy(() => import("./routes/Semantic"));
const Diagnostics = lazy(() => import("./routes/Diagnostics"));

const root = document.getElementById("app");
if (!root) throw new Error("#app mount point is missing");

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";

render(
  () => (
    <I18nProvider>
      <StudioProvider>
        <Router root={AppShell}>
          <Route path="/" component={Desk} />
          <Route path="/project" component={Project} />
          <Route path="/workspace" component={Workspace} />
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
