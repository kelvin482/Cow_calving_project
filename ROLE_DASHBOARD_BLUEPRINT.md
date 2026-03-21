# Role Dashboard Blueprint

This document explains the planned structure for the CowCalving website in a simpler and more understandable way.

The goal is:
- one shared website
- one shared login and registration system
- different dashboards for different user roles
- a structure that can grow later without breaking the project

## Phase One Roles

For now, the system will support only two roles:
- `farmer`
- `veterinary`

More roles may be added later, so the system should not be built in a way that only works for these two forever.

## Main Idea

Everyone uses the same website.

That means:
- all users visit the same home page
- all users use the same login page
- only farmers use the public register page
- veterinary doctors sign in with admin-provisioned credentials

After login, the system checks the user's role and takes them to the correct dashboard.

Example:
- farmer -> shared website home first, then farmer dashboard through the website
- veterinary -> veterinary dashboard

## Planned Apps

We plan to organize the project into these Django apps:

### `core`
**Descriptive title:** Website & Public Pages

This app will handle:
- the home page
- public website pages
- shared site navigation
- shared public layouts such as header and footer

### `accounts`
**Descriptive title:** Authentication & Account Access

This app will handle:
- login
- public farmer registration
- veterinary sign-in with admin-issued professional ID and password
- password reset
- email verification
- auth-related redirects before the user enters a dashboard

### `users`
**Descriptive title:** User Profiles & Role Management

This app will keep the user's extra details.

That means it should store things like:
- role
- farm name
- profile completion state
- dashboard assignment data
- future user profile details

Simple meaning:
- `accounts` handles how a user signs in
- `users` handles who the user is in the system

### `farmers_dashboard`
**Descriptive title:** Farmer Operations Dashboard

This app will handle:
- the farmer dashboard home
- farmer-specific pages
- farmer-only tools and records

### `veterinary_dashboard`
**Descriptive title:** Veterinary Care Dashboard

This app will handle:
- the veterinary dashboard home
- veterinary-specific pages
- veterinary-only tools and records

### `cow_calving_ai`
**Descriptive title:** AI Assistance & Insights

This app will handle:
- AI tools
- shared AI features
- future role-aware AI support if needed

## Current Implementation Status

The first implementation slice has now started.

Already implemented:
- `users` app
- role/profile data layer
- shared `/dashboard/` redirect entry point
- `farmers_dashboard` placeholder app
- `veterinary_dashboard` placeholder app

Still planned next:
- `core` public website app
- full role-aware navigation
- final styled dashboard screens
- richer farmer and veterinary modules

## How the Website Will Work

The website flow should be:

1. A user visits the same public website.
2. The user signs up or logs in from the same auth pages.
3. The system checks the user's role.
4. The system redirects the user to the correct dashboard.

This keeps the project simple for users because there is:
- one website
- one login
- one registration flow

## Suggested URL Structure

- `/` -> public home page
- `/accounts/login/` -> shared login page
- `/accounts/signup/` -> shared register page
- `/dashboard/` -> shared redirect page after login
- `/farmers/` -> farmer dashboard
- `/veterinary/` -> veterinary dashboard
- `/app/` -> shared AI or internal tools if still needed

## Why the `users` App Is Important

Right now, the signup form already asks for some extra information, such as:
- farm name

But that information should not stay only inside the auth form forever.

The `users` app is important because it gives the project one proper place to store user details after authentication.

This avoids mixing:
- authentication logic
with
- user business/profile data

That separation makes the project:
- cleaner
- easier to maintain
- easier to expand later

## Recommended Data Direction

The safest short-term plan is:

```text
User
`-- Profile
    |-- role
    |-- professional_id
    |-- farm_name
    |-- phone_number
    |-- is_profile_complete
    `-- dashboard_slug
```

Better long-term scalable option:

```text
Role
|-- slug
|-- name
|-- dashboard_namespace
|-- default_path
`-- is_active

Profile
|-- user
|-- role -> Role
|-- professional_id
|-- farm_name
`-- is_profile_complete
```

Why this is better:
- role behavior stays configurable
- redirects stay easier to manage
- new roles can be added later without rewriting many views and templates

## Redirect Plan

After login or registration, the project should use one shared redirect entry point:
- `/dashboard/`

That route should:
1. confirm the user is logged in
2. load the user's profile and role data
3. send the user to the correct dashboard

For phase one:
- `farmer` -> `/`
- `veterinary` -> `/veterinary/`

Important rule:
- do not hardcode this redirect logic in many places
- keep one shared source of truth for dashboard routing

## Access Control Plan

Each dashboard must protect its own pages.

Expected behavior:
- logged-out users should be redirected to login
- users with the wrong role should not enter the wrong dashboard
- public website pages should stay open to everyone

Recommended shared tools:
- `login_required`
- reusable role decorator or mixin

Suggested location for role checks:
- `users/permissions.py`

## Template Structure

Suggested structure:

```text
templates/
  core/
    home.html
  accounts/
  farmers_dashboard/
    dashboard.html
  veterinary_dashboard/
    dashboard.html
  includes/
    navbar.html
    footer.html
    sidebar.html
```

## Navigation Plan

Public navigation should show:
- Home
- About
- Contact
- Login
- Farmer Register

Authenticated navigation should:
- keep the shared brand
- show the correct dashboard link for the current role
- show only the navigation items that the role is allowed to use

## Authentication Direction Update

To keep veterinary access professional and controlled:
- farmers can self-register
- veterinary doctors cannot self-register
- veterinary accounts are created by admin
- veterinary doctors sign in with `professional_id` and password
- role changes into `veterinary` must not be possible through self-service profile editing

## Build Order

To avoid conflicts, we should build in this order:

1. Create `core` for the shared public website
2. Create `users` for profile and role persistence
3. Move role storage out of the auth form and into the profile layer
4. Create `/dashboard/` redirect logic
5. Create `farmers_dashboard`
6. Create `veterinary_dashboard`
7. Update login and signup redirects to use `/dashboard/`
8. Add role-aware navigation and role protection

## Conflict Prevention Rules

To keep the project stable:
- do not duplicate auth logic inside dashboard apps
- do not store role rules in many different places
- do not hardcode dashboard redirects across multiple views
- keep role-routing logic centralized
- add concise comments around non-obvious role and permission logic

## Immediate Next Step

The safest coding step after this blueprint is:

1. create the `users` app
2. add a `Profile` model
3. persist the selected role from registration
4. prepare the shared `/dashboard/` redirect

That will give the project the right foundation for both dashboards.
