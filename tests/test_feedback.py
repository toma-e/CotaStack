"""Test suite for user feedback collection module."""

from io import BytesIO
import json
from pathlib import Path
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from backend.feedback import (
    FeedbackItem,
    save_feedback,
    load_feedbacks,
    format_github_issue_content,
    build_github_issue_url,
    submit_github_issue,
)


class TestFeedbackModule:
    """Tests for feedback creation, serialization and storage."""

    def test_save_and_load_feedback(self, tmp_path: Path):
        fb_file = tmp_path / "feedbacks_test.jsonl"
        item = save_feedback(
            message="Excellente application, il faudrait ajouter l'export STEP.",
            feedback_type="suggestion",
            author_email="user@example.com",
            metadata={"source_page": "multi_chain"},
            filepath=fb_file,
        )

        assert item.message == "Excellente application, il faudrait ajouter l'export STEP."
        assert item.feedback_type == "suggestion"
        assert item.author_email == "user@example.com"
        assert item.metadata.get("source_page") == "multi_chain"

        loaded = load_feedbacks(fb_file)
        assert len(loaded) == 1
        assert loaded[0].message == item.message
        assert loaded[0].feedback_type == item.feedback_type
        assert loaded[0].author_email == item.author_email

    def test_empty_message_raises_value_error(self, tmp_path: Path):
        fb_file = tmp_path / "feedbacks_test.jsonl"
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            save_feedback("   ", filepath=fb_file)

        with pytest.raises(ValueError, match="ne peut pas être vide"):
            save_feedback("", filepath=fb_file)

    def test_load_feedbacks_non_existent_file(self, tmp_path: Path):
        fb_file = tmp_path / "does_not_exist.jsonl"
        assert load_feedbacks(fb_file) == []

    def test_load_feedbacks_ignores_corrupted_lines(self, tmp_path: Path):
        fb_file = tmp_path / "corrupted.jsonl"
        fb_file.write_text("valid line\n{invalid json\n{\"message\": \"OK\"}\n\n", encoding="utf-8")
        loaded = load_feedbacks(fb_file)
        assert len(loaded) == 1
        assert loaded[0].message == "OK"
        assert loaded[0].feedback_type == "suggestion"

    def test_feedback_item_to_dict_and_from_dict(self):
        item = FeedbackItem(
            timestamp="2026-10-30T22:00:00Z",
            feedback_type="bug",
            message="Erreur d'arrondi",
            author_email="test@cotastack.app",
            metadata={"browser": "chrome"},
        )
        d = item.to_dict()
        assert d["message"] == "Erreur d'arrondi"
        assert d["feedback_type"] == "bug"

        reconstructed = FeedbackItem.from_dict(d)
        assert reconstructed.message == item.message
        assert reconstructed.timestamp == item.timestamp
        assert reconstructed.metadata == item.metadata


class TestGitHubIssueIntegration:
    """Tests for formatting, URL generation, and GitHub REST API integration."""

    def test_format_github_issue_content(self):
        item = FeedbackItem(
            timestamp="2026-10-30T22:00:00Z",
            feedback_type="suggestion",
            message="Ajouter un export Excel XLS\nDeuxième ligne de détail",
            author_email="engineer@company.com",
            metadata={"page": "04_Multi_Chaines"},
        )
        title, body = format_github_issue_content(item)
        assert "[Retour Utilisateur]" in title
        assert "Ajouter un export Excel XLS" in title
        assert "engineer@company.com" in body
        assert "04_Multi_Chaines" in body
        assert "Deuxième ligne de détail" in body

    def test_format_anonymous_feedback(self):
        item = FeedbackItem(
            timestamp="2026-10-30T22:00:00Z",
            feedback_type="general",
            message="Avis court",
            author_email="",
        )
        title, body = format_github_issue_content(item)
        assert "Anonyme" in body

    def test_build_github_issue_url(self):
        url = build_github_issue_url(
            title="Titre Test",
            body="Description avec accents et espaces",
            repo="toma-e/CotaStack",
            labels=["user-feedback", "enhancement"],
        )
        assert url.startswith("https://github.com/toma-e/CotaStack/issues/new?")
        assert "Titre+Test" in url or "Titre%20Test" in url
        assert "labels=user-feedback%2Cenhancement" in url or "labels=user-feedback%2Cenhancement" in url or "labels=user-feedback" in url

    def test_submit_github_issue_empty_token_raises(self):
        with pytest.raises(ValueError, match="jeton d'accès GitHub"):
            submit_github_issue("Titre", "Corps", token="")

    @patch("urllib.request.urlopen")
    def test_submit_github_issue_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": 123456,
            "number": 42,
            "html_url": "https://github.com/toma-e/CotaStack/issues/42",
            "title": "Titre test",
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = submit_github_issue(
            title="Bug calcul",
            body="Détails du bug",
            token="ghp_fake_token_test",
            repo="toma-e/CotaStack",
        )

        assert res["number"] == 42
        assert res["html_url"] == "https://github.com/toma-e/CotaStack/issues/42"

    @patch("urllib.request.urlopen")
    def test_submit_github_issue_http_error(self, mock_urlopen):
        err_fp = BytesIO(b'{"message": "Bad credentials"}')
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.github.com/repos/toma-e/CotaStack/issues",
            code=401,
            msg="Unauthorized",
            hdrs=MagicMock(),
            fp=err_fp,
        )

        with pytest.raises(RuntimeError, match="Erreur GitHub API"):
            submit_github_issue(
                title="Bug",
                body="Détail",
                token="invalid_token",
            )

    @patch("urllib.request.urlopen")
    def test_submit_github_issue_generic_exception(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("Network down")
        with pytest.raises(RuntimeError, match="Échec de connexion"):
            submit_github_issue(
                title="Bug",
                body="Détail",
                token="dummy",
            )
