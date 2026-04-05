"""Tests for the YAML loader."""

import sys
from datetime import date
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.loader import load_papers_from_file, filter_papers
from scripts.models import PaperEntry

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_sample_papers():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    assert len(papers) == 4
    assert all(isinstance(p, PaperEntry) for p in papers)


def test_paper_fields():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    p = papers[0]
    assert p.id == "post_training-2026-t01"
    assert p.title == "Test Paper on RLHF Improvements"
    assert p.direction == "post_training"
    assert p.is_open_source is True
    assert p.citations == 150
    assert isinstance(p.date, date)


def test_filter_by_direction():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, direction="post_training")
    assert len(filtered) == 2
    assert all(p.direction == "post_training" for p in filtered)


def test_filter_by_open_source():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, is_open_source=True)
    assert len(filtered) == 2
    assert all(p.is_open_source for p in filtered)


def test_filter_by_tags():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, tags=["rlhf"])
    assert len(filtered) == 1
    assert filtered[0].id == "post_training-2026-t01"


def test_filter_by_date_range():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, since=date(2026, 3, 1))
    assert len(filtered) == 2  # post_training-2026-t01 and llm_search_retrieval-2026-t01


def test_filter_by_citations():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, min_citations=50)
    assert len(filtered) == 2


def test_filter_combined():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    filtered = filter_papers(papers, direction="post_training", is_open_source=True)
    assert len(filtered) == 1
    assert filtered[0].id == "post_training-2026-t01"


def test_load_empty_file(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    papers = load_papers_from_file(empty)
    assert papers == []


def test_load_list_format(tmp_path):
    f = tmp_path / "list.yaml"
    f.write_text("""
- id: test-001
  title: Test
  authors: [A]
  affiliations: [X]
  date: 2026-01-01
  direction: post_training
  tags: []
  category: method
  core_contribution: test
  summary: test summary
""")
    papers = load_papers_from_file(f)
    assert len(papers) == 1
    assert papers[0].id == "test-001"
