"""
REST API routes — registered on the Flask app via register_routes().
"""

from datetime import datetime

from flask import Flask, jsonify, render_template, request

from database import get_db, row_to_dict
from logic import is_valid_transition, validate_task_data


def register_routes(app: Flask) -> None:

    # ── Frontend ──────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("index.html")

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @app.route("/api/tasks", methods=["GET"])
    def get_tasks():
        status   = request.args.get("status",   "")
        priority = request.args.get("priority", "")
        category = request.args.get("category", "")
        search   = request.args.get("search",   "")

        query  = "SELECT * FROM tasks WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?";   params.append(status)
        if priority:
            query += " AND priority = ?"; params.append(priority)
        if category:
            query += " AND category = ?"; params.append(category)
        if search:
            query += " AND (title LIKE ? OR description LIKE ?)";  params += [f"%{search}%", f"%{search}%"]

        query += " ORDER BY created_at DESC"

        conn  = get_db()
        tasks = [row_to_dict(r) for r in conn.execute(query, params).fetchall()]
        conn.close()
        return jsonify(tasks)

    @app.route("/api/tasks", methods=["POST"])
    def create_task():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        err = validate_task_data(data)
        if err:
            return jsonify({"error": err}), 400

        now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        cur  = conn.execute(
            "INSERT INTO tasks (title,description,status,priority,category,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                data["title"].strip(),
                data.get("description", "").strip(),
                "Pending",
                data.get("priority", "Medium"),
                data.get("category", "General").strip() or "General",
                now, now,
            ),
        )
        conn.commit()
        task = row_to_dict(conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone())
        conn.close()
        return jsonify(task), 201

    @app.route("/api/tasks/<int:task_id>", methods=["PUT"])
    def update_task(task_id: int):
        data = request.get_json()
        conn = get_db()
        row  = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Task not found"}), 404

        current = row_to_dict(row)

        # State-machine transition check
        new_status = data.get("status", current["status"])
        if new_status != current["status"] and not is_valid_transition(current["status"], new_status):
            conn.close()
            return jsonify({"error": f"Invalid transition: {current['status']} → {new_status}"}), 400

        err = validate_task_data(data, is_update=True)
        if err:
            conn.close()
            return jsonify({"error": err}), 400

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE tasks SET title=?,description=?,status=?,priority=?,category=?,updated_at=? WHERE id=?",
            (
                data.get("title",       current["title"]).strip(),
                data.get("description", current["description"]).strip(),
                new_status,
                data.get("priority",    current["priority"]),
                (data.get("category",   current["category"]).strip() or "General"),
                now,
                task_id,
            ),
        )
        conn.commit()
        task = row_to_dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
        conn.close()
        return jsonify(task)

    @app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
    def delete_task(task_id: int):
        conn = get_db()
        row  = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Deleted", "id": task_id})

    # ── Stats & categories ────────────────────────────────────────────────────

    @app.route("/api/stats", methods=["GET"])
    def stats():
        conn      = get_db()
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
        cats = [r[0] for r in
                conn.execute("SELECT DISTINCT category FROM tasks ORDER BY category").fetchall()]
        conn.close()
        return jsonify(cats)
