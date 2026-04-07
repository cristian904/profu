"""
Handcrafted synthetic scenarios and LLM-generated evaluation checklists for clarify step-by-step.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, ValidationError

LOG = logging.getLogger("profu_testing.synthetic_data")


class ClarifyScenario(BaseModel):
    """One scripted multi-turn scenario for `/clarify/step-by-step-stream`."""

    id: str = Field(..., description="Stable scenario identifier (slug).")
    opening_user_message: str = Field(..., description="First user message (Romanian, student voice).")
    scenario_goal: str = Field(
        ...,
        description="Operator-facing success intent in English for checklist generation.",
    )
    user_followups: list[str] = Field(
        default_factory=list,
        description="Subsequent user messages after each assistant turn, in order.",
    )
    max_turns: int = Field(default=12, ge=1, le=50, description="Safety cap on HTTP round-trips.")


class ChecklistItem(BaseModel):
    """Single observable criterion for Langfuse LLM-as-judge."""

    id: str = Field(..., description="Stable snake_case id.")
    text: str = Field(..., description="What must be verifiable from the transcript.")
    priority: Literal["must", "nice"] = Field(
        default="must",
        description="must = required for pass; nice = optional stretch goals.",
    )


class _ChecklistEnvelope(BaseModel):
    """Structured output wrapper for Gemini."""

    items: list[ChecklistItem] = Field(default_factory=list)


def scenarios_dir() -> Path:
    """
    Directory containing `clarify_step_by_step` YAML files (shipped inside the package).

    Returns:
        Absolute path to packaged scenarios root.
    """
    return Path(__file__).resolve().parent / "scenarios" / "clarify_step_by_step"


def load_clarify_scenarios(*, directory: Path | None = None) -> list[ClarifyScenario]:
    """
    Load all ``*.yaml`` scenarios from the clarify step-by-step folder.

    Args:
        directory: Override scenarios directory (for tests).

    Returns:
        Parsed scenarios sorted by ``id``.

    Raises:
        FileNotFoundError: If directory does not exist.
        ValidationError: If any YAML fails schema validation.
    """
    root = directory or scenarios_dir()
    if not root.is_dir():
        LOG.error("Scenarios directory missing: %s", root)
        raise FileNotFoundError(f"Scenarios directory not found: {root}")
    scenarios: list[ClarifyScenario] = []
    yaml_files = sorted(root.glob("*.yaml"))
    if not yaml_files:
        LOG.error("No *.yaml scenarios found in %s", root)
        raise FileNotFoundError(f"No scenario YAML files in {root}")
    for path in yaml_files:
        LOG.info("Loading scenario file: %s", path.name)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            LOG.error("YAML parse failed for %s: %s", path, exc)
            raise
        if not isinstance(raw, dict):
            LOG.error("Scenario file must be a mapping: %s", path)
            raise ValueError(f"Scenario file must be a YAML mapping: {path}")
        try:
            scenarios.append(ClarifyScenario.model_validate(raw))
        except ValidationError as exc:
            LOG.error("Scenario validation failed for %s: %s", path, exc)
            raise
    LOG.info("Loaded %d clarify step-by-step scenario(s).", len(scenarios))
    return sorted(scenarios, key=lambda s: s.id)


async def generate_checklist_for_scenario(
    scenario: ClarifyScenario,
    *,
    llm: ChatGoogleGenerativeAI,
    max_items: int = 10,
) -> list[ChecklistItem]:
    """
    Use an LLM to derive an observable checklist from the opening message and goal.

    Args:
        scenario: Scripted scenario (opening + goal).
        llm: Configured chat model (temperature 0 recommended).
        max_items: Upper bound on checklist size.

    Returns:
        Validated checklist items.

    Raises:
        ValidationError: If the model output does not match the schema.
        RuntimeError: If the model returns no items after retries are exhausted.
    """
    system = SystemMessage(
        content=(
            "You are an evaluation designer for Romanian Bac-level mathematics tutoring. "
            "Given the student's opening question and the scenario goal, produce a checklist "
            "of observable criteria that a perfect clarify-step-by-step session would satisfy "
            "by the end of the conversation. "
            "Each item must be checkable from the chat transcript only (no hidden state). "
            f"Return at most {max_items} items. "
            "At least half must be priority \"must\". "
            "Use English for item text. "
            "Ids must be snake_case and unique. "
            "Avoid vague items like \"is encouraging\"; prefer concrete concepts, definitions, "
            "examples, or prerequisite coverage."
        )
    )
    human = HumanMessage(
        content=(
            f"scenario_id: {scenario.id}\n"
            f"opening_user_message (Romanian):\n{scenario.opening_user_message}\n\n"
            f"scenario_goal (English):\n{scenario.scenario_goal}\n\n"
            "Respond with JSON only matching schema: "
            '{"items": [{"id": "...", "text": "...", "priority": "must"|"nice"}]}'
        )
    )
    structured = llm.with_structured_output(_ChecklistEnvelope)
    LOG.info(
        "Generating checklist for scenario_id=%s via structured output.",
        scenario.id,
    )
    try:
        result = await structured.ainvoke([system, human])
    except Exception as exc:
        LOG.error("Checklist LLM call failed for scenario_id=%s: %s", scenario.id, exc)
        raise
    if not result.items:
        LOG.error("Checklist model returned zero items for scenario_id=%s", scenario.id)
        raise RuntimeError(f"Empty checklist for scenario {scenario.id}")
    LOG.info(
        "Checklist ready for scenario_id=%s: %d item(s).",
        scenario.id,
        len(result.items),
    )
    return list(result.items)


def checklist_to_expected_output_json(items: list[ChecklistItem]) -> str:
    """
    Serialize checklist for Langfuse dataset ``expected_output`` field.

    Args:
        items: Checklist rows.

    Returns:
        JSON string (stable key order via model_dump).
    """
    payload = [i.model_dump() for i in items]
    return json.dumps(payload, ensure_ascii=False, indent=2)
