import vue from "rollup-plugin-vue";
import css from "rollup-plugin-css-only";
import { nodeResolve } from "@rollup/plugin-node-resolve";

export default [
  {
    input: "src/index.js",
    output: {
      file: "../static/vue/vueui.js",
      sourcemap: "inline",
      name: "VueUI",
      format: "iife",
    },
    plugins: [
      vue({css: true, compileTemplate: true}),
      css(),
      nodeResolve({browser: true})
    ],
  },
];
