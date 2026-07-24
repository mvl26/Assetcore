import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default [
  { ignores: ['dist/**', 'node_modules/**', 'public/**', '*.config.js', '*.config.ts'] },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'],

  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
    },
  },

  {
    // Script build/dev chạy bằng Node, KHÔNG phải trình duyệt → global khác hẳn.
    files: ['scripts/**/*.{js,mjs,cjs}'],
    languageOptions: {
      globals: {
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        Buffer: 'readonly',
      },
    },
  },

  {
    languageOptions: {
      globals: {
        // Browser
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        FormData: 'readonly',
        File: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
        Image: 'readonly',
        Event: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLImageElement: 'readonly',
        HTMLVideoElement: 'readonly',
        MouseEvent: 'readonly',
        KeyboardEvent: 'readonly',
        DragEvent: 'readonly',
        Element: 'readonly',
        Node: 'readonly',
        confirm: 'readonly',
        alert: 'readonly',
        prompt: 'readonly',
        navigator: 'readonly',
        location: 'readonly',
        history: 'readonly',
      },
    },
    rules: {
      // ── TypeScript ────────────────────────────────────────────────────────
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
      }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-empty-function': 'off',
      '@typescript-eslint/ban-ts-comment': 'warn',

      // ── Vue ───────────────────────────────────────────────────────────────
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'warn',
      'vue/html-self-closing': ['warn', {
        html: { void: 'any', normal: 'any', component: 'always' },
      }],
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/attributes-order': 'warn',
      // Repo truyền CONTEXT của composable xuống làm prop (vd `ctx: ImportWizardCtx`
      // = object chứa ref). Ghi `ctx.someRef.value = x` là mutate GIÁ TRỊ của ref,
      // KHÔNG phải gán đè prop → không phải anti-pattern. `shallowOnly` giữ rule
      // bắt đúng lỗi thật (gán đè chính prop) mà bỏ false-positive này.
      'vue/no-mutating-props': ['error', { shallowOnly: true }],

      // ── Style / safety ────────────────────────────────────────────────────
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'warn',
      'prefer-const': 'warn',
      'no-var': 'error',
      'eqeqeq': ['warn', 'smart'],
    },
  },
]
