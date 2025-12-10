import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: {
        compatibility: {
          componentApi: 4,
        },
      },
    }),
  ],
  root: ".", // run from frontend/ by default
  // Use relative base so assets resolve on GitHub Pages and local file:// previews
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false, // disable source maps to avoid extra requests on GitHub Pages / file:// previews
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
