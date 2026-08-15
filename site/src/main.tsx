import "./appearance-v5";
import { render } from "solid-js/web";
import ProductApp from "./ProductApp";
import { ProductFailureBoundary, ProductNotFound } from "./ProductResilience";
import "./styles/index.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

const productRoutes = new Set([
  "/",
  "/start",
  "/product",
  "/studio",
  "/architecture",
  "/publication",
  "/inspect",
  "/playground",
  "/agents",
  "/changelog",
]);

function normalizedPath() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path || "/";
}

render(() => (
  <ProductFailureBoundary>
    {productRoutes.has(normalizedPath()) ? <ProductApp /> : <ProductNotFound />}
  </ProductFailureBoundary>
), root);
