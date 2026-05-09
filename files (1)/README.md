# Smart Task Management System

A Flask + SQLite task manager with a full REST API, state-machine status transitions, and a responsive single-page UI.

---

## Project structure

```
task-app/
├── app.py              # Entry point — creates Flask app, starts server
├── database.py         # DB connection, schema init, seed data
├── logic.py            # Business logic: state machine, validation
├── routes.py           # All REST API + frontend routes
├── templates/
│   └── index.html      # Single-page HTML template
├── static/
│   ├── css/style.css   # All styles
│   └── js/app.js       # All frontend JavaScript
├── tests/
│   └── test_app.py     # Pytest unit + API tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

---

## Run locally

```bash
pip install -r requirements.txt
python app.py
# → http://127.0.0.1:5000
```

---

## Run with Docker

```bash
# Build and start
docker compose up --build

# Stop
docker compose down
```

The SQLite database is stored in a Docker volume (`task_data`) so data persists across container restarts.

---

## Run tests

```bash
pip install pytest
pytest tests/
```

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks` | List tasks (filter by `status`, `priority`, `category`, `search`) |
| POST | `/api/tasks` | Create a task |
| PUT | `/api/tasks/<id>` | Update a task |
| DELETE | `/api/tasks/<id>` | Delete a task |
| GET | `/api/stats` | Counts by status and priority |
| GET | `/api/categories` | Distinct category list |

### Status transitions (state machine)

```
Pending  ──►  In Progress  ──►  Completed
   │               │                │
   └──► Cancelled ◄┘                └──► Pending
```
