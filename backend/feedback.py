"""Feedback collection module for CotaStack.

Allows users to submit suggestions, bug reports, or feature requests.
Stores feedback locally in a JSONL file with ISO timestamps and privacy protections.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path


DEFAULT_FEEDBACK_FILE = Path("feedbacks.jsonl")


@dataclass(slots=True)
class FeedbackItem:
    """A user feedback entry."""
    timestamp: str
    feedback_type: str
    message: str
    author_email: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackItem":
        return cls(
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            feedback_type=data.get("feedback_type", "suggestion"),
            message=data.get("message", "").strip(),
            author_email=data.get("author_email", "").strip(),
            metadata=data.get("metadata", {}),
        )


def save_feedback(
    message: str,
    feedback_type: str = "suggestion",
    author_email: str = "",
    metadata: dict | None = None,
    filepath: Path | str = DEFAULT_FEEDBACK_FILE,
) -> FeedbackItem:
    """Save a user feedback entry to the specified JSONL file."""
    clean_msg = str(message or "").strip()
    if not clean_msg:
        raise ValueError("Le message de commentaire ne peut pas être vide.")

    item = FeedbackItem(
        timestamp=datetime.now(timezone.utc).isoformat(),
        feedback_type=str(feedback_type).strip() or "suggestion",
        message=clean_msg,
        author_email=str(author_email or "").strip(),
        metadata=metadata or {},
    )

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")

    return item


def load_feedbacks(filepath: Path | str = DEFAULT_FEEDBACK_FILE) -> list[FeedbackItem]:
    """Load all feedback entries from a JSONL file."""
    path = Path(filepath)
    if not path.exists():
        return []

    items: list[FeedbackItem] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if isinstance(data, dict):
                    items.append(FeedbackItem.from_dict(data))
            except Exception:
                continue

    return items
