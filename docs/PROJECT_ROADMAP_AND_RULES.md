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

AI should support a farmer's decision. An anomaly is a signal to investigate; it is not proof of illness or a veterinary diagnosis. Do not claim that a model is accurate for real farms until it has been evaluated on suitable, representative real data.

## Confirmed Starting Point

The repository currently uses Django, Python, Django templates, HTML, CSS/Tailwind, JavaScript, PostgreSQL configuration, and an OpenRouter-backed AI advice service. The codebase already includes:

- Shared public pages, authentication, profiles, and database-backed `farmer` and `veterinary` roles.
- A `Cow` model owned by a farmer, cow registration, reproductive dates and status, reproductive events, and a calving tracker.
- Farmer-to-veterinary conversations, image attachments, and notifications stored in the database.
- A veterinary workspace whose patient and clinical-record screens contain demo data and are not yet backed by veterinary case models.
- An AI advice workspace. This is a question-and-answer feature, not a milk-yield prediction or anomaly-detection system.

At the initial review, the code did **not** include a milk-production record model or entry workflow. Stages 0–2 have since added daily milk capture and deterministic per-cow historical feature calculations. The code still does not include feeding or health record models, milk anomaly detection, or milk-yield prediction. No real historical milk dataset has been collected, so there is not enough production data to assess real-world model performance. The project stores farm details on a user profile rather than in a separate multi-farm model.

Treat this as a baseline from the initial review, not a permanent guarantee. Inspect the relevant code and Git status again before every implementation slice.

## Architecture Direction

Keep the existing Django application and extend it. Do not rebuild the project or add a second implementation of accounts, cows, dashboards, or AI advice.

- **User interface:** Existing Django templates and dashboard assets collect entries and show results.
- **Application logic:** Existing Django views and forms validate requests and enforce role and owner access. Put calculations and model inference in focused service modules when those responsibilities are introduced.
- **Database:** Django models and committed migrations remain the source of truth. Milk records should relate to the existing cow record; do not create a duplicate animal model.
- **Anomaly workflow:** A validated milk entry supplies data to feature calculations, then Isolation Forest, then separate severity rules. Store any resulting alert and its evidence so the farmer can review and acknowledge it.
- **Prediction workflow:** Random Forest next-day yield prediction is a later, separate feature. Do not mix it into the anomaly detector.
- **Existing AI advice:** Keep the current OpenRouter question-and-answer service separate from statistical milk models. Do not send health or production data to an external provider unless the user approves that data flow.

Enforce farmer ownership through the existing cow-to-owner relationship on every read and write. Do not trust a submitted cow ID by itself. If multi-farm management becomes necessary, plan a distinct Farm model and migration explicitly rather than treating a profile's farm-name string as a complete access-control system.

## Roadmap

Work on one stage at a time. Each stage has a completion gate; do not start the next stage until the current one is implemented, checked, and explained.

### Priority checklist

Use this short list to see what is important now. `[x]` means the work and its checks are complete; `[ ]` means it is still ahead. Keep the detailed scope and checks in the matching stage below.

| Priority | Task | Why it matters / alignment | Status |
|---|---|---|---|
| P0: Foundation | Reconcile Django migrations | Prevent new persistent features from building on an unclear database baseline. | [x] Migration reviewed and applied; Django check and all 20 `cow_calving_ai` tests passed. |
| P1: Core data | Record and correct one daily total per cow | Reliable production history is required for trends, anomaly detection, and prediction. | [x] Farmer-owned entry, correction, duplicate/date/quantity validation, 32 dashboard tests, and responsive layout checks passed. |
| P1: Data readiness | Collect and review milk records for coverage, gaps, duplicates, invalid values, and usable history | Avoid training or alerting from sparse or misleading data. Missing entries must not be treated as zero. | [ ] No real production history collected yet; model evaluation waits for suitable history. |
| P1: Explainable foundation | Calculate and test historical production features | Provides understandable, time-safe inputs for anomaly detection and later prediction. | [x] Stage 2 formulas documented and implemented; 8 focused tests passed. |
| P1: Core outcome | Detect unusual production changes, apply approved severity rules, and give farmers a useful follow-up workflow | Delivers the project's early-warning goal without presenting an anomaly as a diagnosis. | [ ] Depends on features, approved thresholds, and an alert workflow. |
| P1: Reliability | Verify the full milk-entry-to-alert flow, including access control and small, medium, and large screens | Ensures the main farmer workflow works end to end. | [ ] After alert integration. |
| P2: Prediction | Add and chronologically evaluate next-day Random Forest predictions against a previous-day baseline | Adds forecasting only after data and the core monitoring workflow are dependable. | [ ] Later; requires enough suitable real history. |
| P3: Extensions | Add feeding, health, veterinary-case, or other farm records only when a confirmed workflow needs them | Supports the broader product goal while avoiding disconnected tables and unfinished screens. | [ ] Select one user need at a time after the core workflow. |
| P3: Release readiness | Prepare and verify deployment configuration and integrations | Makes the completed workflows safe and operable in the chosen deployment environment. | [ ] Near release. |

**Current focus:** Stages 0–2 are complete and checked. Start collecting real milk history and review its coverage before training or evaluating an anomaly model. Synthetic tests verify calculation behavior only; they are not evidence of model accuracy.

### Stage 0: Reconcile migration state — complete and tested

- **Purpose:** Start database work from a clean, understood migration baseline.
- **Resolved:** Added and applied `cow_calving_ai/migrations/0002_alter_calvingevent_options.py` to record the `CalvingEvent` model options without editing the initial migration. Django reports no further model changes.
- **Likely files:** A new migration in `cow_calving_ai/migrations/`. Inspect the model and migration graph first. Do not edit an old migration to hide the mismatch.
- **Complete when:** The intended migration is reviewed and `makemigrations --check --dry-run` no longer reports this existing change.
- **Checks:** `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --plan`, `python manage.py check`, and relevant AI-app tests. Applying a migration to a database is a separate operation and must be planned and reported.

### Stage 1: Confirm and implement milk-record capture

- **Status:** Complete and tested. The approved format is one daily total per cow, measured in litres. Responsive layouts were checked at small, medium, and large widths.

- **Purpose:** Begin collecting the historical data required for trends and anomaly detection.
- **Dependencies:** The existing `farmers_dashboard.Cow` model, farmer role protection, cow-owner scoping, and the clean migration baseline.
- **Decision gate:** Before creating the schema, confirm whether a record is one daily total per cow or separate milking-session entries. The initial product description says daily production, but the exact recording granularity must be explicit.
- **Likely files:** `farmers_dashboard/models.py`, `forms.py`, `views.py`, `urls.py` if a new route is justified, a cow-focused template, a new farmers-dashboard migration, and `farmers_dashboard/tests.py`.
- **Complete when:** An authorized farmer can create and correct a valid milk record for their own cow, see saved records, and cannot access another farmer's cow records. Invalid quantities and duplicate records follow the approved recording rule.
- **Checks:** Model and form tests, duplicate/date/quantity validation tests, owner-isolation tests, migration review and checks, Django system check, and relevant farmer-dashboard tests.

### Stage 2: Calculate and explain historical features

- **Status:** Complete and tested. The approved baselines use the prior 7 and 30 calendar days, measured entries only, with minimum counts of 5 and 20 respectively. The 30-day deviation is in litres; days in milk uses the latest recorded calving event on or before the milk date and is unavailable without one.

- **Purpose:** Turn a cow's own production history into understandable inputs for the anomaly detector.
- **Dependencies:** Saved milk records with reliable dates and quantities from Stage 1.
- **Required features from the proposal:** Current day's yield; percentage change from the previous 7-day average; deviation from the previous 30-day average; standard deviation over the previous 7 days; and days in milk.
- **Decisions:** Windows are the preceding calendar days and exclude the current observation. Missing dates are not zero. Percentage change is `(current yield - previous 7-day mean) / previous 7-day mean * 100`; 30-day deviation is `current yield - previous 30-day mean` in litres; 7-day spread is population standard deviation in litres. At least 5 of the prior 7 days and 20 of the prior 30 days must have measurements. Percentage change is unavailable when its baseline is zero. Days in milk counts calving day as day 1 and uses the latest `calved` reproductive event no later than the record date; if none exists, it is unavailable. `expected_calving_date` is not used as an actual calving date.
- **Files:** `farmers_dashboard/milk_features.py` and `farmers_dashboard/test_milk_features.py`.
- **Complete when:** Each feature has a documented formula, source fields, and behavior for missing or insufficient history; calculations are deterministic and tested.
- **Checks:** Unit tests for known values, calendar-window boundaries, missing dates, zero baselines, insufficient history, other-cow isolation, and missing calving events. No model training is required in this stage.

### Stage 3: Evaluate and integrate Isolation Forest

- **Status:** Not started; depends on enough valid real milk history for the selected per-cow approach.

- **Purpose:** Flag records that look unusual compared with relevant historical production patterns.
- **Dependencies:** Stages 1 and 2, sufficient valid history for the selected approach, and an agreed plan for how cows' histories inform the model.
- **Rules:** Use the Isolation Forest specified in the proposal. Build features from each cow's own history rather than comparing raw yields to one universal farm-wide average. Do not train or score when required data is missing or insufficient; return a clear "not enough history" outcome. Keep training, evaluation, and inference separable. Use time-aware evaluation where applicable and avoid future data leaking into past predictions.
- **Likely files:** A small anomaly-detection service, the declared Python dependencies if a model library is approved and needed, and tests using clearly labeled synthetic examples.
- **Complete when:** The service returns a testable anomaly result and evidence, handles insufficient data safely, and its limits are explained. Synthetic data verifies software behavior only; it does not establish real-world accuracy.
- **Checks:** Deterministic tests for expected normal/unusual inputs, insufficient history, missing features, and error handling. Evaluate on real data before making accuracy claims.

### Stage 4: Agree and implement severity rules

- **Purpose:** Translate a model flag into a practical Low, Medium, or High follow-up level.
- **Dependencies:** Stage 3 and the proposal's configured severity thresholds.
- **Decision gate:** The proposal's Low-severity wording is ambiguous. Locate any existing configuration, explain the ambiguity, and get the user's approval for a clear interpretation before implementation. Do not guess thresholds.
- **Rules:** Keep severity thresholds separate from Isolation Forest. Severity and recommendations are not diagnoses. Make thresholds configurable in the project's established configuration or data model rather than scattering magic numbers across views and templates.
- **Likely files:** A focused severity/rules service, configuration or persistence only if justified, and tests.
- **Complete when:** Approved rules map model evidence and relevant recorded events to a severity and understandable reason, with boundary cases covered by tests.

### Stage 5: Save, display, and acknowledge alerts

- **Purpose:** Give farmers a durable, understandable follow-up workflow.
- **Dependencies:** Stages 1–4 and an approved alert schema.
- **Likely files:** A farmer-app alert model and migration, alert-generation service integration, farmer dashboard views/templates, and tests.
- **Complete when:** A qualifying anomaly produces a saved alert with its evidence, reason, severity, and recommended next step; the farmer can view and acknowledge it; repeat entries do not create uncontrolled duplicate alerts.
- **Checks:** Migration and model tests, alert-generation tests, farmer access-control tests, acknowledgement tests, and an end-to-end milk-entry-to-alert test.

### Stage 6: Verify the full anomaly workflow

- **Purpose:** Confirm the complete path works for real user actions and safe failure cases.
- **Dependencies:** Stages 1–5.
- **Checks:** Test valid and invalid entries, duplicate/corrected records, sparse histories, normal and unusual yields, severity boundaries, alert persistence, acknowledgement, ownership isolation, and readable messages. Manually verify the farmer workflow at small, medium, and large screen sizes if templates change.
- **Complete when:** The workflow behaves consistently from milk entry to alert review, and known data/model limitations are documented.

### Stage 7: Add next-day milk prediction

- **Purpose:** Predict next-day yield with the proposal's Random Forest Regression model after the anomaly workflow and adequate data are established.
- **Dependencies:** Stable milk records, suitable real history, agreed prediction features, and an honest chronological evaluation plan.
- **Complete when:** Predictions are distinguishable from actual measurements, evaluated using appropriate metrics such as MAE and RMSE (and R² when appropriate), and limitations are visible to users.

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
- Creating this workspace does not start Stage 3 or change the current next step: collect and review real daily milk records.

## Known Baseline Items to Recheck

The initial read-only review identified these issues; recheck them before the related work because they may have changed:

- Django reported a pending `CalvingEvent` model-options migration.
- `manage.py check --deploy` warned that the configured Django `SECRET_KEY` is weak.
- SMTP authentication returned code 535 during a no-email connectivity check.
- PostgreSQL connected successfully with a read-only query, and the OpenRouter models endpoint accepted its configured key. These checks do not guarantee future availability.
- Google OAuth credentials were present and Google's public endpoint was reachable, but a complete interactive sign-in was not tested.

## Decision and Progress Log

Keep this section short. After each approved stage, record its status, important decisions, and any remaining blocker. Update the roadmap when implementation reveals that a dependency or assumption is wrong.

- **Current product-data status:** Stages 1 and 2 are implemented. No real milk-production history has been collected yet; calculation tests use synthetic records only.
- **Completed:** Stage 0 migration generated, reviewed, and applied. Stage 1 added daily milk entry and correction; its migration was applied, all 32 `farmers_dashboard` tests passed, and the page was visually checked at 504, 738, and 1,410 CSS-pixel widths. Stage 2 adds deterministic per-cow historical features with approved missing-data rules and focused tests.
- **Current next step:** Collect real daily milk records and review coverage. Begin Stage 3 only when enough valid per-cow history is available for a meaningful evaluation.
- **Open product decisions:** Stage 4 severity thresholds still require review of the proposal's ambiguous Low-severity wording before implementation.
