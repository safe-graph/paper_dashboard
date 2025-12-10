import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {
    compatibility: {
      componentApi: 4, // allow new App(...) style for Svelte 5
    },
  },
};
