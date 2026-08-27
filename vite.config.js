import { resolve } from 'node:path';

import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// GitHub Pages serves a project site under /<repo>/, so every asset URL has to
// carry that prefix — and the same build has to work from a file server at the
// root during development. `base` does both: vite rewrites the URLs it owns,
// and `import.meta.env.BASE_URL` covers the two we fetch by hand.
//
// Built into docs/ rather than dist/ because Pages can serve that folder off
// the default branch directly, with no workflow and no second branch to keep.
export default defineConfig({
  base: process.env.BASE_PATH ?? '/hs-map/',
  plugins: [svelte()],
  // Two pages, one build: the map and the codex are read separately and carry
  // different data, so they are separate documents rather than routes — nobody
  // reading the map should be made to download two thousand item icons first.
  build: {
    outDir: 'docs',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        map: resolve(import.meta.dirname, 'index.html'),
        codex: resolve(import.meta.dirname, 'codex.html'),
      },
    },
  },
  server: { port: 5180, strictPort: true },
});
