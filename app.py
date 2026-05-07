"""
Smart Task Management System
Based on: Architectural Design Report (ASRS Document)
Stack: Python + Flask + SQLite (no external dependencies beyond Flask)
Run:   python app.py   → opens at http://127.0.0.1:5000
"""

import sqlite3
import json
import os
import webbrowser
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

# ── Database layer ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'Pending',
            priority    TEXT    NOT NULL DEFAULT 'Medium',
            category    TEXT    DEFAULT 'General',
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)
    # Seed with sample tasks if empty
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        samples = [
            ("Design REST API endpoints", "Define all CRUD routes for task management", "Completed", "High", "Backend", now, now),
            ("Set up SQLite database", "Create schema with task attributes per ASR", "Completed", "High", "Backend", now, now),
            ("Build Flask application", "Implement business logic and routing layer", "In Progress", "High", "Backend", now, now),
            ("Create responsive UI", "HTML/CSS frontend with filtering and forms", "In Progress", "High", "Frontend", now, now),
            ("Add input validation", "Client-side and server-side checks per ASR-02", "Pending", "Medium", "Frontend", now, now),
            ("Write unit tests", "Decouple business logic for testability", "Pending", "Medium", "Testing", now, now),
            ("Docker containerisation", "Wrap app in Docker per DevOps perspective", "Pending", "Low", "DevOps", now, now),
            ("CI/CD with GitHub Actions", "Automate deploy pipeline per ASR-05", "Pending", "Low", "DevOps", now, now),
        ]
        conn.executemany(
            "INSERT INTO tasks (title,description,status,priority,category,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            samples
        )
    conn.commit()
    conn.close()

def row_to_dict(row):
    return dict(row)

# ── Business logic: valid state transitions (ASR — state machine) ─────────────

VALID_TRANSITIONS = {
    "Pending":     ["In Progress", "Cancelled"],
    "In Progress": ["Completed",   "Pending", "Cancelled"],
    "Completed":   ["Pending"],
    "Cancelled":   ["Pending"],
}

def is_valid_transition(current, new):
    return new in VALID_TRANSITIONS.get(current, [])

# ── REST API routes ───────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    status   = request.args.get("status", "")
    priority = request.args.get("priority", "")
    category = request.args.get("category", "")
    search   = request.args.get("search", "")

    query  = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"; params.append(status)
    if priority:
        query += " AND priority = ?"; params.append(priority)
    if category:
        query += " AND category = ?"; params.append(category)
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"; params += [f"%{search}%", f"%{search}%"]

    query += " ORDER BY created_at DESC"

    conn  = get_db()
    tasks = [row_to_dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    # Validation (ASR-02 / ASR-04)
    if not data or not data.get("title", "").strip():
        return jsonify({"error": "Title is required"}), 400
    if len(data["title"]) > 120:
        return jsonify({"error": "Title must be 120 characters or fewer"}), 400
    if data.get("priority") not in ("High", "Medium", "Low"):
        return jsonify({"error": "Invalid priority"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cur  = conn.execute(
        "INSERT INTO tasks (title,description,status,priority,category,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
        (
            data["title"].strip(),
            data.get("description", "").strip(),
            "Pending",
            data.get("priority", "Medium"),
            data.get("category", "General").strip() or "General",
            now, now
        )
    )
    conn.commit()
    task = row_to_dict(conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    conn = get_db()
    row  = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    current = row_to_dict(row)

    # Status transition validation
    new_status = data.get("status", current["status"])
    if new_status != current["status"] and not is_valid_transition(current["status"], new_status):
        conn.close()
        return jsonify({"error": f"Invalid transition: {current['status']} → {new_status}"}), 400

    if not data.get("title", current["title"]).strip():
        conn.close()
        return jsonify({"error": "Title cannot be empty"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE tasks SET title=?,description=?,status=?,priority=?,category=?,updated_at=? WHERE id=?",
        (
            data.get("title", current["title"]).strip(),
            data.get("description", current["description"]).strip(),
            new_status,
            data.get("priority", current["priority"]),
            data.get("category", current["category"]).strip() or "General",
            now,
            task_id
        )
    )
    conn.commit()
    task = row_to_dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return jsonify(task)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    row  = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted", "id": task_id})


@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_db()
    total     = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    by_status = {r["status"]: r["cnt"] for r in
                 conn.execute("SELECT status, COUNT(*) cnt FROM tasks GROUP BY status").fetchall()}
    by_prio   = {r["priority"]: r["cnt"] for r in
                 conn.execute("SELECT priority, COUNT(*) cnt FROM tasks GROUP BY priority").fetchall()}
    conn.close()
    return jsonify({"total": total, "by_status": by_status, "by_priority": by_prio})


@app.route("/api/categories", methods=["GET"])
def categories():
    conn = get_db()
    cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM tasks ORDER BY category").fetchall()]
    conn.close()
    return jsonify(cats)


# ── Frontend (single-page app, served from Python) ───────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Task Management System</title>
<style>
  :root {
    --purple:   #534AB7;
    --purple-l: #EEEDFE;
    --teal:     #0F6E56;
    --teal-l:   #E1F5EE;
    --amber:    #BA7517;
    --amber-l:  #FAEEDA;
    --coral:    #993C1D;
    --coral-l:  #FAECE7;
    --gray:     #5F5E5A;
    --gray-l:   #F5F4F0;
    --gray-m:   #E8E6DF;
    --text:     #2C2C2A;
    --white:    #FFFFFF;
    --shadow:   0 2px 12px rgba(0,0,0,0.08);
    --radius:   10px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--gray-l); color: var(--text); min-height: 100vh; }

  /* ── Header ── */
  header {
    background: var(--purple); color: white;
    padding: 0 24px; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(83,74,183,.3);
    position: sticky; top: 0; z-index: 100;
  }
  header h1 { font-size: 17px; font-weight: 700; letter-spacing: -.3px; }
  header .subtitle { font-size: 11px; opacity: .7; margin-top: 2px; }
  .header-left { display: flex; align-items: center; gap: 12px; }
  .header-logo { width: 32px; height: 32px; background: rgba(255,255,255,.15);
                 border-radius: 8px; display: flex; align-items: center;
                 justify-content: center; font-size: 18px; }

  /* ── Layout ── */
  .layout { display: flex; min-height: calc(100vh - 56px); }
  aside {
    width: 220px; background: white; border-right: 1px solid var(--gray-m);
    padding: 16px 12px; flex-shrink: 0; position: sticky;
    top: 56px; height: calc(100vh - 56px); overflow-y: auto;
  }
  main { flex: 1; padding: 24px; overflow-y: auto; }

  /* ── Sidebar ── */
  .sidebar-section { margin-bottom: 20px; }
  .sidebar-label { font-size: 10px; font-weight: 700; letter-spacing: .8px;
                   color: var(--gray); text-transform: uppercase; margin-bottom: 6px;
                   padding: 0 6px; }
  .nav-item {
    display: flex; align-items: center; gap: 8px; padding: 7px 10px;
    border-radius: 7px; cursor: pointer; font-size: 13.5px; color: var(--gray);
    transition: all .15s; user-select: none;
  }
  .nav-item:hover { background: var(--gray-l); color: var(--text); }
  .nav-item.active { background: var(--purple-l); color: var(--purple); font-weight: 600; }
  .nav-item .badge {
    margin-left: auto; background: var(--gray-m); color: var(--gray);
    border-radius: 20px; padding: 1px 7px; font-size: 11px; font-weight: 600;
  }
  .nav-item.active .badge { background: var(--purple); color: white; }

  /* ── Stats bar ── */
  .stats-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .stat-card {
    background: white; border-radius: var(--radius); padding: 14px 16px;
    box-shadow: var(--shadow); border-left: 4px solid var(--gray-m);
    transition: transform .15s;
  }
  .stat-card:hover { transform: translateY(-2px); }
  .stat-card.purple { border-color: var(--purple); }
  .stat-card.teal   { border-color: var(--teal); }
  .stat-card.amber  { border-color: var(--amber); }
  .stat-card.coral  { border-color: var(--coral); }
  .stat-num { font-size: 26px; font-weight: 700; line-height: 1; }
  .stat-label { font-size: 12px; color: var(--gray); margin-top: 3px; }
  .stat-card.purple .stat-num { color: var(--purple); }
  .stat-card.teal   .stat-num { color: var(--teal); }
  .stat-card.amber  .stat-num { color: var(--amber); }
  .stat-card.coral  .stat-num { color: var(--coral); }

  /* ── Toolbar ── */
  .toolbar {
    display: flex; gap: 10px; align-items: center;
    background: white; padding: 10px 14px; border-radius: var(--radius);
    box-shadow: var(--shadow); margin-bottom: 16px; flex-wrap: wrap;
  }
  .toolbar input, .toolbar select {
    border: 1.5px solid var(--gray-m); border-radius: 7px;
    padding: 7px 10px; font-size: 13px; color: var(--text);
    background: var(--gray-l); outline: none; transition: border .15s;
  }
  .toolbar input:focus, .toolbar select:focus { border-color: var(--purple); background: white; }
  .toolbar input { flex: 1; min-width: 180px; }
  .btn {
    padding: 8px 16px; border-radius: 7px; border: none; cursor: pointer;
    font-size: 13px; font-weight: 600; transition: all .15s; white-space: nowrap;
  }
  .btn-primary { background: var(--purple); color: white; }
  .btn-primary:hover { background: #4339a3; }
  .btn-sm { padding: 5px 10px; font-size: 12px; border-radius: 6px; }
  .btn-ghost { background: transparent; color: var(--gray); border: 1.5px solid var(--gray-m); }
  .btn-ghost:hover { background: var(--gray-l); color: var(--text); }
  .btn-danger { background: var(--coral-l); color: var(--coral); border: 1.5px solid var(--coral); }
  .btn-danger:hover { background: var(--coral); color: white; }

  /* ── Task table ── */
  .task-table-wrap { background: white; border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    background: var(--gray-l); padding: 10px 14px; text-align: left;
    font-size: 11.5px; font-weight: 700; letter-spacing: .5px;
    color: var(--gray); text-transform: uppercase; border-bottom: 1px solid var(--gray-m);
  }
  tbody tr { border-bottom: 1px solid var(--gray-m); transition: background .12s; }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: #FAFAF8; }
  tbody td { padding: 11px 14px; font-size: 13.5px; vertical-align: middle; }
  .task-title { font-weight: 600; color: var(--text); }
  .task-desc { font-size: 12px; color: var(--gray); margin-top: 2px; }
  .task-meta { font-size: 11px; color: var(--gray); }

  /* ── Status badges ── */
  .badge-status {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 600;
  }
  .badge-status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; }
  .status-Pending     { background: var(--amber-l); color: var(--amber); }
  .status-Pending::before { background: var(--amber); }
  .status-InProgress  { background: var(--purple-l); color: var(--purple); }
  .status-InProgress::before { background: var(--purple); }
  .status-Completed   { background: var(--teal-l); color: var(--teal); }
  .status-Completed::before { background: var(--teal); }
  .status-Cancelled   { background: var(--gray-l); color: var(--gray); }
  .status-Cancelled::before { background: var(--gray); }

  /* ── Priority badges ── */
  .badge-priority {
    display: inline-block; padding: 2px 8px; border-radius: 5px;
    font-size: 11px; font-weight: 700;
  }
  .prio-High   { background: var(--coral-l); color: var(--coral); }
  .prio-Medium { background: var(--amber-l); color: var(--amber); }
  .prio-Low    { background: var(--teal-l);  color: var(--teal); }

  /* ── Action buttons in row ── */
  .row-actions { display: flex; gap: 5px; }

  /* ── Modal ── */
  .overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,.35); z-index: 200;
    align-items: center; justify-content: center;
  }
  .overlay.open { display: flex; }
  .modal {
    background: white; border-radius: 14px; width: 480px; max-width: 96vw;
    box-shadow: 0 20px 60px rgba(0,0,0,.2); animation: slideUp .2s ease;
    max-height: 90vh; overflow-y: auto;
  }
  @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } }
  .modal-header {
    padding: 18px 20px 14px; border-bottom: 1px solid var(--gray-m);
    display: flex; justify-content: space-between; align-items: center;
  }
  .modal-header h2 { font-size: 16px; }
  .modal-close { background: none; border: none; font-size: 20px; cursor: pointer;
                 color: var(--gray); line-height: 1; padding: 2px 6px; border-radius: 5px; }
  .modal-close:hover { background: var(--gray-l); }
  .modal-body { padding: 18px 20px; }
  .modal-footer { padding: 12px 20px; border-top: 1px solid var(--gray-m);
                  display: flex; gap: 8px; justify-content: flex-end; }

  /* ── Form ── */
  .form-group { margin-bottom: 14px; }
  label { font-size: 12.5px; font-weight: 600; color: var(--gray); display: block; margin-bottom: 5px; }
  .form-control {
    width: 100%; border: 1.5px solid var(--gray-m); border-radius: 8px;
    padding: 8px 11px; font-size: 13.5px; color: var(--text);
    background: var(--gray-l); outline: none; transition: border .15s;
    font-family: inherit;
  }
  .form-control:focus { border-color: var(--purple); background: white; }
  textarea.form-control { resize: vertical; min-height: 72px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .error-msg { font-size: 12px; color: var(--coral); margin-top: 4px; }

  /* ── Status selector in edit ── */
  .status-flow { margin-bottom: 14px; }
  .status-flow-title { font-size: 12.5px; font-weight: 600; color: var(--gray); margin-bottom: 8px; }
  .status-pills { display: flex; gap: 6px; flex-wrap: wrap; }
  .status-pill {
    padding: 5px 13px; border-radius: 20px; font-size: 12px; font-weight: 600;
    cursor: pointer; border: 2px solid transparent; transition: all .15s; opacity: .5;
  }
  .status-pill.available { opacity: 1; }
  .status-pill.current { opacity: 1; border-color: currentColor; }
  .status-pill.selected { opacity: 1; border-color: currentColor; box-shadow: 0 0 0 2px currentColor; }

  /* ── Toast ── */
  #toast {
    position: fixed; bottom: 24px; right: 24px; z-index: 300;
    background: #2C2C2A; color: white; padding: 10px 18px;
    border-radius: 8px; font-size: 13.5px; font-weight: 500;
    opacity: 0; transform: translateY(10px); transition: all .25s;
    pointer-events: none;
  }
  #toast.show { opacity: 1; transform: translateY(0); }
  #toast.success { background: var(--teal); }
  #toast.error   { background: var(--coral); }

  /* ── Empty state ── */
  .empty-state { text-align: center; padding: 60px 20px; color: var(--gray); }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  .empty-state h3 { font-size: 16px; margin-bottom: 6px; color: var(--text); }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    aside { display: none; }
    .stats-bar { grid-template-columns: repeat(2, 1fr); }
    .form-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<!-- Header -->
<header>
  <div class="header-left">
    <div class="header-logo">✓</div>
    <div>
      <h1>Smart Task Management System</h1>
      <div class="subtitle">Layered architecture · CRUD · State machine · ASR-compliant</div>
    </div>
  </div>
  <button class="btn btn-primary" onclick="openModal()">+ New Task</button>
</header>

<div class="layout">

  <!-- Sidebar -->
  <aside>
    <div class="sidebar-section">
      <div class="sidebar-label">Filter by Status</div>
      <div class="nav-item active" data-filter="status" data-value="" onclick="setFilter(this)">
        🗂 All Tasks <span class="badge" id="cnt-all">0</span>
      </div>
      <div class="nav-item" data-filter="status" data-value="Pending" onclick="setFilter(this)">
        ⏳ Pending <span class="badge" id="cnt-Pending">0</span>
      </div>
      <div class="nav-item" data-filter="status" data-value="In Progress" onclick="setFilter(this)">
        🔄 In Progress <span class="badge" id="cnt-InProgress">0</span>
      </div>
      <div class="nav-item" data-filter="status" data-value="Completed" onclick="setFilter(this)">
        ✅ Completed <span class="badge" id="cnt-Completed">0</span>
      </div>
      <div class="nav-item" data-filter="status" data-value="Cancelled" onclick="setFilter(this)">
        ❌ Cancelled <span class="badge" id="cnt-Cancelled">0</span>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-label">Priority</div>
      <div class="nav-item" data-filter="priority" data-value="High" onclick="setFilter(this)">
        🔴 High
      </div>
      <div class="nav-item" data-filter="priority" data-value="Medium" onclick="setFilter(this)">
        🟡 Medium
      </div>
      <div class="nav-item" data-filter="priority" data-value="Low" onclick="setFilter(this)">
        🟢 Low
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-label">Categories</div>
      <div id="cat-list"></div>
    </div>
  </aside>

  <!-- Main content -->
  <main>
    <!-- Stats -->
    <div class="stats-bar">
      <div class="stat-card purple">
        <div class="stat-num" id="stat-total">0</div>
        <div class="stat-label">Total Tasks</div>
      </div>
      <div class="stat-card amber">
        <div class="stat-num" id="stat-pending">0</div>
        <div class="stat-label">Pending</div>
      </div>
      <div class="stat-card teal">
        <div class="stat-num" id="stat-inprogress">0</div>
        <div class="stat-label">In Progress</div>
      </div>
      <div class="stat-card coral">
        <div class="stat-num" id="stat-completed">0</div>
        <div class="stat-label">Completed</div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <input type="text" id="search-input" placeholder="🔍  Search tasks..." oninput="loadTasks()">
      <select id="filter-priority" onchange="loadTasks()">
        <option value="">All Priorities</option>
        <option>High</option><option>Medium</option><option>Low</option>
      </select>
      <select id="filter-category" onchange="loadTasks()">
        <option value="">All Categories</option>
      </select>
      <button class="btn btn-ghost btn-sm" onclick="resetFilters()">Clear filters</button>
    </div>

    <!-- Task table -->
    <div class="task-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Category</th>
            <th>Created</th>
            <th>Updated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="task-tbody">
          <tr><td colspan="7" class="empty-state">Loading…</td></tr>
        </tbody>
      </table>
    </div>
  </main>
</div>

<!-- Create / Edit Modal -->
<div class="overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header">
      <h2 id="modal-title">New Task</h2>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body">
      <div id="modal-error" class="error-msg" style="margin-bottom:10px;display:none;"></div>

      <!-- Status flow (edit mode only) -->
      <div class="status-flow" id="status-flow-section" style="display:none;">
        <div class="status-flow-title">Status transition</div>
        <div class="status-pills" id="status-pills"></div>
      </div>

      <div class="form-group">
        <label for="f-title">Title <span style="color:var(--coral)">*</span></label>
        <input type="text" id="f-title" class="form-control" placeholder="Task title" maxlength="120">
      </div>
      <div class="form-group">
        <label for="f-desc">Description</label>
        <textarea id="f-desc" class="form-control" placeholder="Optional details…"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label for="f-priority">Priority</label>
          <select id="f-priority" class="form-control">
            <option>High</option><option selected>Medium</option><option>Low</option>
          </select>
        </div>
        <div class="form-group">
          <label for="f-category">Category</label>
          <input type="text" id="f-category" class="form-control" placeholder="e.g. Frontend">
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" id="modal-save-btn" onclick="saveTask()">Create Task</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div id="toast"></div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
let activeFilters = { status: '', priority: '', category: '', search: '' };
let editingId = null;
let editingCurrentStatus = null;
let selectedStatus = null;

const TRANSITIONS = {
  'Pending':     ['In Progress', 'Cancelled'],
  'In Progress': ['Completed', 'Pending', 'Cancelled'],
  'Completed':   ['Pending'],
  'Cancelled':   ['Pending'],
};
const STATUS_COLORS = {
  'Pending':     'var(--amber)',
  'In Progress': 'var(--purple)',
  'Completed':   'var(--teal)',
  'Cancelled':   'var(--gray)',
};

// ── API helpers ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'show ' + type;
  setTimeout(() => { el.className = ''; }, 2800);
}

// ── Load tasks ───────────────────────────────────────────────────────────────
async function loadTasks() {
  const search   = document.getElementById('search-input').value;
  const priority = document.getElementById('filter-priority').value;
  const category = document.getElementById('filter-category').value;
  const params   = new URLSearchParams();
  if (activeFilters.status)   params.set('status',   activeFilters.status);
  if (priority)               params.set('priority', priority);
  if (category)               params.set('category', category);
  if (search)                 params.set('search',   search);

  const tasks = await api('GET', '/api/tasks?' + params.toString());
  renderTable(tasks);
}

function renderTable(tasks) {
  const tbody = document.getElementById('task-tbody');
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="7">
      <div class="empty-state">
        <div class="icon">📭</div>
        <h3>No tasks found</h3>
        <p>Try adjusting your filters or create a new task.</p>
      </div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => {
    const statusKey = t.status.replace(' ', '');
    const created   = t.created_at.split(' ')[0];
    const updated   = t.updated_at.split(' ')[0];
    return `<tr>
      <td>
        <div class="task-title">${esc(t.title)}</div>
        ${t.description ? `<div class="task-desc">${esc(t.description.substring(0,80))}${t.description.length>80?'…':''}</div>` : ''}
      </td>
      <td><span class="badge-status status-${statusKey}">${t.status}</span></td>
      <td><span class="badge-priority prio-${t.priority}">${t.priority}</span></td>
      <td><span style="font-size:12px">${esc(t.category)}</span></td>
      <td class="task-meta">${created}</td>
      <td class="task-meta">${updated}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-ghost btn-sm" onclick="openEdit(${t.id})">✏️ Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTask(${t.id}, '${esc(t.title)}')">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Stats ────────────────────────────────────────────────────────────────────
async function loadStats() {
  const s = await api('GET', '/api/stats');
  document.getElementById('stat-total').textContent      = s.total;
  document.getElementById('stat-pending').textContent    = s.by_status['Pending']     || 0;
  document.getElementById('stat-inprogress').textContent = s.by_status['In Progress'] || 0;
  document.getElementById('stat-completed').textContent  = s.by_status['Completed']   || 0;
  document.getElementById('cnt-all').textContent         = s.total;
  document.getElementById('cnt-Pending').textContent     = s.by_status['Pending']     || 0;
  document.getElementById('cnt-InProgress').textContent  = s.by_status['In Progress'] || 0;
  document.getElementById('cnt-Completed').textContent   = s.by_status['Completed']   || 0;
  document.getElementById('cnt-Cancelled').textContent   = s.by_status['Cancelled']   || 0;
}

// ── Categories ───────────────────────────────────────────────────────────────
async function loadCategories() {
  const cats = await api('GET', '/api/categories');
  const sel  = document.getElementById('filter-category');
  sel.innerHTML = '<option value="">All Categories</option>' +
    cats.map(c => `<option>${esc(c)}</option>`).join('');

  const list = document.getElementById('cat-list');
  list.innerHTML = cats.map(c =>
    `<div class="nav-item" data-filter="category" data-value="${esc(c)}" onclick="setFilter(this)">
       📁 ${esc(c)}
     </div>`).join('');
}

// ── Filter ───────────────────────────────────────────────────────────────────
function setFilter(el) {
  const filterType = el.dataset.filter;
  const value      = el.dataset.value;

  // Remove active from same filter type
  document.querySelectorAll(`[data-filter="${filterType}"]`).forEach(e => e.classList.remove('active'));
  el.classList.add('active');
  activeFilters[filterType] = value;

  document.getElementById('filter-priority').value = filterType === 'priority' ? value : '';
  document.getElementById('filter-category').value = filterType === 'category' ? value : '';

  loadTasks();
}

function resetFilters() {
  activeFilters = { status: '', priority: '', category: '', search: '' };
  document.getElementById('search-input').value    = '';
  document.getElementById('filter-priority').value = '';
  document.getElementById('filter-category').value = '';
  document.querySelectorAll('[data-filter="status"]').forEach(e => e.classList.remove('active'));
  document.querySelector('[data-filter="status"][data-value=""]').classList.add('active');
  loadTasks();
}

// ── Modal ────────────────────────────────────────────────────────────────────
function openModal() {
  editingId = null; editingCurrentStatus = null; selectedStatus = null;
  document.getElementById('modal-title').textContent    = 'New Task';
  document.getElementById('modal-save-btn').textContent = 'Create Task';
  document.getElementById('f-title').value     = '';
  document.getElementById('f-desc').value      = '';
  document.getElementById('f-priority').value  = 'Medium';
  document.getElementById('f-category').value  = '';
  document.getElementById('modal-error').style.display = 'none';
  document.getElementById('status-flow-section').style.display = 'none';
  document.getElementById('modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('f-title').focus(), 100);
}

async function openEdit(id) {
  const tasks = await api('GET', '/api/tasks');
  const t = tasks.find(x => x.id === id);
  if (!t) return;

  editingId            = id;
  editingCurrentStatus = t.status;
  selectedStatus       = t.status;

  document.getElementById('modal-title').textContent    = 'Edit Task';
  document.getElementById('modal-save-btn').textContent = 'Save Changes';
  document.getElementById('f-title').value    = t.title;
  document.getElementById('f-desc').value     = t.description;
  document.getElementById('f-priority').value = t.priority;
  document.getElementById('f-category').value = t.category;
  document.getElementById('modal-error').style.display = 'none';

  // Build status pills
  const section = document.getElementById('status-flow-section');
  const pills   = document.getElementById('status-pills');
  const allowed = TRANSITIONS[t.status] || [];
  const allStatuses = ['Pending', 'In Progress', 'Completed', 'Cancelled'];

  pills.innerHTML = allStatuses.map(s => {
    const isCurrent   = s === t.status;
    const isAvailable = allowed.includes(s);
    let cls = 'status-pill';
    if (isCurrent) cls += ' current selected';
    else if (isAvailable) cls += ' available';
    const col = STATUS_COLORS[s];
    return `<div class="${cls}" style="background:${col}22;color:${col}"
               onclick="selectStatus('${s}', ${isAvailable || isCurrent})">${s}</div>`;
  }).join('');

  section.style.display = 'block';
  document.getElementById('modal-overlay').classList.add('open');
}

function selectStatus(s, allowed) {
  if (!allowed) return;
  selectedStatus = s;
  document.querySelectorAll('.status-pill').forEach(el => {
    const isThis = el.textContent.trim() === s;
    el.classList.toggle('selected', isThis);
    if (!isThis && !el.classList.contains('current') && !el.classList.contains('available')) return;
  });
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').classList.remove('open');
}

// ── Save (create or update) ───────────────────────────────────────────────────
async function saveTask() {
  const errEl = document.getElementById('modal-error');
  errEl.style.display = 'none';

  const title    = document.getElementById('f-title').value.trim();
  const desc     = document.getElementById('f-desc').value.trim();
  const priority = document.getElementById('f-priority').value;
  const category = document.getElementById('f-category').value.trim() || 'General';

  if (!title) {
    errEl.textContent = 'Title is required.'; errEl.style.display = 'block'; return;
  }

  try {
    if (editingId) {
      await api('PUT', `/api/tasks/${editingId}`, {
        title, description: desc, status: selectedStatus || editingCurrentStatus,
        priority, category
      });
      toast('Task updated ✓');
    } else {
      await api('POST', '/api/tasks', { title, description: desc, priority, category });
      toast('Task created ✓');
    }
    document.getElementById('modal-overlay').classList.remove('open');
    await Promise.all([loadTasks(), loadStats(), loadCategories()]);
  } catch (err) {
    errEl.textContent = err.message; errEl.style.display = 'block';
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
async function deleteTask(id, title) {
  if (!confirm(`Delete "${title}"?`)) return;
  try {
    await api('DELETE', `/api/tasks/${id}`);
    toast('Task deleted', 'error');
    await Promise.all([loadTasks(), loadStats(), loadCategories()]);
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── Keyboard shortcut ────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('modal-overlay').classList.remove('open');
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); openModal(); }
});

// ── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  await Promise.all([loadTasks(), loadStats(), loadCategories()]);
})();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)


# ── Launcher ──────────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    init_db()
    print("\n" + "="*54)
    print("  Smart Task Management System")
    print("  Based on ASRS Architectural Design Document")
    print("="*54)
    print("  → http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop")
    print("="*54 + "\n")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, port=5000)
