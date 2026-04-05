"""Tests for batch metadata store."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.batch_store import load_batch_meta, save_batch_meta


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.batch_store.BATCHES_PATH", tmp_path / "batches.yaml")


def test_load_empty():
    assert load_batch_meta() == {}


def test_save_and_load():
    save_batch_meta("2026-03-26", "post_training", query="reward hacking")
    meta = load_batch_meta()
    assert "2026-03-26" in meta
    assert meta["2026-03-26"]["directions"] == ["post_training"]
    assert meta["2026-03-26"]["query"] == "reward hacking"


def test_append_direction():
    save_batch_meta("2026-03-26", "post_training")
    save_batch_meta("2026-03-26", "world_models")
    meta = load_batch_meta()
    assert set(meta["2026-03-26"]["directions"]) == {"post_training", "world_models"}


def test_no_duplicate_direction():
    save_batch_meta("2026-03-26", "post_training")
    save_batch_meta("2026-03-26", "post_training")
    meta = load_batch_meta()
    assert meta["2026-03-26"]["directions"] == ["post_training"]


def test_no_query():
    save_batch_meta("2026-03-26", "post_training")
    meta = load_batch_meta()
    assert meta["2026-03-26"]["query"] == ""
