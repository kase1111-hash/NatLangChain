module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: ['svelte'],
  overrides: [
    {
      files: ['*.svelte'],
      processor: 'svelte/svelte',
      extends: ['plugin:svelte/recommended'],
    },
  ],
  rules: {
    // Code quality
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': ['warn', { allow: ['warn', 'error'] }],

    // Style (let Prettier handle most formatting)
    'semi': ['error', 'always'],
    'quotes': ['error', 'single', { avoidEscape: true }],

    // Best practices
    'eqeqeq': ['error', 'always'],
    'no-var': 'error',
    'prefer-const': 'warn',
    'prefer-template': 'warn',
  },
  ignorePatterns: [
    'dist/',
    'build/',
    'node_modules/',
    'src-tauri/',
  ],
};
