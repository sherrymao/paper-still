"""Utility functions."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


def ensure_output_dirs():
    for subdir in ["html"]:
        (OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)
