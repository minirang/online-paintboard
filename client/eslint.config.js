import js from "@eslint/js";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
    {
        ignores: ["dist/**", "build/**", "node_modules/**"],
    },
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
        languageOptions: {
            globals: {
                ...globals.browser
            }
        },
        rules: {
            "semi": ["error", "always"],
            "@typescript-eslint/no-explicit-any": "warn",
            "no-console": "off",
            "@typescript-eslint/no-unused-vars": "warn",
            "no-case-declarations": "warn"
        }
    },
    {
        files: ["**/sw.js"],
        languageOptions: {
            globals: {
                ...globals.serviceworker
            }
        }
    }
);
