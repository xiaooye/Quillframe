import "./appearance-v5";
import { render } from "solid-js/web";
import ProductApp from "./ProductApp";
import "./styles/index.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

render(() => <ProductApp />, root);
