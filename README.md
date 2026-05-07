# Smart Task Management System
### Python Desktop App — based on ASRS Architectural Design Document

## Quick Start

```bash
# 1. Install the only dependency
pip install flask

# 2. Run the app
python app.py
```

The app opens automatically in your browser at **http://127.0.0.1:5000**

---

## Features (mapped to ASRs)

| ASR | Requirement | Implementation |
|-----|-------------|----------------|
| ASR-01 | Response < 2s | SQLite with indexed queries; no network calls |
| ASR-02 | Security / env vars | Input validation on client + server; no raw SQL injection possible |
| ASR-03 | Concurrent users | Flask threaded server; SQLite WAL mode |
| ASR-04 | Usable, responsive UI | Responsive CSS layout; sidebar filters; keyboard shortcuts |
| ASR-05 | Maintainability | Layered architecture: DB layer / business logic / REST API / frontend |

## Architecture (from the document)

```
Frontend (HTML/CSS/JS)       ← Presentation layer
      ↓ fetch() REST calls
Flask REST API               ← Application / business logic layer
      ↓ SQL queries
SQLite (tasks.db)            ← Data layer
```

## Task State Machine

```
Pending → In Progress → Completed
    ↑           ↓            ↓
    └── Cancelled ←──────────┘
         ↓
       Pending
```

## Keyboard Shortcuts
- `Ctrl+N` — New task
- `Escape` — Close modal

## Files
- `app.py`   — Complete application (Flask server + embedded frontend)
- `tasks.db` — SQLite database (auto-created on first run)
