"""
Unit tests for business logic and API routes.
Run:  python -m pytest tests/
"""

import json
import os
import sys
import tempfile

import pytest

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database
from app import app as flask_app
from logic import is_valid_transition, validate_task_data


# ── Logic tests ───────────────────────────────────────────────────────────────

class TestStateMachine:
    def test_pending_to_in_progress(self):
        assert is_valid_transition("Pending", "In Progress") is True

    def test_pending_to_cancelled(self):
        assert is_valid_transition("Pending", "Cancelled") is True

    def test_pending_to_completed_invalid(self):
        assert is_valid_transition("Pending", "Completed") is False

    def test_in_progress_to_completed(self):
        assert is_valid_transition("In Progress", "Completed") is True

    def test_completed_to_pending(self):
        assert is_valid_transition("Completed", "Pending") is True

    def test_completed_to_cancelled_invalid(self):
        assert is_valid_transition("Completed", "Cancelled") is False

    def test_unknown_status(self):
        assert is_valid_transition("Unknown", "Pending") is False


class TestValidation:
    def test_valid_task(self):
        assert validate_task_data({"title": "My task", "priority": "High"}) is None

    def test_empty_title(self):
        assert validate_task_data({"title": "", "priority": "High"}) is not None

    def test_title_too_long(self):
        assert validate_task_data({"title": "x" * 121, "priority": "Medium"}) is not None

    def test_invalid_priority(self):
        assert validate_task_data({"title": "Task", "priority": "Critical"}) is not None

    def test_update_skips_missing_title(self):
        # On update, title key absence should not fail
        assert validate_task_data({"priority": "Low"}, is_update=True) is None


# ── API tests ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path):
    """Isolated Flask test client with a fresh temp database."""
    db_file = str(tmp_path / "test_tasks.db")
    database.DB_PATH = db_file
    database.init_db()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestTaskAPI:
    def test_get_tasks_empty_after_seed(self, client):
        rv = client.get("/api/tasks")
        assert rv.status_code == 200
        data = json.loads(rv.data)
        assert isinstance(data, list)

    def test_create_task(self, client):
        rv = client.post(
            "/api/tasks",
            json={"title": "Test task", "priority": "High", "category": "Testing"},
        )
        assert rv.status_code == 201
        body = json.loads(rv.data)
        assert body["title"] == "Test task"
        assert body["status"] == "Pending"

    def test_create_task_missing_title(self, client):
        rv = client.post("/api/tasks", json={"priority": "Low"})
        assert rv.status_code == 400

    def test_update_task_status(self, client):
        # Create first
        create_rv = client.post("/api/tasks", json={"title": "T", "priority": "Medium"})
        task_id = json.loads(create_rv.data)["id"]

        # Valid transition: Pending → In Progress
        rv = client.put(f"/api/tasks/{task_id}", json={"status": "In Progress"})
        assert rv.status_code == 200
        assert json.loads(rv.data)["status"] == "In Progress"

    def test_invalid_status_transition(self, client):
        create_rv = client.post("/api/tasks", json={"title": "T", "priority": "Medium"})
        task_id = json.loads(create_rv.data)["id"]

        # Invalid: Pending → Completed
        rv = client.put(f"/api/tasks/{task_id}", json={"status": "Completed"})
        assert rv.status_code == 400

    def test_delete_task(self, client):
        create_rv = client.post("/api/tasks", json={"title": "T", "priority": "Low"})
        task_id = json.loads(create_rv.data)["id"]

        rv = client.delete(f"/api/tasks/{task_id}")
        assert rv.status_code == 200

        rv2 = client.delete(f"/api/tasks/{task_id}")
        assert rv2.status_code == 404

    def test_stats_endpoint(self, client):
        rv = client.get("/api/stats")
        assert rv.status_code == 200
        body = json.loads(rv.data)
        assert "total" in body
        assert "by_status" in body
