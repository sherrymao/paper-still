"""Tests for fetch and ingest scripts."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fetch import _extract_arxiv_id, _title_similar, _first_sentence, _parse_arxiv_url, _openalex_work_to_paper, _scrape_webpage_meta
from scripts.ingest import load_candidate_file, get_next_seq, delete_papers


def test_extract_arxiv_id_url():
    assert _extract_arxiv_id("http://arxiv.org/abs/2501.12345v1") == "2501.12345"


def test_extract_arxiv_id_short():
    assert _extract_arxiv_id("2603.22283") == "2603.22283"


def test_extract_arxiv_id_no_version():
    assert _extract_arxiv_id("http://arxiv.org/abs/2501.12345") == "2501.12345"


def test_title_similar_exact():
    assert _title_similar("Hello World", "Hello World") is True


def test_title_similar_case_insensitive():
    assert _title_similar("Hello World", "hello world") is True


def test_title_similar_different():
    assert _title_similar("Hello World", "Goodbye Moon") is False


def test_title_similar_minor_diff():
    assert _title_similar(
        "A Comprehensive Study of RLHF Training Methods",
        "A Comprehensive Study of RLHF Training Method"
    ) is True  # nearly identical


def test_first_sentence_normal():
    assert _first_sentence("This is a test. More text here.") == "This is a test."


def test_first_sentence_no_period():
    result = _first_sentence("This has no period ending")
    assert len(result) > 0


def test_first_sentence_empty():
    assert _first_sentence("") == ""


def test_first_sentence_question():
    assert _first_sentence("Can this work? We think so.") == "Can this work?"


def test_load_candidate_file(tmp_path):
    f = tmp_path / "test.yaml"
    data = {
        'papers': [
            {'id': 'test-001', 'title': 'Test', 'direction': 'post_training'},
            {'id': 'test-002', 'title': 'Test2', 'direction': 'post_training'},
        ]
    }
    with open(f, 'w') as fh:
        yaml.dump(data, fh)
    direction, papers, query = load_candidate_file(f)
    assert direction == 'post_training'
    assert len(papers) == 2
    assert query == ''


def test_load_candidate_file_empty(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("")
    direction, papers, query = load_candidate_file(f)
    assert direction == ''
    assert papers == []
    assert query == ''


def test_get_next_seq_basic():
    existing = {'post_training-2026-001', 'post_training-2026-002', 'post_training-2026-003'}
    assert get_next_seq('post_training', 2026, existing) == 4


def test_get_next_seq_empty():
    assert get_next_seq('post_training', 2026, set()) == 1


def test_get_next_seq_ignores_other_directions():
    existing = {'world_models-2026-010', 'post_training-2026-003'}
    assert get_next_seq('post_training', 2026, existing) == 4


def test_get_next_seq_non_numeric_ids():
    # IDs from fetch have non-standard format like post_training-2026-260322283
    # get_next_seq should handle them gracefully
    existing = {'post_training-2026-260322283', 'post_training-2026-003'}
    seq = get_next_seq('post_training', 2026, existing)
    # Should still find 003 as max parseable seq
    # 260322283 is also parseable as int, so it becomes the max
    assert seq >= 4  # at least after 003


# --- fetch_paper_by_url tests ---

def test_parse_arxiv_url_abs():
    assert _parse_arxiv_url("https://arxiv.org/abs/2501.12345") == "2501.12345"


def test_parse_arxiv_url_pdf():
    assert _parse_arxiv_url("https://arxiv.org/pdf/2501.12345") == "2501.12345"


def test_parse_arxiv_url_non_arxiv():
    assert _parse_arxiv_url("https://example.com/paper/123") is None


def test_parse_arxiv_url_with_version():
    assert _parse_arxiv_url("https://arxiv.org/abs/2501.12345v2") == "2501.12345"


def test_openalex_work_to_paper_basic():
    work = {
        'display_name': 'Test Paper Title',
        'publication_date': '2026-01-15',
        'locations': [
            {'landing_page_url': 'https://arxiv.org/abs/2601.00001'}
        ],
        'authorships': [
            {'author': {'display_name': 'Alice'}, 'institutions': [{'display_name': 'MIT'}]},
            {'author': {'display_name': 'Bob'}, 'institutions': []},
        ],
        'abstract_inverted_index': {'Hello': [0], 'world': [1]},
        'cited_by_count': 42,
    }
    paper = _openalex_work_to_paper(work, 'post_training', ['MIT'])
    assert paper['title'] == 'Test Paper Title'
    assert paper['direction'] == 'post_training'
    assert paper['citations'] == 42
    assert paper['authors'] == ['Alice', 'Bob']
    assert 'MIT' in paper['affiliations']
    assert paper['links']['paper'] == 'https://arxiv.org/abs/2601.00001'
    assert paper['core_contribution']  # should have extracted first sentence


def test_scrape_webpage_meta_with_og_tags():
    html = '''<html><head>
        <meta property="og:title" content="My Great Paper">
        <meta property="og:description" content="This is a great paper about AI.">
        <meta name="author" content="Alice, Bob">
        <title>Fallback Title</title>
    </head><body></body></html>'''
    import requests
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    with patch.object(requests, 'get', return_value=mock_resp):
        meta = _scrape_webpage_meta('https://example.com/paper')
    assert meta['title'] == 'My Great Paper'
    assert meta['description'] == 'This is a great paper about AI.'
    assert meta['authors'] == ['Alice', 'Bob']


def test_scrape_webpage_meta_title_fallback():
    html = '<html><head><title>Only Title Tag</title></head><body></body></html>'
    import requests
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    with patch.object(requests, 'get', return_value=mock_resp):
        meta = _scrape_webpage_meta('https://example.com/paper')
    assert meta['title'] == 'Only Title Tag'
    assert meta['description'] == ''
    assert meta['authors'] == []


def test_openalex_work_to_paper_no_arxiv():
    work = {
        'id': 'https://openalex.org/W12345',
        'display_name': 'Non-arXiv Paper',
        'publication_date': '2026-03-01',
        'locations': [],
        'authorships': [],
        'cited_by_count': 0,
    }
    paper = _openalex_work_to_paper(work, 'world_models', [])
    assert paper['title'] == 'Non-arXiv Paper'
    assert paper['links']['paper'] == 'https://openalex.org/W12345'


# --- delete_papers tests ---

def test_delete_papers(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest.DATA_DIR", tmp_path)
    monkeypatch.setattr("scripts.ingest.VALID_DIRECTIONS", {"test_dir"})

    # Create a data file
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    (dir_path / "_meta.yaml").write_text("name: Test")
    papers = [
        {'id': 'test_dir-2026-001', 'title': 'Paper 1'},
        {'id': 'test_dir-2026-002', 'title': 'Paper 2'},
        {'id': 'test_dir-2026-003', 'title': 'Paper 3'},
    ]
    with open(dir_path / "2026-03.yaml", 'w') as f:
        yaml.dump({'papers': papers}, f)

    deleted = delete_papers(['test_dir-2026-001', 'test_dir-2026-003'])
    assert deleted == 2

    # Verify remaining
    with open(dir_path / "2026-03.yaml") as f:
        data = yaml.safe_load(f)
    assert len(data['papers']) == 1
    assert data['papers'][0]['id'] == 'test_dir-2026-002'


def test_delete_papers_removes_file_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest.DATA_DIR", tmp_path)
    monkeypatch.setattr("scripts.ingest.VALID_DIRECTIONS", {"test_dir"})

    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    papers = [{'id': 'test_dir-2026-001', 'title': 'Only Paper'}]
    with open(dir_path / "2026-03.yaml", 'w') as f:
        yaml.dump({'papers': papers}, f)

    deleted = delete_papers(['test_dir-2026-001'])
    assert deleted == 1
    assert not (dir_path / "2026-03.yaml").exists()


def test_delete_papers_empty_list():
    assert delete_papers([]) == 0


def test_delete_papers_nonexistent_ids(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.ingest.DATA_DIR", tmp_path)
    monkeypatch.setattr("scripts.ingest.VALID_DIRECTIONS", {"test_dir"})

    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    papers = [{'id': 'test_dir-2026-001', 'title': 'Paper 1'}]
    with open(dir_path / "2026-03.yaml", 'w') as f:
        yaml.dump({'papers': papers}, f)

    deleted = delete_papers(['nonexistent-id'])
    assert deleted == 0
