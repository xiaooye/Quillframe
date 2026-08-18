import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import solid from "vite-plugin-solid";

const repositoryRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  plugins: [solid()],
  optimizeDeps: {
    exclude: ["pyodide"],
  },
  server: {
    fs: {
      allow: [repositoryRoot],
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
