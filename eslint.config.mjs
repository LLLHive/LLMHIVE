import nextConfig from "eslint-config-next"

/** Ignore Python venvs and other non-app trees so `npm run lint` stays scoped to the product. */
const ignorePatterns = [
  "**/.venv/**",
  "**/venv/**",
  "llmhive/.venv/**",
  "benchmark_reports/**",
  "artifacts/**",
]

/**
 * Next.js 16 enables strict React Compiler hook rules that flag many established patterns
 * (effects that hydrate state, impure render helpers in admin tooling, Playwright fixture `use`, etc.).
 * We keep them off for CI until those call sites are refactored incrementally.
 */
const relaxedReactCompilerRules = {
  "react-hooks/set-state-in-effect": "off",
  "react-hooks/purity": "off",
  "react-hooks/immutability": "off",
}

/** @type {import("eslint").Linter.Config[]} */
const eslintConfig = [
  { ignores: ignorePatterns },
  ...nextConfig,
  {
    rules: {
      ...relaxedReactCompilerRules,
    },
  },
]

export default eslintConfig
