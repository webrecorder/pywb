import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";

export default [
  js.configs.recommended,
  ...pluginVue.configs["flat/essential"],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: globals.browser
    },
    rules: {
      "no-restricted-globals": [
        2,
        "event", "error"
      ],
      "indent": [
        "error",
        2
      ],
      "linebreak-style": [
        "error",
        "unix"
      ],
      "quotes": [
        "error",
        "double"
      ],
      "semi": [
        "error",
        "always"
      ]
    }
  }
];
