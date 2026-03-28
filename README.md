# CowCalving.farm

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0.3-0C4B33.svg)](https://www.djangoproject.com/)
[![Status](https://img.shields.io/badge/Status-Active%20Development-2d7a46.svg)](#current-status)

CowCalving.farm is a Django-based livestock support platform focused on cow calving guidance, farmer workflows, and veterinary coordination. The repository combines a public educational website, authentication flows, role-based dashboards, and an AI-assisted workspace in one modular project.

## Why This Project Exists

Cow calving is a high-stakes period for farmers. Good outcomes depend on preparation, monitoring, timely intervention, and access to support when a case becomes risky. This project is designed to make that journey clearer by giving users:

- public learning pages for guidance and preparation
- structured authentication and profile flows
- role-aware dashboards for farmers and veterinary professionals
- an AI workspace for livestock and calving-related support

## Core Features

- Public website with Home, Guide, Checklist, and Support pages
- Login, registration, logout, and password reset flows
- Database-backed role and profile system
- Shared post-login dashboard handoff
- Farmer dashboard with overview, herd, alerts, and reports pages
- Veterinary dashboard with schedule, farms, patients, diagnosis, prescriptions, labs, telehealth, and analytics pages
- AI workspace for guided livestock assistance

## Tech Stack

- Python 3
- Django 6
- SQLite for local development by default
- PostgreSQL-ready database configuration via environment variables
- Django Allauth for authentication and social login support
- OpenAI SDK support inside the AI app service layer
- HTML, CSS, and JavaScript for frontend pages

## Quick Start

```powershell
git clone https://github.com/kelvin482/Ai_Testing_intergration.git
cd Ai_Testing_intergration
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## Repository Structure

```text
DIGITAL FARM/
|-- manage.py
|-- requirements.txt
|-- .env.example
|-- README.md
|-- TEAM_RULES.md
|-- ENGINEERING_INSTRUCTIONS.md
|-- DATABASE_CHANGE_RULES.md
|-- ROLE_DASHBOARD_BLUEPRINT.md
|
|-- cow_calving_MAIN/
|   |-- settings.py
|   |-- urls.py
|   |-- middleware.py
|   |-- context_processors.py
|   |-- asgi.py
|   |-- wsgi.py
|
|-- Core_Web/
|   |-- views.py
|   |-- urls.py
|   |-- templates/
|   `-- static/
|
|-- accounts/
|   |-- views.py
|   |-- urls.py
|   |-- forms.py
|   |-- auth_backends.py
|   |-- email_backends.py
|   `-- templates/
|
|-- users/
|   |-- models.py
|   |-- views.py
|   |-- urls.py
|   |-- forms.py
|   |-- permissions.py
|   |-- services.py
|   `-- migrations/
|
|-- farmers_dashboard/
|   |-- views.py
|   |-- urls.py
|   `-- templates/
|
|-- veterinary_dashboard/
|   |-- views.py
|   |-- urls.py
|   `-- templates/
|
`-- cow_calving_ai/
    |-- views.py
    |-- urls.py
    |-- models.py
    |-- services/
    |-- policies/
    `-- templates/
```

## App Responsibilities

### `cow_calving_MAIN`
Project configuration and shared Django setup.

- settings, middleware, root routing, and template configuration

### `Core_Web`
Public-facing website pages that explain the product and support the demo flow.

- `/`
- `/guide/`
- `/checklist/`
- `/support/`

### `accounts`
Authentication and account access flows.

- `/accounts/login/`
- `/accounts/signup/`
- `/accounts/logout/`
- password reset views
- allauth integration

### `users`
Shared profile and role logic.

- profile model
- role model
- shared post-login redirect
- dashboard/profile routes

### `farmers_dashboard`
Role-restricted farmer workspace.

- `/farmers/`
- `/farmers/herd/`
- `/farmers/alerts/`
- `/farmers/reports/`

### `veterinary_dashboard`
Role-restricted veterinary workspace.

- `/veterinary/`
- `/veterinary/schedule/`
- `/veterinary/farms/`
- `/veterinary/patients/`
- `/veterinary/diagnosis/`
- `/veterinary/prescriptions/`
- `/veterinary/labs/`
- `/veterinary/telehealth/`
- `/veterinary/analytics/`

### `cow_calving_ai`
AI workspace and AI test endpoint.

- `/app/`
- `/app/ai/test/`

## Route Overview

| Area | Base Path | Purpose |
| --- | --- | --- |
| Public website | `/` | Product story, guide, checklist, and support pages |
| Authentication | `/accounts/` | Login, signup, logout, and reset flows |
| Shared dashboard handoff | `/dashboard/` | Role-aware redirect and profile management |
| Farmer workspace | `/farmers/` | Farmer overview, herd, alerts, and reports |
| Veterinary workspace | `/veterinary/` | Clinical and operational dashboard pages |
| AI workspace | `/app/` | Guided livestock support and AI demo entry point |

## User Flow

1. A visitor lands on the public website and learns what the platform does.
2. The visitor reads calving guidance, checklist content, or support information.
3. The visitor signs up or logs in.
4. The shared dashboard redirect checks the user profile and role.
5. The user is routed to the correct workspace.
6. Farmer and veterinary users continue into role-specific pages.
7. The AI workspace can be opened as a supporting tool.

## Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/kelvin482/Ai_Testing_intergration.git
cd Ai_Testing_intergration
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. At minimum, define:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

Optional settings already supported in the project include database, email, Google auth, and AI-related configuration.

### 5. Apply migrations

```powershell
python manage.py migrate
```

### 6. Run the development server

```powershell
python manage.py runserver
```

## Verification Commands

Use these checks before pushing changes:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Architecture Notes

- The project keeps the public website separate from authenticated dashboards.
- Role-aware routing is driven by database-backed role metadata in the `users` app.
- Farmer and veterinary workflows are separated into dedicated apps so each dashboard can grow independently.
- The AI feature is isolated in `cow_calving_ai` to keep provider integration behind a service layer.

## Development Rules In This Repository

Implementation in this repository is guided by:

- `TEAM_RULES.md`
- `ENGINEERING_INSTRUCTIONS.md`
- `DATABASE_CHANGE_RULES.md`
- `ROLE_DASHBOARD_BLUEPRINT.md`

These files define coding quality, roadmap-first workflow, database change rules, and role-based architecture expectations.

## Current Status

The repository already includes:

- a working Django project layout
- public pages for product storytelling
- authentication flows
- role-aware dashboard routing
- structured farmer and veterinary dashboard screens
- an AI app scaffold and demo endpoint

Some dashboard surfaces currently act as structured demo-ready UI while the data model for full live herd and case records continues to evolve.

## Roadmap

- Expand persistent herd, calving, and case data models
- Connect dashboard screens to live operational data
- Strengthen automated test coverage for critical workflows
- Improve AI-assisted support with safer and richer prompt flows

## Contributing

When contributing:

- keep changes focused
- preserve project structure and naming conventions
- do not invent APIs or undocumented behavior
- keep Django models and migrations in sync
- run checks before reporting work as complete

## License

Add the project license here when it is finalized.
