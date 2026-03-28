# Calving Assistant

Calving Assistant is the Django app inside the Cow Calving Assistant project that provides models, APIs and AI integration to help farmers track pregnancy, predict calving dates, record feed and health events, and receive calving advice.

## Purpose

- Store and manage cow and pregnancy records
- Provide calving prediction logic and alerts
- Expose APIs for cow record management
- Integrate with an AI service for advice and question answering

## Key Features

- Cow management (create, read, update, delete)
- Pregnancy tracking and expected calving date calculation
- Feed and health record logging
- Simple AI service interface for livestock questions
- Admin views for managing events

## Models (planned / included)

- `Cow` — cow_id, breed, date_of_birth, weight, health_status
- `Pregnancy` — cow (FK), insemination_date, expected_calving_date, pregnancy_status
- `FeedRecord` — cow (FK), feed_type, quantity, date
- `HealthRecord` — cow (FK), symptoms, diagnosis, treatment, date
- `CalvingEvent` — example model included in this app for event tracking

Expected calving date example logic:

```
expected_calving_date = insemination_date + 283 days
```

## API Endpoints (example)

- `POST   /api/cows/` — create cow
- `GET    /api/cows/` — list cows
- `GET    /api/cows/<id>/` — retrieve cow
- `PUT    /api/cows/<id>/` — update cow
- `DELETE /api/cows/<id>/` — delete cow

Additional endpoints will be added for pregnancies, feed records, health records, and AI-assisted advice.

## AI Integration

Create a service module at `livestock/services/ai_service.py` (or `cow_calving_ai/services/ai_service.py`) responsible for:

- formatting prompts
- sending them to the AI model
- processing and returning responses

The app should keep AI calls behind a service layer so the implementation can be swapped (OpenAI, local LLM, or other provider).

### Website Guide Policy (RAG-lite)

This app loads a short policy document and injects it into the system prompt. This keeps responses aligned to the website goals even when API keys change.

Defaults:
- Policy file: `cow_calving_ai/policies/website_guides.md`
- Max policy characters: `AI_POLICY_MAX_CHARS` (default 1800)
- Policy on/off: `AI_POLICY_ENABLED` (default true)

### Demo provider (GitHub Models)

This app now supports a small demo AI integration through the OpenAI SDK with GitHub Models:

- set `AI_PROVIDER=github_models`
- set `GITHUB_TOKEN=<your_github_pat_token>`
- optional model/base URL:
  - `GITHUB_MODEL=openai/gpt-4o-mini`
  - `GITHUB_MODELS_BASE_URL=https://models.github.ai/inference`

Demo endpoint:

- `GET /ai/test/?q=What+signs+show+calving+is+near&cow_id=COW-001`

## Project Structure (app-level)

```
cow_calving_ai/
├── admin.py
├── apps.py
├── models.py
├── views.py
├── services/
│   └── ai_service.py    # add this
├── migrations/
└── README.md
```

## Setup (development)

1. Create and activate virtualenv (already present as `.venv` in this workspace):

```
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# or cmd
.venv\Scripts\activate.bat
```

2. Install dependencies:

```
python -m pip install -r requirements.txt
```

3. Configure environment variables in the project root `.env` (example keys are present in the repo `.env`).

4. Run migrations and start the dev server:

```
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver
```

## Environment

Keep sensitive values out of source control. `.env` is present and `.gitignore` excludes it.

Recommended env vars:

- `SECRET_KEY`
- `DEBUG` (True/False)
- `ALLOWED_HOSTS`
- `AI_POLICY_PATH` (optional override for policy file)
- `AI_POLICY_MAX_CHARS` (optional token budget for policy text)
- `AI_POLICY_ENABLED` (optional enable/disable policy injection)

## Testing

Run app tests:

```
.venv\Scripts\python manage.py test cow_calving_ai
```

## Next steps (recommended)

1. Implement the full `Cow`, `Pregnancy`, `FeedRecord`, and `HealthRecord` models in `models.py`.
2. Add DRF serializers and viewsets for the API endpoints.
3. Implement `ai_service.py` with concrete provider integration and a safe prompt wrapper.
4. Add scheduled tasks to generate calving alerts (Celery / cron / APScheduler).

## Contributing

Please open issues or pull requests for features or fixes. Follow the Django coding best practices and include tests for new behavior.

## License

Specify project license here.

