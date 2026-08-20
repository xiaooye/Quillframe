import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const siteRead = (relative) => fs.readFileSync(new URL(`../${relative}`, import.meta.url), "utf8");
const repoRead = (relative) => fs.readFileSync(new URL(`../../${relative}`, import.meta.url), "utf8");
const product = siteRead("src/ProductApp.tsx");
const productResilience = siteRead("src/ProductResilience.tsx");
const studioResilience = repoRead("studio/app/src/StudioResilience.tsx");
const appShell = repoRead("studio/app/src/AppShell.tsx");
const review = repoRead("studio/app/src/routes/Review.tsx");
const siteStyles = siteRead("src/styles/site.css");
const siteMain = siteRead("src/main.tsx");

test("all Product and Studio main targets are programmatically focusable skip-link destinations", () => {
  for (const [name, source] of [["Product shell", product], ["Product resilience", productResilience], ["Studio shell", appShell], ["Studio resilience", studioResilience]]) {
    assert.match(source, /id="main-content"[^>]*tabIndex=\{-1\}/, name);
  }
  assert.match(studioResilience, /function focusStudioMain/);
  assert.match(studioResilience, /target\.focus\(\{ preventScroll: true \}\)/);
  assert.match(studioResilience, /onClick=\{focusStudioMain\}/);
  assert.match(siteMain, /function installProductSkipLinkFocus/);
  assert.match(siteMain, /\.nf-skip-link\[href='#main-content'\]/);
  assert.match(siteMain, /target\.focus\(\{ preventScroll: true \}\)/);
});

test("native Product dialog has an explicit accessible name and return-focus contract", () => {
  assert.match(product, /showModal\(\)/);
  assert.match(product, /aria-modal="true"/);
  assert.match(product, /aria-labelledby="product-command-heading"/);
  assert.match(product, /class="wui-button wui-button--soft header-search"[^>]*aria-label=/);
  assert.match(product, /returnFocus|focus\(\)/);
  assert.match(product, /class="wui-input-group launcher-search"[\s\S]{0,240}window\.dispatchEvent\(new KeyboardEvent/);
  assert.doesNotMatch(product, /launcher-search"[\s\S]{0,240}document\.dispatchEvent\(new KeyboardEvent/);
});

test("Product header has a non-overflowing laptop compact state", () => {
  assert.match(siteStyles, /@media \(max-width: 1220px\) and \(min-width: 1081px\)/);
  assert.match(siteStyles, /\.header-search > span:not\(:first-child\)/);
  assert.match(siteStyles, /@media \(max-width: 1080px\)[\s\S]*?\.mobile-menu-button\s*\{\s*display: inline-flex;/);
});

test("Studio custom modals use the shared Portal controller and safe Accept alertdialog", () => {
  assert.match(appShell, /from "\.\/modalA11y"/);
  assert.match(appShell, /<Portal>/);
  assert.match(appShell, /onKeyDown=\{paletteA11y\.onKeyDown\}/);
  assert.match(review, /from "\.\.\/modalA11y"/);
  assert.match(review, /<Portal>/);
  assert.match(review, /role="alertdialog"[^>]*aria-modal="true"/);
  assert.match(review, /aria-describedby="accept-confirm-description"/);
  assert.match(review, /acceptCancelButton/);
  assert.doesNotMatch(review, /role="alertdialog"[^>]*aria-modal="false"/);
});
