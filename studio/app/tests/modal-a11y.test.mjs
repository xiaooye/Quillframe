import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const sourcePath = new URL("../src/modalA11y.ts", import.meta.url);
const sourceExists = fs.existsSync(sourcePath);
const appShell = fs.readFileSync(new URL("../src/AppShell.tsx", import.meta.url), "utf8");
const review = fs.readFileSync(new URL("../src/routes/Review.tsx", import.meta.url), "utf8");
const resilience = fs.readFileSync(new URL("../src/StudioResilience.tsx", import.meta.url), "utf8");

async function loadModal() {
  assert.equal(sourceExists, true, "modalA11y.ts must exist before behavior can be verified");
  const source = fs.readFileSync(sourcePath, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString("base64")}`);
}

class FakeElement {
  constructor(name, { tabIndex = 0, disabled = false, hidden = false } = {}) {
    this.name = name;
    this.tabIndex = tabIndex;
    this.disabled = disabled;
    this.hidden = hidden;
    this.isConnected = true;
    this.inert = false;
    this.attributes = new Map();
    this.children = [];
    this.parentElement = null;
    this.focusCount = 0;
  }
  focus() { this.focusCount += 1; globalThis.document.activeElement = this; }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  hasAttribute(name) { return this.attributes.has(name); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); }
  querySelectorAll() { return this.children; }
  contains(candidate) { return candidate === this || this.children.includes(candidate); }
}

function setupDom() {
  const background = new FakeElement("app");
  const dialog = new FakeElement("dialog", { tabIndex: -1 });
  const first = new FakeElement("first");
  const second = new FakeElement("second");
  dialog.children = [first, second];
  const opener = new FakeElement("opener");
  const fallback = new FakeElement("fallback");
  globalThis.document = {
    activeElement: opener,
    getElementById(id) { return id === "app" ? background : undefined; },
    querySelector() { return fallback; },
  };
  return { background, dialog, first, second, opener, fallback };
}

function key(key, shiftKey = false) {
  let prevented = false;
  let stopped = false;
  return {
    key,
    shiftKey,
    preventDefault() { prevented = true; },
    stopPropagation() { stopped = true; },
    get prevented() { return prevented; },
    get stopped() { return stopped; },
  };
}

test("Studio modal source owns Portal, inert background, and generation-safe keyboard lifecycle", () => {
  assert.match(fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, "utf8") : "", /export function createModalA11y/);
  assert.match(fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, "utf8") : "", /aria-hidden/);
  assert.match(appShell, /from "\.\/modalA11y"/);
  assert.match(appShell, /<Portal>/);
  assert.match(appShell, /onMouseDown=\{\(event\) => paletteA11y\.onOutsidePointer\(event\)\}/);
  assert.match(review, /acceptCancelButton/);
  assert.match(resilience, /tabIndex=\{-1\}/);
});

test("Tab and Shift+Tab wrap within the custom dialog", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose() {}, getInitialFocus: () => dom.first });
  controller.open(dom.opener);
  await new Promise(queueMicrotask);

  dom.first.focus();
  const forward = key("Tab");
  controller.onKeyDown(forward);
  assert.equal(forward.prevented, true);
  assert.equal(globalThis.document.activeElement, dom.second);

  const wrappedForward = key("Tab");
  controller.onKeyDown(wrappedForward);
  assert.equal(globalThis.document.activeElement, dom.first);

  const wrappedBackward = key("Tab", true);
  controller.onKeyDown(wrappedBackward);
  assert.equal(globalThis.document.activeElement, dom.second);
});

test("Escape closes once, outside click closes only on the backdrop, and focus returns to the opener", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  let closes = 0;
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose: () => { closes += 1; }, getInitialFocus: () => dom.first, getFallbackFocus: () => dom.fallback });
  controller.open(dom.opener);
  await new Promise(queueMicrotask);
  const escape = key("Escape");
  controller.onKeyDown(escape);
  assert.equal(escape.prevented, true);
  assert.equal(escape.stopped, true);
  assert.equal(closes, 1);
  await new Promise(queueMicrotask);
  assert.equal(globalThis.document.activeElement, dom.opener);

  controller.open(dom.opener);
  await new Promise(queueMicrotask);
  controller.onOutsidePointer({ target: dom.second, currentTarget: dom.dialog });
  assert.equal(closes, 1);
  controller.onOutsidePointer({ target: dom.dialog, currentTarget: dom.dialog });
  assert.equal(closes, 2);
  controller.close();
});

test("stale close generation cannot steal focus after a fresh open", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  const nextOpener = new FakeElement("next-opener");
  let closes = 0;
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose: () => { closes += 1; }, getInitialFocus: () => dom.first, getFallbackFocus: () => dom.fallback });
  controller.open(dom.opener);
  controller.close();
  controller.open(nextOpener);
  await new Promise(queueMicrotask);
  assert.equal(closes, 1);
  assert.notEqual(globalThis.document.activeElement, dom.opener);
  assert.equal(globalThis.document.activeElement, dom.first);
});

test("a dialog with no tabbable children receives programmatic focus", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  dom.dialog.children = [];
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose() {} });
  controller.open(dom.opener);
  await new Promise(queueMicrotask);
  assert.equal(globalThis.document.activeElement, dom.dialog);
  const tab = key("Tab");
  controller.onKeyDown(tab);
  assert.equal(tab.prevented, true);
  assert.equal(globalThis.document.activeElement, dom.dialog);
});

test("background state is restored exactly and unusable openers use the fallback", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  dom.background.inert = true;
  dom.background.setAttribute("aria-hidden", "false");
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose() {}, getInitialFocus: () => dom.first, getFallbackFocus: () => dom.fallback });
  for (const unusable of ["disconnected", "disabled", "inert"]) {
    controller.open(dom.opener);
    await new Promise(queueMicrotask);
    if (unusable === "disconnected") dom.opener.isConnected = false;
    if (unusable === "disabled") dom.opener.disabled = true;
    if (unusable === "inert") dom.opener.inert = true;
    controller.close();
    await new Promise(queueMicrotask);
    assert.equal(globalThis.document.activeElement, dom.fallback, unusable);
    dom.opener.isConnected = true;
    dom.opener.disabled = false;
    dom.opener.inert = false;
    assert.equal(dom.background.inert, true, unusable);
    assert.equal(dom.background.getAttribute("aria-hidden"), "false", unusable);
  }
});

test("missing inert support fails closed instead of exposing a non-modal surface", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  delete dom.background.inert;
  const controller = modal.createModalA11y({ getDialog: () => dom.dialog, getBackground: () => dom.background, requestClose() {} });
  assert.throws(() => controller.open(dom.opener), (error) => error.code === "modal_inert_unsupported");
});

test("a missing dynamically rendered dialog restores the app instead of leaving it inert", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  let closes = 0;
  const controller = modal.createModalA11y({
    getDialog: () => undefined,
    getBackground: () => dom.background,
    requestClose: () => { closes += 1; },
  });

  controller.open(dom.opener);
  assert.equal(dom.background.inert, true);
  await new Promise(queueMicrotask);

  assert.equal(controller.isOpen(), false);
  assert.equal(dom.background.inert, false);
  assert.equal(dom.background.hasAttribute("aria-hidden"), false);
  assert.equal(closes, 1);
});

test("tab stops under hidden, aria-hidden, or inert ancestors are excluded", async () => {
  const modal = await loadModal();
  const dom = setupDom();
  const hiddenParent = new FakeElement("hidden-parent", { hidden: true });
  const ariaParent = new FakeElement("aria-parent");
  ariaParent.setAttribute("aria-hidden", "true");
  const inertParent = new FakeElement("inert-parent");
  inertParent.inert = true;
  const hiddenChild = new FakeElement("hidden-child");
  const ariaChild = new FakeElement("aria-child");
  const inertChild = new FakeElement("inert-child");
  hiddenChild.parentElement = hiddenParent;
  ariaChild.parentElement = ariaParent;
  inertChild.parentElement = inertParent;
  hiddenParent.parentElement = dom.dialog;
  ariaParent.parentElement = dom.dialog;
  inertParent.parentElement = dom.dialog;
  dom.first.parentElement = dom.dialog;
  dom.dialog.children = [hiddenChild, ariaChild, inertChild, dom.first];

  assert.deepEqual(modal.collectTabStops(dom.dialog), [dom.first]);
});
