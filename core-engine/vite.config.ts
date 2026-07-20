import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// Compila el motor como UNA librería auto-contenida (IIFE) que expone
// window.JarvisCoreEngine — así la UI actual (ui/index.html, sin build
// propio) lo consume con un simple <script src>. React, three.js y todo
// lo demás quedan empaquetados dentro.
export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.ts"),
      name: "JarvisCoreEngine",
      formats: ["iife"],
      fileName: () => "jarvis-core-engine.js",
    },
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    target: "es2020",
    chunkSizeWarningLimit: 2000,
  },
});
