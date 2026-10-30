"""Test suite for user feedback collection module."""

import pytest
from pathlib import Path
from backend.feedback import FeedbackItem, save_feedback, load_feedbacks


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
