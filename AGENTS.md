# AGENTS.md

This file configures OpenCode's agent behavior for this project. It tells the agent to check for and use the skills in `skills/` automatically, without needing slash commands or manual invocation.

## Skill-Driven Execution Model

This project uses a **skill-driven execution model** powered by the `skill` tool and the `skills/` directory at project root.

### Core Rules

- If a task matches a skill, invoke it.
- Skills are located in `skills/<skill-name>/SKILL.md`.
- Do not implement directly if a relevant skill applies — follow its workflow.
- Follow skill instructions exactly; do not partially apply them.
- The user does not need to request a skill by name — match on intent every message.

### Intent → Skill Mapping

- Underspecified request → `interview-me`
- Vague idea needing exploration → `idea-refine`
- New feature / significant change → `spec-driven-development`, then `planning-and-task-breakdown`
- Implementing code → `incremental-implementation`, `test-driven-development`
- UI or visual work → `frontend-ui-engineering` (architecture, accessibility, state) AND `ui-ux-design` (typography, color, spacing, layout) — apply both together
- API / interface design → `api-and-interface-design`
- Loading project context / session start → `context-engineering`
- Verifying against official docs → `source-driven-development`
- High-stakes or unfamiliar-code decisions → `doubt-driven-development`
- Browser-based debugging → `browser-testing-with-devtools`
- Bug / failure / unexpected behavior → `debugging-and-error-recovery`
- Before merging code → `code-review-and-quality`
- Code works but is messy → `code-simplification`
- Handling input, auth, secrets, integrations → `security-and-hardening`
- Performance concerns → `performance-optimization`
- Any code change → `git-workflow-and-versioning`
- Build/deploy pipeline changes → `ci-cd-and-automation`
- Removing old code / migrating → `deprecation-and-migration`
- Architectural decisions / API changes → `documentation-and-adrs`
- Adding telemetry / shipping to production → `observability-and-instrumentation`
- Preparing to deploy → `shipping-and-launch`
- Not sure which skill applies → `using-agent-skills`

### Lifecycle Mapping

For larger pieces of work, follow this phase order:

1. DEFINE → `interview-me` / `idea-refine` / `spec-driven-development`
2. PLAN → `planning-and-task-breakdown`
3. BUILD → `incremental-implementation`, `test-driven-development`, `frontend-ui-engineering`, `ui-ux-design`, `api-and-interface-design`
4. VERIFY → `browser-testing-with-devtools`, `debugging-and-error-recovery`
5. REVIEW → `code-review-and-quality`, `code-simplification`, `security-and-hardening`, `performance-optimization`
6. SHIP → `git-workflow-and-versioning`, `ci-cd-and-automation`, `documentation-and-adrs`, `observability-and-instrumentation`, `shipping-and-launch`

### Execution Model

For every request:

1. Determine if any skill applies, even partially.
2. Invoke the matching skill(s) using the `skill` tool.
3. Follow the skill workflow — don't skip steps like tests, review, or accessibility checks because the task "seems small."
4. For multi-part requests, multiple skills may apply in the same turn (e.g. a new UI feature may invoke `spec-driven-development`, `frontend-ui-engineering`, `ui-ux-design`, and `test-driven-development` together).

### Anti-Rationalization

These excuses are not valid reasons to skip a skill:

- "This is too small for a skill."
- "I can just quickly implement this."
- "I'll add tests/accessibility/review later."

Correct behavior: check for and apply relevant skills first, every time.

## Available Skills

All skills live under `skills/<skill-name>/SKILL.md`:

`api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`, `code-review-and-quality`, `code-simplification`, `context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`, `doubt-driven-development`, `frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`, `interview-me`, `observability-and-instrumentation`, `performance-optimization`, `planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`, `source-driven-development`, `spec-driven-development`, `test-driven-development`, `ui-ux-design`, `using-agent-skills`
