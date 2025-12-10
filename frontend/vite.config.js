import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
  plugins: [svelte()],
  root: ".", // run from frontend/ by default
  // Use relative base so assets resolve on GitHub Pages and local file:// previews
  base: "./",
  build: {
    outDir: "../site",
    emptyOutDir: true,
    sourcemap: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
