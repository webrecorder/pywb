import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import cssInjectedByJs from "vite-plugin-css-injected-by-js";

export default defineConfig({
  plugins: [
    vue({
      template: {
        // keep whitespace between elements as Vue 2 did
        compilerOptions: { whitespace: "preserve" }
      }
    }),
    // inject component styles into the page from the bundle (see main() in
    // index.js), so that only vueui.js needs to be included by the templates
    cssInjectedByJs()
  ],
  define: {
    // library mode does not replace process.env, which the Vue
    // esm-bundler build relies on
    "process.env.NODE_ENV": JSON.stringify("production")
  },
  build: {
    outDir: "../static/vue",
    emptyOutDir: false,
    // no real minification, but escape non-ASCII characters, as some pages
    // that include vueui.js (e.g. frame_insert.html) do not declare a charset
    minify: true,
    cssMinify: false,
    rolldownOptions: {
      output: {
        minify: {
          compress: false,
          mangle: false,
          codegen: { removeWhitespace: false, asciiOnly: true }
        }
      }
    },
    lib: {
      entry: "src/index.js",
      name: "VueUI",
      formats: ["iife"],
      fileName: () => "vueui.js"
    }
  }
});
