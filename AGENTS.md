# AGENT DIRECTIVES & RULES

## Core Constraints
1. DO NOT modify or refactor any existing code in `src/app/`, `src/lib/`, or configuration files (`next.config.ts`, `tsconfig.json`, `Dockerfile`) unless explicitly told.
2. ALL Chrome Extension code MUST be strictly contained inside a new root directory named `extension/`.
3. Do NOT install any new npm packages in the root project.
4. Keep the Chrome Extension simple, clean, and Manifest V3 compliant.

## Workflow Rules
- Read `TASK_SPEC.md` before writing code.
- Check progress against `TASK_SPEC.md` after each step.
- Stop and ask for clarification if an API endpoint contract is missing.
## Active Agent Skills
- Load and follow `.agent/skills/extension-testing.md` when building or modifying the `extension/` directory.
- Load and follow `.agent/skills/prompt-engineering.md` when touching `src/app/api/analyze/route.ts`[cite: 3].

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
