"""
Load prompt templates from the repository ``prompts.yaml`` (next to the ``ai_backend`` package root).
"""

from pathlib import Path

import yaml

# prompts.yaml lives at ai_backend/prompts.yaml (one level above this package subfolder)
_prompts_path = Path(__file__).resolve().parent.parent / "prompts.yaml"
with open(_prompts_path, "r", encoding="utf-8") as f:
    PROMPTS: dict = yaml.safe_load(f)
