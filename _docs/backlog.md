# Django Build Backlog

Small, ordered tasks derived from [`_docs/plan.md`](./_docs/plan.md).

## Foundation

- [x] **Configure the Django application** — Register `chores`, configure environment-based settings, and add a basic health-check or home page.
- [x] **Create the initial database migration** — Confirm SQLite development configuration and establish the migration workflow.

## Authentication and households

- [x] **Implement authentication** — Add registration, login, logout, and protected views using Django’s built-in auth system.
- [x] **Model households and memberships** — Create `Household` and membership/role models with one administrator per household.
- [x] **Add household creation and joining** — Let an authenticated user create a household or join one using a generated household code.
- [x] **Add role-based permissions** — Restrict household administration to the administrator while allowing members to view and complete their chores.

## Chore planning

- [x] **Model chores** — Add one-off and recurring chore fields, including title, description, schedule type, due date, active status, household, and assignee.
- [x] **Build administrator chore CRUD** — Add forms, views, templates, and URL routes for creating, editing, and deleting chores.
- [x] **Build the date-grouped chore list** — Show upcoming, due, and completed chores in a responsive list scoped to the current household.

## Rotation and completion

- [x] **Implement recurring assignment rotation** — Select household members in a deterministic rotation and advance assignments for each recurrence.
- [x] **Add administrator assignment overrides** — Allow the administrator to change the assignee for an individual chore occurrence.
- [x] **Add completion tracking** — Record who completed a chore and when; allow authorized members to mark their assigned chores complete.

## Reminders and release readiness

- [x] **Add in-app reminders** — Display reminders for upcoming and overdue chores in the household interface.
- [x] **Add validation and permission tests** — Cover authentication, household isolation, role restrictions, rotation, and completion behavior.
- [x] **Document local setup and deployment** — Record `uv` commands, migrations, test execution, and required environment variables in `README.md`.
