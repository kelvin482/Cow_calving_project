# AGENTS Instructions

These instructions apply to all prompts in this repository.

## Required Behavior
- Follow [TEAM_RULES.md](./TEAM_RULES.md) for every response and code change.
- Follow [ENGINEERING_INSTRUCTIONS.md](./ENGINEERING_INSTRUCTIONS.md) for implementation quality, roadmap flow, and verification standards.
- Follow [DATABASE_CHANGE_RULES.md](./DATABASE_CHANGE_RULES.md) whenever a feature adds, changes, seeds, or removes persistent data.
- Follow [docs/PROJECT_ROADMAP_AND_RULES.md](./docs/PROJECT_ROADMAP_AND_RULES.md) for the product goal, staged delivery plan, and project-specific AI/data rules.
- Do not invent APIs, packages, or behavior.
- If any requirement is ambiguous, ask concise clarification questions before risky implementation.

## Workflow Requirement
1. Build a short roadmap with small, ordered tasks.
2. Implement incrementally.
3. Validate each change with relevant checks.
4. Report only verified results.

## Minimum Validation
- Run syntax/static checks for changed files.
- Run framework health checks.
- Run tests relevant to changed behavior.
- Run migration/database checks when models or DB config change.

## Output Requirement
- Keep responses concise, clear, and non-repetitive.
- Separate confirmed facts from assumptions.
- Include exact changed file paths in summaries.
