# Database Change Rules

This document defines the required workflow for any feature that adds, removes, or changes persistent data.

The goal is simple:
- new features that need database storage should be added through Django models and migrations
- schema changes should stay predictable and conflict-resistant
- future AI agents should have one clear workflow instead of guessing

## Source of Truth

- The database schema source of truth is:
  - Django models
  - Django migration files committed to the repository
- Do not treat manual database edits as the source of truth.
- Do not change production or local schemas manually and leave Django unaware of the change.
- If an emergency manual database fix is ever required, the next code change must add a matching migration so code and schema return to sync.

## Required Planning Before Any Persistent Feature

Before implementing a feature, decide whether it:
- adds new stored data
- changes an existing table or relationship
- needs seed data or backfilled data
- changes validation, uniqueness, or nullability rules

If the answer is yes to any of the above, the implementation must include the required model and migration work in the same task unless the user explicitly asks to defer it.

## Safe Schema Design Rules

- Prefer additive, backward-compatible schema changes first.
- Avoid destructive changes unless the user explicitly approves them.
- Do not remove or rename columns that active code may still depend on.
- When adding a field to an existing model, prefer one of these safe paths:
  - add it as nullable or blank first, then backfill, then tighten constraints later
  - add it with a safe default that preserves existing rows
- When changing data shape for existing rows, use a data migration instead of relying on manual SQL edits.
- Keep role metadata, dashboard routing data, and other configurable business data in models/tables rather than hardcoding it in views or templates.

## Migration Workflow

For any model or persistence change, follow this order:

1. Update the Django models and related application code.
2. Run `python manage.py makemigrations <app_label>` or `python manage.py makemigrations`.
3. Inspect the generated migration before accepting it.
4. If existing rows need values transformed or seeded, add a data migration.
5. Run `python manage.py migrate`.
6. Run `python manage.py makemigrations --check --dry-run`.
7. Run `python manage.py check`.
8. Run tests relevant to the changed behavior.

Do not report a database-related task as complete until the migration state is verified clean.

## Migration Quality Rules

- Keep migrations small and focused on one logical change set where practical.
- Use clear migration names when a change is meaningful enough to deserve one.
- Do not edit old migrations that may already be applied on another machine unless the user explicitly approves a repair strategy.
- Do not delete committed migrations just to make conflicts disappear.
- Do not use `--fake` or `--fake-initial` unless the user explicitly approves it and the reason is documented in the final summary.

## Conflict Prevention Rules

- If two branches create migrations in the same app, resolve the conflict with a proper merge migration or by regenerating the unapplied local migration safely.
- If Django reports multiple leaf nodes, inspect the migration graph and resolve it intentionally instead of deleting files blindly.
- Never overwrite another developer's migration without understanding whether it has already been applied elsewhere.
- When a change is risky, prefer a two-step rollout:
  - deploy additive schema support first
  - migrate data
  - remove old fields or constraints later in a separate task

## Data Migration Rules

- Use data migrations for:
  - seeding required reference data
  - backfilling new non-null fields
  - converting old values into a new format
- Data migrations must be deterministic and repeatable.
- Do not depend on temporary local state, browser actions, or manual admin edits to make migrations succeed.

## Verification Standard

When models, migrations, or DB configuration change, verify all applicable steps:
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate`
- relevant tests
- database-specific checks when constraints, indexes, or seed data are involved

## AI Agent Rule

Any future AI agent working in this repository must assume:
- a feature is not complete if it needs persistent data but no schema plan exists
- Django models and migrations must stay in sync
- conflict avoidance is part of the implementation, not a cleanup task for later
- database changes should be explicit, reviewed, and verified in the same task whenever safely possible
