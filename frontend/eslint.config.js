// Lint rules for the frontend.
//
// This exists because of one specific bug. A variable was renamed, one place
// that used it was missed, and `npm run build` was perfectly happy: Vite
// bundles each file on its own and never asks whether a name actually exists.
// The app built, deployed, and rendered a blank white page. Nothing in the
// build output hinted at it.
//
// `no-undef` catches exactly that, in about a second. Run it before you build:
//
//     npm run lint
//
// The rules of hooks are here for the same reason - the bugs they catch
// (a hook behind an if, a stale value captured in a dependency list) show up
// as the app quietly doing the wrong thing rather than as an error.

import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  { ignores: ['dist/**', '../backend/frontend_dist/**', 'node_modules/**'] },

  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2021 },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...js.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,

      // The one that would have caught the blank page.
      'no-undef': 'error',

      // An unused import is usually a leftover from a rename - the same kind
      // of edit that produced the bug above.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^[A-Z]' }],

      // Deliberate in this codebase: several catch blocks swallow a failure on
      // purpose (storage blocked in private browsing, a cancelled request),
      // and each one says so in a comment.
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
];
