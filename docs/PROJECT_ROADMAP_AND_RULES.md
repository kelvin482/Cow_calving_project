# Digital Farm Project Roadmap and Working Rules

This is the project-specific guide for building the AI-based livestock monitoring system in small, reviewable steps. It records the product goal, what the repository already contains, the planned order of work, and rules for deciding when a stage is complete.

This guide does not replace the repository-wide engineering or database rules. Follow `AGENTS.md`, `TEAM_RULES.md`, `ENGINEERING_INSTRUCTIONS.md`, and `DATABASE_CHANGE_RULES.md` as well. If this guide and a higher-level repository rule differ, follow the higher-level rule and update this guide when appropriate.

## Product Goal

Build on the existing Digital Farm Django application to help dairy farmers in Kenya:

1. Keep reliable records for their farms and individual animals.
2. Record milk production and understand how it changes over time.
3. Notice unusual production changes early and receive a clear, useful next step.
4. Manage relevant breeding, calving, feeding, and health information.
5. Contact veterinary or extension support when needed.

AI should support a farmer's decision. A milk-drop alert is a signal to investigate; it is not proof of illness or a veterinary diagnosis. Do not claim that a rule or forecast is reliable for real farms until it has been evaluated on suitable, representative real data.

## Confirmed Starting Point

The repository currently uses Django, Python, Django templates, HTML, CSS/Tailwind, JavaScript, PostgreSQL configuration, and an OpenRouter-backed AI advice service. The codebase already includes:

- Shared public pages, authentication, profiles, and database-backed `farmer` and `veterinary` roles.
- A `Cow` model owned by a farmer, cow registration, reproductive dates and status, reproductive events, and a calving tracker.
- Farmer-to-veterinary conversations, image attachments, and notifications stored in the database.
- A veterinary workspace whose patient and clinical-record screens contain demo data and are not yet backed by veterinary case models.
- An AI advice workspace. This is a question-and-answer feature, not a milk-yield prediction or anomaly-detection system.

At the initial review, the code did **not** include a milk-production record model or entry workflow. Stages 0–2 have since added morning/evening milk capture, calculated daily totals, and deterministic per-cow historical feature calculations. Older daily-total rows remain valid without invented session values. The code still does not include feeding or health record models, milk-drop alerts, or next-day milk estimates. No real historical milk dataset has been collected, so operational rule performance cannot yet be measured. The project stores farm details on a user profile rather than in a separate multi-farm model.

Treat this as a baseline from the initial review, not a permanent guarantee. Inspect the relevant code and Git status again before every implementation slice.

## Architecture Direction

Keep the existing Django application and extend it. Do not rebuild the project or add a second implementation of accounts, cows, dashboards, or AI advice.

- **User interface:** Existing Django templates and dashboard assets collect entries and show results.
- **Application logic:** Existing Django views and forms validate requests and enforce role and owner access. Put calculations and model inference in focused service modules when those responsibilities are introduced.
- **Database:** Django models and committed migrations remain the source of truth. Milk records should relate to the existing cow record; do not create a duplicate animal model.
- **Milk-drop workflow:** Compare today's calculated daily total with that cow's average over its previous seven recorded days using the proposal's 15% and 25% thresholds. This is a rule-based follow-up prompt, not a diagnosis; do not train a model for this workflow.
- **Prediction workflow:** A simple rule-based next-day estimate is a later, separate feature. Compare it with a previous-day baseline through chronological backtesting; do not train a model or mix forecasts into milk-drop alerts.
- **Existing AI advice:** Keep the current OpenRouter question-and-answer service separate from statistical milk models. Do not send health or production data to an external provider unless the user approves that data flow.

Enforce farmer ownership through the existing cow-to-owner relationship on every read and write. Do not trust a submitted cow ID by itself. If multi-farm management becomes necessary, plan a distinct Farm model and migration explicitly rather than treating a profile's farm-name string as a complete access-control system.

## Roadmap

Work on one stage at a time. Each stage has a completion gate; do not start the next stage until the current one is implemented, checked, and explained.

### Priority checklist

Use this short list to see what is important now. `[x]` means the work and its checks are complete; `[ ]` means it is still ahead. Keep the detailed scope and checks in the matching stage below.

| Priority | Task | Why it matters / alignment | Status |
|---|---|---|---|
| P0: Foundation | Reconcile Django migrations | Prevent new persistent features from building on an unclear database baseline. | [x] Migration reviewed and applied; Django check and all 20 `cow_calving_ai` tests passed. |
| P1: Core data | Record morning and evening milk per cow and calculate the daily total | Reliable production history is required for trends, rule-based alerts, and estimates. | [x] Farmer-owned entry, correction, duplicate/date/quantity validation, and legacy-total preservation. |
| P1: Data readiness | Collect and review milk records for coverage, gaps, duplicates, invalid values, and usable history | Avoid rules based on sparse or misleading data. Missing entries must not be treated as zero. | [ ] No real production history collected yet; operational rule evaluation waits for suitable history. |
| P1: Explainable foundation | Calculate and test historical production features | Provides understandable, time-safe inputs for monitoring and later estimates. | [x] Stage 2 formulas documented and implemented; 8 focused tests passed. |
| P1: Core outcome | Apply the proposal's 15%/25% milk-drop rules and give farmers a useful follow-up workflow | Delivers the early-warning goal without presenting a production change as a diagnosis. | [x] Rule, persisted alerts, farmer dashboard, cow trend, acknowledgement, and demo alert are implemented; six focused alert tests pass. |
| P1: Reliability | Verify the full milk-entry-to-alert flow, including access control and small, medium, and large screens | Ensures the main farmer workflow works end to end. | [ ] Automated farmer-dashboard and milk tests pass; manual responsive review and professional threshold review remain. |
| P2: Prediction | Add and chronologically evaluate a rule-based next-day estimate against a previous-day baseline | Adds a transparent estimate without model training. | [ ] Later; requires enough suitable real history for evaluation. |
| P3: Extensions | Add feeding, health, veterinary-case, or other farm records only when a confirmed workflow needs them | Supports the broader product goal while avoiding disconnected tables and unfinished screens. | [ ] Select one user need at a time after the core workflow. |
| P3: Release readiness | Prepare and verify deployment configuration and integrations | Makes the completed workflows safe and operable in the chosen deployment environment. | [ ] Near release. |

**Current focus:** Stages 0–2 are complete and checked. Start collecting real morning/evening milk records and review coverage. Rule tests can verify calculations on synthetic examples, but operational alert and forecast performance require suitable real records.

### Stage 0: Reconcile migration state — complete and tested

- **Purpose:** Start database work from a clean, understood migration baseline.
- **Resolved:** Added and applied `cow_calving_ai/migrations/0002_alter_calvingevent_options.py` to record the `CalvingEvent` model options without editing the initial migration. Django reports no further model changes.
- **Likely files:** A new migration in `cow_calving_ai/migrations/`. Inspect the model and migration graph first. Do not edit an old migration to hide the mismatch.
- **Complete when:** The intended migration is reviewed and `makemigrations --check --dry-run` no longer reports this existing change.
- **Checks:** `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --plan`, `python manage.py check`, and relevant AI-app tests. Applying a migration to a database is a separate operation and must be planned and reported.

### Stage 1: Implement proposal-aligned milk-record capture

- **Status:** Complete and tested. Farmers enter morning and evening amounts per cow and date; the daily total is calculated. Older daily-total rows are preserved with their session amounts left unknown.

- **Purpose:** Begin collecting the historical data required for trends and rule-based monitoring.
- **Dependencies:** The existing `farmers_dashboard.Cow` model, farmer role protection, cow-owner scoping, and the clean migration baseline.
- **Decision:** Follow the proposal's morning/evening format. Require both session values to save a new daily record; allow zero as an explicit measured value. Keep previous daily totals without fabricating a session split.
- **Likely files:** `farmers_dashboard/models.py`, `forms.py`, `views.py`, the milk-record template, a new farmers-dashboard migration, and `farmers_dashboard/tests.py`.
- **Complete when:** An authorized farmer can create and correct both session values for their own cow, see the calculated daily total, and cannot access another farmer's cow records. Invalid quantities, future dates, and duplicate daily records are rejected.
- **Checks:** Session sum and validation tests, duplicate/date/quantity validation tests, owner-isolation tests, migration review and checks, Django system check, and relevant farmer-dashboard tests.

### Stage 2: Calculate and explain historical features

- **Status:** Complete and tested. The approved baselines use the prior 7 and 30 calendar days, measured entries only, with minimum counts of 5 and 20 respectively. The 30-day deviation is in litres; days in milk uses the latest recorded calving event on or before the milk date and is unavailable without one.

- **Purpose:** Turn a cow's own production history into understandable inputs for monitoring and later estimates.
- **Dependencies:** Saved milk records with reliable dates and quantities from Stage 1.
- **Required features from the proposal:** Current day's yield; percentage change from the previous 7-day average; deviation from the previous 30-day average; standard deviation over the previous 7 days; and days in milk.
- **Decisions:** Windows are the preceding calendar days and exclude the current observation. Missing dates are not zero. Percentage change is `(current yield - previous 7-day mean) / previous 7-day mean * 100`; 30-day deviation is `current yield - previous 30-day mean` in litres; 7-day spread is population standard deviation in litres. At least 5 of the prior 7 days and 20 of the prior 30 days must have measurements. Percentage change is unavailable when its baseline is zero. Days in milk counts calving day as day 1 and uses the latest `calved` reproductive event no later than the record date; if none exists, it is unavailable. `expected_calving_date` is not used as an actual calving date.
- **Files:** `farmers_dashboard/milk_features.py` and `farmers_dashboard/test_milk_features.py`.
- **Complete when:** Each feature has a documented formula, source fields, and behavior for missing or insufficient history; calculations are deterministic and tested.
- **Checks:** Unit tests for known values, calendar-window boundaries, missing dates, zero baselines, insufficient history, other-cow isolation, and missing calving events. No model training is required in this stage.

### Stage 3: Implement the proposal's rule-based milk-drop calculation

- **Status:** Implemented in `farmers_dashboard/milk_alerts.py`; focused rule, correction, and dashboard tests pass. The proposal specifies the formula and initial thresholds; this workflow does not require model training.
- **Purpose:** Compare today's calculated daily total with that cow's mean over its previous seven recorded days.
- **Dependencies:** Stage 1 session-based records and the approved proposal thresholds.
- **Rules:** `drop_percent = (previous_seven_day_mean - today_total) / previous_seven_day_mean * 100`. A drop of 15% or less is Normal; above 15% through 25% is Warning; above 25% is Critical. Fewer than seven previous recorded daily totals is insufficient history. Do not treat missing dates as zero. The zero-baseline case must return an explicit unavailable result. Alerts prompt a check and are not diagnoses.
- **Threshold review:** The proposal says an officer should review the initial thresholds. Keep them identified as initial rules until that review; do not claim clinical accuracy from the formula alone.
- **Complete when:** The deterministic service returns the correct level and reason at each boundary, isolates each cow's history, and explains insufficient history.
- **Checks:** Tests for exact 15% and 25% boundaries, normal/warning/critical values, zero baseline, insufficient history, missing dates, and other-cow isolation. Synthetic values verify arithmetic only.

### Stage 4: Review initial thresholds with a veterinary or extension officer

- **Purpose:** Have a qualified local professional review the proposal's initial 15% and 25% thresholds and suggested farmer actions.
- **Dependencies:** Stage 3's documented rule and a review by the intended veterinary or extension contact.
- **Rules:** Record the reviewer, date, feedback, and any approved threshold changes. Until review, label these as initial project thresholds rather than validated clinical values.
- **Complete when:** The project records whether the initial values and actions were accepted or what changes were requested.

### Stage 5: Save, display, and acknowledge alerts

- **Status:** Implemented and covered by automated tests: saved alerts, farmer dashboard/alerts page, cow-level trend summary/chart, acknowledgement, owner access, and recalculation after corrected records. Manual responsive review remains in Stage 6.

- **Purpose:** Give farmers a durable, understandable follow-up workflow.
- **Dependencies:** Stages 1–4 and an approved alert schema.
- **Likely files:** A farmer-app alert model and migration, alert-generation service integration, farmer dashboard views/templates, and tests.
- **Complete when:** A qualifying rule produces a saved alert with its evidence, reason, severity, and suggested next step; the farmer can view and acknowledge it; repeat entries do not create uncontrolled duplicate alerts.
- **Checks:** Migration and model tests, alert-generation tests, farmer access-control tests, acknowledgement tests, and an end-to-end milk-entry-to-alert test.

### Stage 6: Verify the full rule-based alert workflow

- **Status:** Automated milk-rule, correction, dashboard, access-control, and farmer-dashboard checks pass; manual responsive review remains pending.

- **Purpose:** Confirm the complete path works for real user actions and safe failure cases.
- **Dependencies:** Stages 1–5.
- **Checks:** Test valid and invalid entries, duplicate/corrected records, sparse histories, normal and unusual yields, severity boundaries, alert persistence, acknowledgement, ownership isolation, and readable messages. Manually verify the farmer workflow at small, medium, and large screen sizes if templates change.
- **Complete when:** The workflow behaves consistently from milk entry to alert review, and known data/rule limitations are documented.

### Stage 7: Add a rule-based next-day milk estimate

- **Purpose:** Show a simple next-day estimate without training a model or mixing it with alerts.
- **Dependencies:** Stable milk records, an agreed rule such as a recent recorded-day average, and enough history for chronological evaluation.
- **Complete when:** Estimates are distinguished from actual milk records, compared with a previous-day baseline using date-ordered backtesting, reported in litres of error, and shown with their limitations.

### Stage 8: Extend farm-management records and support

- **Purpose:** Add remaining animal, farm, feeding, health, breeding/calving, and officer-support capabilities that are needed by users.
- **Dependencies:** Confirmed user workflow and data requirements. Reuse existing cow, reproductive-event, messaging, and notification functionality where it fits.
- **Complete when:** Each selected record type has a clear purpose, owner/access rules, validation, migration, tests, and a connected user workflow. Do not create all conceptual tables at once.

### Stage 9: Deployment readiness

- **Purpose:** Make configuration, security, storage, and operational steps clear for deployment.
- **Dependencies:** Stable workflows and a deployment target.
- **Complete when:** Environment setup is documented, production secrets and allowed hosts are configured safely, database migrations are reviewed, email/OAuth/AI integrations are actually verified as required, and deployment checks pass without unresolved critical warnings.

## Working Rules for Every Task

1. **Inspect first:** Read relevant files, check Git status, and identify current behavior before planning a change.
2. **Explain the slice:** State its purpose, dependencies, intended files, risks, completion conditions, and checks in beginner-friendly language.
3. **Wait for approval:** Do not edit or implement a proposed feature until the user approves that specific slice. A request to inspect or plan is not approval to code.
4. **Keep scope narrow:** Change only what the approved slice needs. Preserve existing public pages, login, role routing, reproductive tracking, messaging, and dashboard behavior unless a change is explicitly part of the slice.
5. **Protect stored data:** Follow `DATABASE_CHANGE_RULES.md`; use reviewed Django migrations, prefer additive changes, and never reset or manually alter the database to make checks pass.
6. **Validate the changed behavior:** Run relevant static/system/migration checks and focused tests. Do not claim checks passed unless they ran successfully. Do not advance to the next stage with unresolved failures.
7. **Explain the result:** Summarize changed paths, behavior, verification results, remaining limits, and commands the beginner can use to review it.

## AI and Data Safety Rules

- Validate and retain the original farmer-entered milk measurement; keep calculated features and predictions separate from actual records.
- Identify missing, invalid, corrected, or insufficient data explicitly. Never silently invent measurements or dates.
- Use chronological splits for time-dependent evaluation and prevent future information from entering historical features.
- Store enough evidence to explain an alert, but do not expose raw coordinates, secrets, or unnecessary personal information.
- An unusual yield means "check this," not "this cow is sick." Route clinical concerns to qualified veterinary or extension staff.
- Clearly label synthetic data and simulated screens. Never use synthetic performance as proof that the model works for Kenyan dairy farms.
- Do not transmit farm or animal data to external AI services without making the data flow clear and receiving approval.

## Isolated Model Experiments

- Use `experiments/milk_ai/` for prototypes and model comparisons before considering changes to the Django application.
- Keep its Python environment, experiment code, downloaded model weights, datasets, and generated reports separate from the application environment and tracked source data.
- Start with clearly labeled synthetic data. Use real farm data only after its source, privacy, and any external data transfer have been reviewed and approved.
- An experiment passing its checks does not by itself approve integration. Review its time-aware evaluation and fit with the roadmap before proposing an application change.
- The isolated workspace may be used for optional forecasting experiments, but the application roadmap does not require model training. The current next step remains collecting and reviewing real session-based milk records.

## Known Baseline Items to Recheck

The initial read-only review identified these issues; recheck them before the related work because they may have changed:

- Django reported a pending `CalvingEvent` model-options migration.
- `manage.py check --deploy` warned that the configured Django `SECRET_KEY` is weak.
- SMTP authentication returned code 535 during a no-email connectivity check.
- PostgreSQL connected successfully with a read-only query, and the OpenRouter models endpoint accepted its configured key. These checks do not guarantee future availability.
- Google OAuth credentials were present and Google's public endpoint was reachable, but a complete interactive sign-in was not tested.

## Decision and Progress Log

Keep this section short. After each approved stage, record its status, important decisions, and any remaining blocker. Update the roadmap when implementation reveals that a dependency or assumption is wrong.

- **Current product-data status:** Session-based entry and Stage 2 features are implemented. No real milk-production history has been collected yet; tests use synthetic records only.
- **Completed:** Stage 0 migration generated, reviewed, and applied. Stage 1 now records morning/evening values and preserves existing daily totals; the additive migration is applied and farmer-dashboard checks pass. Stage 2's deterministic per-cow historical features remain unchanged.
- **Current next step:** Collect real session-based milk records and review coverage. Then implement the proposal's rule-based 15%/25% alert calculation and arrange the stated veterinary/extension review.
- **Open product decision:** The proposal's alert baseline uses the previous seven recorded daily totals, while Stage 2's separate historical features use the preceding seven calendar days. Keep these meanings explicit when implementing alerts.
