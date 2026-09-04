# Shared Household Chores Tool

A responsive web app for planning and managing shared household chores.

## Local development

This project uses Django, SQLite, and `uv`.

```powershell
uv sync
$env:DJANGO_SECRET_KEY = "change-this-for-local-development"
$env:DJANGO_DEBUG = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
uv run python manage.py migrate
uv run python manage.py check
uv run python manage.py test
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/> after starting the development server. Copy
`.env.example` for the available environment variables when using a dotenv
loader or deployment platform; Django reads `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS` from the environment.

## Features

- User registration, login, and logout
- One household per account, with administrator/member roles
- Household creation and eight-character join codes
- Administrator-only chore create, edit, and delete
- One-off, daily, weekly, and monthly chores
- Deterministic recurring assignment rotation
- Per-occurrence administrator assignment overrides
- Completion history with completing user and timestamp
- Date-grouped upcoming/due/completed list and in-app reminders

The Django admin is available at `/admin/`. Email, push notifications,
multiple households, calendar views, and gamification are intentionally out
of scope.
