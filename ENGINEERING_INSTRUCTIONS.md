# Engineering Instructions

## Role
Act as a senior software engineer.

## Non-Negotiable Rules
- Never hallucinate libraries, APIs, or features.
- Strictly follow all rules in this document and related instruction files.
- If uncertain, say so instead of guessing.
- Follow official best practices for the specified tech stack.
- Write clean, modular, production-quality code.
- Avoid hard-coded values; use configs or environment variables.
- Do not hardcode features or behaviors that are expected to change; use configuration and feature flags.
- Keep responses concise and avoid repetition.
- Ensure code sections do not conflict.
- Use consistent naming and clear structure.
- Write clean, readable code with clear, helpful comments where needed for understanding.
- Add concise comments around custom flows, security-sensitive logic, and non-obvious decisions; optimize comments for teammate understanding, not narration.
- Whenever behavior is changed, add or refresh concise comments around the updated non-obvious code so the current implementation remains easy to follow.
- For multi-role architecture, prefer role metadata/configuration and redirect maps over hardcoded per-role branching so new roles can be added safely later.
- Frontend and template work must be responsive by default and verified across small, medium, and large viewport layouts.
- For website and template UI work in this repository, use Tailwind CSS as the default styling system unless the user explicitly requests a different approach.
- For this hackathon project, optimize for a strong end-to-end demo: fewer polished flows, simpler interfaces, and clearly useful outcomes beat feature breadth.
- Ask clarification questions if requirements are unclear.
- Provide solutions that can run with minimal modification.
- Preserve project structure and conventions; do not move/rename files or modules unless explicitly requested.
- Focus on one task at a time and complete it before starting another.

## Additional Standards
- Prefer readability and maintainability over clever shortcuts.
- Keep functions/classes small and single-purpose.
- Validate inputs and handle failure paths explicitly.
- Do not expose secrets in code, logs, or commits.
- Preserve backward compatibility unless a breaking change is explicitly approved.
- Add or update tests for behavior changes.
- Document assumptions, tradeoffs, and known limitations.
- Use deterministic, repeatable setup and execution steps.
- Treat Django models and committed migrations as the database source of truth; use additive schema changes, data migrations, and deliberate conflict resolution instead of manual database drift.

## Roadmap-First Workflow
Always follow a roadmap and break work into small tasks.

1. Understand the request and constraints.
2. Confirm unclear requirements with focused questions.
3. Write a short implementation roadmap (small, ordered tasks).
4. Execute one task at a time.
5. Validate after each task.
6. Run final end-to-end checks.
7. Summarize what changed, what was verified, and any open risks.

## Hackathon Product Focus
- Default to one high-value workflow per page rather than many low-confidence cards or sections.
- Prefer working actions, realistic data flow, and community relevance over decorative or speculative features.
- Each page should answer one main user question and expose only the actions needed for that workflow.
- When choosing between multiple ideas, prioritize the one that is easiest to demo clearly and most likely to solve a real farmer or veterinary pain point.

## Error-Check Policy
Always check for errors before declaring completion.

Minimum checks:
- Static/syntax checks for touched files.
- Project health checks (framework-specific).
- Tests for changed behavior.
- Database/migration checks when models or persistence change.
- Config validation for environment-dependent features.

For Django projects, run as applicable:
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate`
- `python manage.py test`

## Database Evolution Workflow
- Follow [DATABASE_CHANGE_RULES.md](./DATABASE_CHANGE_RULES.md) for every model, migration, or persistence change.
- If a feature needs stored data, include the model and migration plan in the same task unless the user explicitly defers it.
- Prefer backward-compatible schema changes first:
  - add nullable/defaulted fields
  - backfill with a data migration if needed
  - tighten constraints later
- If migration conflicts appear, resolve them intentionally with the Django migration graph; do not delete committed migrations as a shortcut.

## Role Dashboard Blueprint
- Keep one shared public website and one shared authentication flow.
- Route authenticated users to dashboards based on stored role metadata, not template-only role labels.
- Start with two roles only for now: `farmer` and `veterinary`.
- Design the persistence layer so more roles can be added later without rewriting redirect logic.
- Use lowercase Django app package names for dashboards, for example `farmers_dashboard` and `veterinary_dashboard`.
- Record architecture decisions in [ROLE_DASHBOARD_BLUEPRINT.md](./ROLE_DASHBOARD_BLUEPRINT.md) before implementing new role-sensitive apps or redirects.

## Output Quality Bar
- Keep output structured and concise.
- Include exact file paths for changes.
- State what is confirmed vs assumed.
- Never claim a check passed unless it was actually run.
