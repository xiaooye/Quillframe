import { render } from "solid-js/web";
import App from "./App";
import "./styles/site.css";
import "./styles/showcase.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("NovelForge Product Site root element is missing");
}

render(() => <App />, root);
