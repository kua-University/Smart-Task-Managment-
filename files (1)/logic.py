"""
Business logic — state-machine transitions (ASR state machine).
"""

VALID_TRANSITIONS: dict[str, list[str]] = {
    "Pending":     ["In Progress", "Cancelled"],
    "In Progress": ["Completed",   "Pending",   "Cancelled"],
    "Completed":   ["Pending"],
    "Cancelled":   ["Pending"],
}

VALID_PRIORITIES = ("High", "Medium", "Low")


def is_valid_transition(current: str, new: str) -> bool:
    """Return True if the status change from *current* to *new* is allowed."""
    return new in VALID_TRANSITIONS.get(current, [])


def validate_task_data(data: dict, is_update: bool = False) -> str | None:
    """
    Validate task payload.  Returns an error string or None if valid.
    """
    title = data.get("title", "")
    if not is_update or "title" in data:
        if not str(title).strip():
            return "Title is required"
        if len(title) > 120:
            return "Title must be 120 characters or fewer"

    if "priority" in data and data["priority"] not in VALID_PRIORITIES:
        return "Invalid priority"

    return None
