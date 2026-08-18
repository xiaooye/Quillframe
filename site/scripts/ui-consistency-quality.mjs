#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(here, "..");
const read = (relative) => fs.readFileSync(path.join(siteRoot, relative), "utf8");

const productShell = read("src/styles/product-shell.css");
const docsConfig = read("docs-site/astro.config.mjs");
const docsLanding = read("docs-site/src/components/DocsLanding.astro");
const docsPageTitle = read("docs-site/src/components/QuillframePageTitle.astro");
const docsSiteTitle = read("docs-site/src/components/QuillframeSiteTitle.astro");
const docsActions = read("docs-site/src/components/QuillframeActions.astro");
const docsShell = read("docs-site/src/styles/product-header-parity.css");
const docsNavigation = read("docs-site/src/styles/navigation-polish.css");
const docsArticle = read("docs-site/src/styles/article-polish.css");
const docsCustom = read("docs-site/src/styles/custom.css");

const legacyProduct = ["Novel", "Forge"].join("");
const legacyLower = legacyProduct.toLowerCase();
const legacyUpper = legacyProduct.toUpperCase();
const legacyWhyRoute = `why-${legacyLower}`;
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

/* Current Docs identity and destinations. Historical docs/specs are out of
 * scope here by design: this gate only inspects files that own current chrome. */
check(docsConfig.includes('title: "Quillframe"'), "current Starlight title must be Quillframe");
check(docsConfig.includes('site: "https://quillframe.wei-dev.com"'), "current Docs canonical site must use the Quillframe domain");
check(docsSiteTitle.includes("Quillframe") && !docsSiteTitle.includes(legacyProduct), "current Docs SiteTitle must expose only Quillframe identity");
check(docsLanding.includes('title: "Quillframe Documentation"') && docsLanding.includes('title: "Quillframe 文档中心"'), "Docs landing title must use Quillframe in both locales");
check(docsLanding.includes('primaryAction: "Why Quillframe"') && docsLanding.includes('primaryAction: "为什么选择 Quillframe"'), "Docs landing CTA must use Quillframe in both locales");
check(docsLanding.includes('"/docs/en/why-quillframe"') && docsLanding.includes('"/docs/why-quillframe"'), "Docs landing must target current why-quillframe routes");
check(![legacyProduct, legacyLower, legacyUpper, legacyWhyRoute].some((token) => docsLanding.includes(token)), "current Docs landing must not retain stale product identity or route slugs");
check(docsPageTitle.includes('"why-quillframe"') && !docsPageTitle.includes(legacyWhyRoute), "Docs route-aware PageTitle must classify the current why-quillframe slug");
check(docsActions.includes('https://github.com/xiaooye/cn_webnovel_agent'), "current Docs GitHub entry must target the canonical repository");
check(docsActions.includes('https://studio.quillframe.wei-dev.com'), "current Docs Studio entry must target the current Quillframe Studio destination");
check(!docsActions.toLowerCase().includes(`studio.${legacyLower}`) && !docsActions.toLowerCase().includes(`github.com/xiaooye/${legacyLower}`), "current Docs actions must not retain stale product destinations");
check(docsActions.includes("Quillframe product navigation") && !docsActions.includes(`${legacyProduct} product navigation`), "current Docs navigation aria identity must be Quillframe");

/* Product foreground ownership. */
for (const token of ["--pe-nav-foreground", "--pe-nav-active", "--pe-link-foreground", "--pe-link-hover"]) {
  check(productShell.includes(token), `ProductShell semantic foreground token missing ${token}`);
}
check(productShell.includes(".desktop-nav .wui-app-bar__link") && productShell.includes("color: var(--pe-nav-foreground)"), "Product desktop navigation must own its normal foreground");
check(productShell.includes(".mobile-nav .wui-sidebar__item") && productShell.includes("min-block-size: 44px"), "Product mobile navigation must retain semantic foreground ownership and 44px touch targets");
check(productShell.includes("color: var(--pe-nav-active)"), "Product active navigation must use the semantic active foreground");
check(productShell.includes("color: var(--pe-link-foreground)"), "Product footer links must use the semantic link foreground");
check(productShell.includes(".wui-app-bar__link > span") && productShell.includes("color: inherit"), "Product navigation icon spans must inherit the owning link foreground");

/* Docs foreground ownership: header shell, reading navigation, and article
 * links each keep their own semantic role rather than leaking decorative color. */
for (const token of ["--qf-nav-foreground", "--qf-nav-active", "--qf-action-foreground", "--qf-link-hover"]) {
  check(docsShell.includes(token), `Docs shell semantic foreground token missing ${token}`);
}
check(docsShell.includes(".nf-product-link") && docsShell.includes("color: var(--qf-nav-foreground)"), "Docs product navigation must own its normal foreground");
check(docsShell.includes("color: var(--qf-nav-active)"), "Docs active navigation must use the semantic active foreground");
check(docsShell.includes("color: var(--qf-action-foreground)"), "Docs Studio CTA must own its action foreground");
check(docsShell.includes(".nf-github-link span") && docsShell.includes("color: inherit"), "Docs GitHub arrow span must inherit anchor foreground across hover/focus states");
check(docsShell.includes(".nf-studio-link > span"), "Docs CTA icon span must inherit its semantic parent action color");
check(docsNavigation.includes('.right-sidebar a[aria-current="true"]') && docsNavigation.includes('.sidebar-content li > a[aria-current="page"]'), "Docs sidebar and TOC must retain explicit active-state owners");
check(docsArticle.includes(".right-sidebar") && docsArticle.includes(".pagination-links"), "Docs article chrome must retain explicit TOC and pagination styling owners");
check(docsCustom.includes(".sl-markdown-content a:not([class])"), "Docs inline article links must retain an explicit content-link owner");

/* Destructive global patches are forbidden in the modified semantic owners. */
for (const [name, css] of [["ProductShell", productShell], ["Docs shell", docsShell]]) {
  check(!/(^|\n)\s*a\s*\{[^}]*\bcolor\s*:/m.test(css), `${name} must not add a bare global a color override`);
  check(!/(^|\n)\s*span\s*\{[^}]*\bcolor\s*:/m.test(css), `${name} must not add a bare global span color override`);
  check(!css.includes("!important"), `${name} must not use !important`);
}

if (failures.length) {
  for (const failure of failures) console.error(`ui-consistency-quality: FAIL: ${failure}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    schema: "quillframe_ui_consistency_quality_v1",
    status: "pass",
    docs_current_identity: "Quillframe",
    github: "https://github.com/xiaooye/cn_webnovel_agent",
    studio: "https://studio.quillframe.wei-dev.com",
    stale_current_identity: false,
    product_semantic_foreground_owner: "product-shell.css",
    docs_semantic_foreground_owner: "product-header-parity.css",
    nested_span_inheritance: true,
    destructive_global_anchor_override: false,
    destructive_global_span_override: false,
    important_overrides: false,
    mobile_touch_target_px: 44,
  }, null, 2));
}
