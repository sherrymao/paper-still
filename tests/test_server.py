"""Tests for Flask server API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.server import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with isolated notebooks, notes, and briefings."""
    nb_path = tmp_path / "notebooks.yaml"
    notes_path = tmp_path / "notes.yaml"
    monkeypatch.setattr("scripts.notebook_store.NOTEBOOKS_PATH", nb_path)
    monkeypatch.setattr("scripts.notes_store.NOTES_PATH", notes_path)
    monkeypatch.setattr("scripts.briefing.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("scripts.server.OUTPUT_DIR", tmp_path)
    rn_path = tmp_path / "random_notes.yaml"
    monkeypatch.setattr("scripts.random_notes_store.RANDOM_NOTES_PATH", rn_path)
    adj_path = tmp_path / "score_adjustments.yaml"
    monkeypatch.setattr("scripts.score_adjustments_store.ADJUSTMENTS_PATH", adj_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_api_papers(client):
    resp = client.get("/api/papers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    # Each entry should have score, id, and fetch_batch
    if data:
        assert "score" in data[0]
        assert "id" in data[0]
        assert "fetch_batch" in data[0]


def test_api_notebooks_empty(client):
    resp = client.get("/api/notebooks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_api_notebook_generate(client):
    # Use real paper IDs from the data
    resp = client.get("/api/papers")
    papers = resp.get_json()
    if not papers:
        pytest.skip("No papers loaded")
    paper_ids = [papers[0]["id"]]

    resp = client.post("/api/notebook/generate",
                       data=json.dumps({"paper_ids": paper_ids, "name": "Test NB"}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["notebook_id"] == "nb-001"
    assert data["paper_count"] == 1
    assert "markdown" in data
    assert isinstance(data["urls"], list)


def test_api_notebook_generate_empty(client):
    resp = client.post("/api/notebook/generate",
                       data=json.dumps({"paper_ids": []}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_notebook_register(client):
    # Create a notebook first
    resp = client.get("/api/papers")
    papers = resp.get_json()
    if not papers:
        pytest.skip("No papers loaded")

    client.post("/api/notebook/generate",
                data=json.dumps({"paper_ids": [papers[0]["id"]], "name": "Test"}),
                content_type="application/json")

    # Register URL
    resp = client.post("/api/notebook/register",
                       data=json.dumps({"id": "nb-001", "url": "https://notebooklm.google.com/nb/123"}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["url"] == "https://notebooklm.google.com/nb/123"


def test_api_notebook_register_not_found(client):
    resp = client.post("/api/notebook/register",
                       data=json.dumps({"id": "nb-999", "url": "http://x.com"}),
                       content_type="application/json")
    assert resp.status_code == 404


def test_api_notebook_register_no_id(client):
    resp = client.post("/api/notebook/register",
                       data=json.dumps({"url": "http://x.com"}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_notes_empty(client):
    resp = client.get("/api/notes")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_api_save_note(client):
    resp = client.post("/api/notes",
                       data=json.dumps({"paper_id": "post_training-2026-001", "text": "Good paper"}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["paper_id"] == "post_training-2026-001"
    assert data["text"] == "Good paper"

    # Verify via GET
    resp = client.get("/api/notes")
    notes = resp.get_json()
    assert notes["post_training-2026-001"] == "Good paper"


def test_api_save_note_no_id(client):
    resp = client.post("/api/notes",
                       data=json.dumps({"text": "orphan note"}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_delete_note(client):
    client.post("/api/notes",
                data=json.dumps({"paper_id": "post_training-2026-001", "text": "To delete"}),
                content_type="application/json")
    resp = client.post("/api/notes",
                       data=json.dumps({"paper_id": "post_training-2026-001", "text": ""}),
                       content_type="application/json")
    assert resp.status_code == 200
    notes = client.get("/api/notes").get_json()
    assert "post_training-2026-001" not in notes


def test_api_briefing_generate(client):
    resp = client.get("/api/papers")
    papers = resp.get_json()
    if not papers:
        pytest.skip("No papers loaded")
    paper_ids = [papers[0]["id"]]

    resp = client.post("/api/briefing/generate",
                       data=json.dumps({"paper_ids": paper_ids, "title": "Test Briefing"}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["paper_count"] == 1
    assert data["filename"].startswith("test-briefing-")
    assert data["filename"].endswith(".html")


def test_api_briefing_generate_empty(client):
    resp = client.post("/api/briefing/generate",
                       data=json.dumps({"paper_ids": []}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_serve_briefing(client):
    resp = client.get("/api/papers")
    papers = resp.get_json()
    if not papers:
        pytest.skip("No papers loaded")
    paper_ids = [papers[0]["id"]]

    gen_resp = client.post("/api/briefing/generate",
                           data=json.dumps({"paper_ids": paper_ids, "title": "Serve Test"}),
                           content_type="application/json")
    filename = gen_resp.get_json()["filename"]

    resp = client.get(f"/briefing/{filename}")
    assert resp.status_code == 200
    assert b"Serve Test" in resp.data


def test_api_random_notes_empty(client):
    resp = client.get("/api/random-notes")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_api_save_random_note(client):
    resp = client.post("/api/random-notes",
                       data=json.dumps({"text": "A random thought", "tags": ["idea", "rlhf"]}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["text"] == "A random thought"
    assert data["tags"] == ["idea", "rlhf"]
    assert data["id"].startswith("rn-")

    # Verify via GET
    notes = client.get("/api/random-notes").get_json()
    assert len(notes) == 1
    assert notes[0]["text"] == "A random thought"


def test_api_save_random_note_empty(client):
    resp = client.post("/api/random-notes",
                       data=json.dumps({"text": "  "}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_update_random_note(client):
    resp = client.post("/api/random-notes",
                       data=json.dumps({"text": "First"}),
                       content_type="application/json")
    note_id = resp.get_json()["id"]

    resp = client.post("/api/random-notes",
                       data=json.dumps({"id": note_id, "text": "Updated", "tags": ["v2"]}),
                       content_type="application/json")
    assert resp.status_code == 200
    assert resp.get_json()["text"] == "Updated"

    notes = client.get("/api/random-notes").get_json()
    assert len(notes) == 1


def test_api_delete_random_note(client):
    resp = client.post("/api/random-notes",
                       data=json.dumps({"text": "To delete"}),
                       content_type="application/json")
    note_id = resp.get_json()["id"]

    resp = client.delete(f"/api/random-notes/{note_id}")
    assert resp.status_code == 200

    notes = client.get("/api/random-notes").get_json()
    assert len(notes) == 0


def test_api_delete_random_note_not_found(client):
    resp = client.delete("/api/random-notes/rn-fake")
    assert resp.status_code == 404


# --- Add Paper by URL tests ---

def test_api_add_paper_no_url(client):
    resp = client.post("/api/add-paper",
                       data=json.dumps({"url": "", "direction": "post_training"}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_add_paper_invalid_direction(client):
    resp = client.post("/api/add-paper",
                       data=json.dumps({"url": "https://arxiv.org/abs/2501.12345", "direction": "invalid"}),
                       content_type="application/json")
    assert resp.status_code == 400


# --- Delete Papers API tests ---

def test_api_delete_papers_empty(client):
    resp = client.post("/api/papers/delete",
                       data=json.dumps({"paper_ids": []}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_delete_papers_nonexistent(client):
    resp = client.post("/api/papers/delete",
                       data=json.dumps({"paper_ids": ["fake-id-001"]}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["deleted"] == 0


# --- Score Adjustments API tests ---

def test_api_score_adjustments_empty(client):
    resp = client.get("/api/score-adjustments")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_api_save_score_adjustment(client):
    resp = client.post("/api/score-adjustments",
                       data=json.dumps({"paper_id": "test-001", "score": 85.5}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["paper_id"] == "test-001"
    assert data["score"] == 85.5

    # Verify via GET
    resp = client.get("/api/score-adjustments")
    adj = resp.get_json()
    assert adj["test-001"] == 85.5


def test_api_delete_score_adjustment(client):
    client.post("/api/score-adjustments",
                data=json.dumps({"paper_id": "test-001", "score": 85.5}),
                content_type="application/json")
    resp = client.post("/api/score-adjustments",
                       data=json.dumps({"paper_id": "test-001", "score": None}),
                       content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["deleted"] is True

    adj = client.get("/api/score-adjustments").get_json()
    assert "test-001" not in adj


def test_api_score_adjustment_no_paper_id(client):
    resp = client.post("/api/score-adjustments",
                       data=json.dumps({"score": 50}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_score_adjustment_invalid_score(client):
    resp = client.post("/api/score-adjustments",
                       data=json.dumps({"paper_id": "test-001", "score": "abc"}),
                       content_type="application/json")
    assert resp.status_code == 400


def test_api_papers_include_adjustment_fields(client):
    resp = client.get("/api/papers")
    data = resp.get_json()
    if data:
        assert "computed_score" in data[0]
        assert "score_adjusted" in data[0]
