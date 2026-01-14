import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';

/** @type {import('eslint').Linter.Config[]} */
export default [
  js.configs.recommended,
  ...svelte.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  {
    rules: {
      // Code quality
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],

      // Style (let Prettier handle most formatting)
      'semi': ['error', 'always'],
      'quotes': ['error', 'single', { avoidEscape: true }],

      // Best practices
      'eqeqeq': ['error', 'always'],
      'no-var': 'error',
      'prefer-const': 'warn',
      'prefer-template': 'warn',
    },
  },
  {
    ignores: [
      'dist/',
      'build/',
      'node_modules/',
      'src-tauri/',
    ],
  },
];
