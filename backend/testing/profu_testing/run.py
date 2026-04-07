"""
CLI: run clarify step-by-step synthetic scenarios against the live API and register Langfuse dataset items.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from typing import Any

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import Langfuse

from profu_testing.config import get_testing_settings, repo_root, testing_env_files
from profu_testing.sse import parse_clarify_sse_to_assistant_text
from profu_testing.synthetic_data import (
    ChecklistItem,
    ClarifyScenario,
    checklist_to_expected_output_json,
    generate_checklist_for_scenario,
    load_clarify_scenarios,
)

LOG = logging.getLogger("profu_testing.run")


def _build_llm() -> ChatGoogleGenerativeAI:
    """
    Build Gemini client for checklist generation.

    Returns:
        Chat model instance.

    Raises:
        ValueError: When ``GOOGLE_API_KEY`` is missing.
    """
    settings = get_testing_settings()
    api_key = settings.google_api_key.strip()
    if not api_key:
        LOG.error("GOOGLE_API_KEY is not set; cannot generate checklists.")
        raise ValueError("GOOGLE_API_KEY is required for checklist generation")
    model = settings.checklist_gemini_model
    LOG.info("Checklist LLM model=%s", model)
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=0.0,
        google_api_key=api_key,
    )


def _langfuse_client() -> Langfuse | None:
    """
    Initialise Langfuse when keys are present.

    Returns:
        Client or ``None`` if keys are missing.
    """
    settings = get_testing_settings()
    public_key = settings.langfuse_public_key.strip()
    secret_key = settings.langfuse_secret_key.strip()
    if not public_key or not secret_key:
        LOG.info("Langfuse keys missing; skipping dataset registration.")
        return None
    host = settings.langfuse_host.rstrip("/")
    LOG.info("Initialising Langfuse client host=%s", host)
    try:
        return Langfuse(public_key=public_key, secret_key=secret_key, host=host, flush_interval=1.0)
    except Exception as exc:
        LOG.error("Langfuse client init failed: %s", exc)
        return None


def _ensure_dataset(client: Langfuse, name: str, description: str) -> None:
    """
    Create dataset if it does not already exist.

    Args:
        client: Langfuse client.
        name: Dataset name.
        description: Human-readable description.
    """
    try:
        client.create_dataset(name=name, description=description)
        LOG.info("Created Langfuse dataset: %s", name)
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" in err or "duplicate" in err or "409" in err:
            LOG.info("Dataset already exists: %s", name)
            return
        LOG.warning("Could not create dataset (continuing): %s", exc)


def _register_dataset_item(
    client: Langfuse,
    *,
    dataset_name: str,
    scenario: ClarifyScenario,
    transcript: str,
    checklist: list[ChecklistItem],
    trace_id: str,
) -> None:
    """
    Add a dataset row linking checklist (expected_output) to the API trace.

    Args:
        client: Langfuse client.
        dataset_name: Target dataset.
        scenario: Scenario metadata.
        transcript: Full user/assistant text log for the judge.
        checklist: Generated checklist items.
        trace_id: 32-char hex trace id sent to the API (must match exported trace).
    """
    expected = checklist_to_expected_output_json(checklist)
    item_input: dict[str, Any] = {
        "scenario_id": scenario.id,
        "opening_user_message": scenario.opening_user_message,
        "scenario_goal": scenario.scenario_goal,
    }
    metadata = {
        "transcript": transcript,
        "feature": "clarify_step_by_step",
    }
    try:
        client.create_dataset_item(
            dataset_name=dataset_name,
            input=item_input,
            expected_output=expected,
            metadata=metadata,
            source_trace_id=trace_id,
        )
        client.flush()
        LOG.info(
            "Registered dataset item for scenario_id=%s trace_id=%s dataset=%s",
            scenario.id,
            trace_id,
            dataset_name,
        )
    except Exception as exc:
        LOG.error(
            "Failed to create dataset item for scenario_id=%s: %s",
            scenario.id,
            exc,
        )


async def _post_clarify_stream(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    token: str,
    query: str,
    history: list[dict[str, str]],
    trace_id: str,
    session_id: str,
) -> str:
    """
    Call ``/clarify/step-by-step-stream`` and return assistant text for one turn.

    Args:
        client: HTTP client.
        base_url: API root without trailing slash.
        token: Bearer JWT.
        query: Current user message.
        history: Prior turns as ``{"role","content"}`` dicts.
        trace_id: Langfuse trace id (hex).
        session_id: Langfuse session id.

    Returns:
        Parsed assistant-visible text.

    Raises:
        httpx.HTTPError: On transport or HTTP errors.
    """
    url = f"{base_url.rstrip('/')}/clarify/step-by-step-stream"
    payload = {
        "query": query,
        "history": history,
        "conversation_id": None,
        "trace_id": trace_id,
        "session_id": session_id,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    LOG.info("POST clarify stream trace_id=%s history_len=%d", trace_id, len(history))
    try:
        response = await client.post(url, json=payload, headers=headers, timeout=600.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        LOG.error("Clarify HTTP error: %s", exc)
        raise
    body = response.text
    text = parse_clarify_sse_to_assistant_text(body)
    LOG.info("Assistant reply length=%d chars", len(text))
    return text


def _format_transcript(turns: list[tuple[str, str]]) -> str:
    """
    Build a readable transcript for Langfuse metadata and logs.

    Args:
        turns: Ordered (role, content) pairs, role in ``user``/``assistant``.

    Returns:
        Plain-text transcript.
    """
    lines: list[str] = []
    for role, content in turns:
        lines.append(f"{role.upper()}:\n{content}\n")
    return "\n".join(lines)


async def run_single_scenario(
    scenario: ClarifyScenario,
    *,
    base_url: str,
    token: str,
    llm: ChatGoogleGenerativeAI | None,
    skip_checklist: bool,
    langfuse_client: Langfuse | None,
    dataset_name: str,
) -> None:
    """
    Generate checklist, run all scripted user turns, optionally register Langfuse dataset item.

    Args:
        scenario: Scenario definition.
        base_url: API base URL.
        token: JWT.
        llm: Model for checklist (unused if ``skip_checklist``).
        skip_checklist: If True, use a single placeholder checklist item.
        langfuse_client: Optional Langfuse client.
        dataset_name: Dataset for ``create_dataset_item``.
    """
    trace_id = uuid.uuid4().hex
    session_id = f"eval-{scenario.id}-{trace_id[:8]}"
    LOG.info("Starting scenario_id=%s trace_id=%s", scenario.id, trace_id)

    if skip_checklist or llm is None:
        checklist = [
            ChecklistItem(
                id="placeholder",
                text="Session completed without automated checklist (skip mode).",
                priority="nice",
            )
        ]
        LOG.info("Using placeholder checklist for scenario_id=%s", scenario.id)
    else:
        checklist = await generate_checklist_for_scenario(scenario, llm=llm)

    user_sequence = [scenario.opening_user_message] + list(scenario.user_followups)
    user_sequence = user_sequence[: scenario.max_turns]
    if not user_sequence:
        LOG.error("scenario_id=%s has no user messages.", scenario.id)
        return

    history: list[dict[str, str]] = []
    transcript_turns: list[tuple[str, str]] = []

    async with httpx.AsyncClient() as http_client:
        for user_text in user_sequence:
            transcript_turns.append(("user", user_text))
            try:
                assistant_text = await _post_clarify_stream(
                    http_client,
                    base_url=base_url,
                    token=token,
                    query=user_text,
                    history=history,
                    trace_id=trace_id,
                    session_id=session_id,
                )
            except httpx.HTTPError:
                LOG.error("Aborting scenario_id=%s after HTTP failure.", scenario.id)
                raise
            transcript_turns.append(("assistant", assistant_text))
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})

    transcript = _format_transcript(transcript_turns)
    LOG.info("Scenario_id=%s finished; transcript length=%d", scenario.id, len(transcript))
    out_dir = repo_root() / "backend" / "testing" / "runs"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{scenario.id}_{trace_id[:8]}.txt"
        out_path.write_text(transcript, encoding="utf-8")
        LOG.info("Wrote transcript to %s", out_path)
    except OSError as exc:
        LOG.error("Could not write transcript file: %s", exc)

    if langfuse_client is not None:
        _ensure_dataset(
            langfuse_client,
            name=dataset_name,
            description="Profu clarify step-by-step harness: items link traces to checklist JSON.",
        )
        _register_dataset_item(
            langfuse_client,
            dataset_name=dataset_name,
            scenario=scenario,
            transcript=transcript,
            checklist=checklist,
            trace_id=trace_id,
        )


async def _async_main(args: argparse.Namespace) -> int:
    """
    Async entry: load scenarios and run selection.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Process exit code (0 success).
    """
    settings = get_testing_settings()
    env_paths = testing_env_files()
    if env_paths:
        LOG.info("Loaded settings from env file(s): %s", env_paths)
    else:
        LOG.info("Loaded settings from process environment only (no .env file found).")

    scenarios = load_clarify_scenarios()
    if args.list:
        for s in scenarios:
            print(s.id)
        return 0

    selected: list[ClarifyScenario] = []
    if args.all:
        selected = list(scenarios)
    elif args.scenario:
        found = {s.id: s for s in scenarios}
        if args.scenario not in found:
            LOG.error("Unknown scenario id: %s", args.scenario)
            return 2
        selected = [found[args.scenario]]
    else:
        LOG.error("Specify --scenario <id> or --all or --list")
        return 2

    token = settings.eval_jwt
    if not token:
        LOG.error("Set EVAL_JWT (or PROFU_EVAL_BEARER) to a valid Supabase JWT.")
        return 2
    base_url = settings.resolved_api_base_url

    llm: ChatGoogleGenerativeAI | None = None
    if not args.skip_checklist:
        try:
            llm = _build_llm()
        except ValueError:
            return 2

    lf: Langfuse | None = None
    if not args.skip_langfuse:
        lf = _langfuse_client()
    dataset_name = settings.profu_langfuse_eval_dataset.strip() or "profu_clarify_step_by_step_eval"

    for sc in selected:
        try:
            await run_single_scenario(
                sc,
                base_url=base_url,
                token=token,
                llm=llm,
                skip_checklist=args.skip_checklist,
                langfuse_client=lf,
                dataset_name=dataset_name,
            )
        except Exception as exc:
            LOG.error("Scenario_id=%s failed: %s", sc.id, exc)
            return 1
    return 0


def main() -> None:
    """CLI entrypoint for ``profu-test-clarify``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run Profu clarify step-by-step synthetic scenarios.")
    parser.add_argument("--scenario", type=str, default=None, help="Single scenario id to run.")
    parser.add_argument("--all", action="store_true", help="Run every loaded scenario.")
    parser.add_argument("--list", action="store_true", help="List scenario ids and exit.")
    parser.add_argument("--skip-checklist", action="store_true", help="Skip LLM checklist generation.")
    parser.add_argument("--skip-langfuse", action="store_true", help="Skip Langfuse dataset registration.")
    args = parser.parse_args()
    code = asyncio.run(_async_main(args))
    sys.exit(code)


if __name__ == "__main__":
    main()
