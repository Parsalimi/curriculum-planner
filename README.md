# Curriculum Planner

A Django MVP for managing a university curriculum and tracking a student's course progress.

## MVP features

- User registration, login and logout
- Curriculum selection
- Course catalog
- Curriculum-specific course categories and mandatory flags
- Requirement groups:
  - Mandatory
  - Choose N courses
  - Choose N credits
- Prerequisite display
- Personal course tracking:
  - Not started
  - In progress
  - Passed
  - Failed
- Grade tracking
- Dashboard with credit and requirement progress
- Django Admin for managing curriculum data

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

Admin: http://127.0.0.1:8000/admin/

## Optional sample data

After migrations:

```bash
python manage.py seed_demo
```

This creates a demo Computer Science curriculum and courses. It does not create a user.

## PostgreSQL

The project is configured to use SQLite by default for zero-setup development.

To use PostgreSQL, set:

```bash
export DB_NAME=curriculum_planner
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_HOST=127.0.0.1
export DB_PORT=5432
```

Then run:

```bash
python manage.py migrate
```
