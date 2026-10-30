import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Single-file output: index.html inlines JS + CSS so pywebview can load it
// via html=... with no asset resolution.
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
});
