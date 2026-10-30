"""Feedback collection module for CotaStack.

Allows users to submit suggestions, bug reports, or feature requests.
Stores feedback locally in a JSONL file with ISO timestamps and privacy protections,
and provides GitHub Issues integration for centralized public or private tracking.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error


DEFAULT_FEEDBACK_FILE = Path("feedbacks.jsonl")
DEFAULT_GITHUB_REPO = "toma-e/CotaStack"


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


def format_github_issue_content(item: FeedbackItem) -> tuple[str, str]:
    """Format title and markdown body for a GitHub issue from a FeedbackItem."""
    type_labels = {
        "suggestion": "💡 Suggestion",
        "bug": "🐞 Signalement Bug",
        "feature": "✨ Fonctionnalité",
        "general": "🌟 Retour utilisateur",
    }
    label = type_labels.get(item.feedback_type.lower(), f"💬 {item.feedback_type.capitalize()}")

    # Build concise excerpt for the title
    first_line = item.message.split("\n")[0].strip()
    excerpt = (first_line[:50] + "...") if len(first_line) > 50 else first_line
    title = f"[Retour Utilisateur] {label} : {excerpt}"

    body_lines = [
        "### 💬 Nouveau retour utilisateur CotaStack",
        "",
        f"- **Type** : {label}",
        f"- **Horodatage (UTC)** : `{item.timestamp}`",
        f"- **Contact / E-mail** : `{item.author_email}`" if item.author_email else "- **Contact** : *Non communiqué (Anonyme)*",
    ]

    for k, v in item.metadata.items():
        body_lines.append(f"- **{k}** : `{v}`")

    body_lines.extend([
        "",
        "---",
        "",
        "### 📝 Message / Besoin exprimé :",
        "",
        item.message,
        "",
        "---",
        "*Soumis directement depuis l'application CotaStack.*",
    ])

    return title, "\n".join(body_lines)


def build_github_issue_url(
    title: str,
    body: str,
    repo: str = DEFAULT_GITHUB_REPO,
    labels: list[str] | None = None,
) -> str:
    """Build a pre-filled GitHub web URL to open the issue creation page."""
    base = f"https://github.com/{repo}/issues/new"
    query_params: dict[str, str] = {
        "title": title,
        "body": body,
    }
    if labels:
        query_params["labels"] = ",".join(labels)

    return f"{base}?{urllib.parse.urlencode(query_params)}"


def submit_github_issue(
    title: str,
    body: str,
    token: str,
    repo: str = DEFAULT_GITHUB_REPO,
    labels: list[str] | None = None,
) -> dict:
    """Create a new GitHub issue in the target repository using the official GitHub REST API."""
    clean_token = str(token or "").strip()
    if not clean_token:
        raise ValueError("Le jeton d'accès GitHub (GITHUB_TOKEN) est manquant ou vide.")

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "CotaStack-Feedback-Client",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "body": body,
        "labels": labels or ["user-feedback"],
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return {
                "id": res_data.get("id"),
                "number": res_data.get("number"),
                "html_url": res_data.get("html_url"),
                "title": res_data.get("title"),
            }
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"Erreur GitHub API ({e.code}) : {err_msg}") from e
    except Exception as e:
        raise RuntimeError(f"Échec de connexion à GitHub : {e}") from e
