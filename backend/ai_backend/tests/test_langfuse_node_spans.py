"""
Integration test: verifies that clarify_with_steps LangGraph nodes appear as
individual spans in local Langfuse.

Architecture notes
-------------------
The ``CallbackHandler`` (langfuse.langchain) creates one observation per
LangGraph node automatically via ``on_chain_start`` / ``on_chain_end`` callbacks.
LLM generation observations are nested under the correct node observation because
``llm_config()`` preserves the child ``AsyncCallbackManagerForChainRun`` (which
carries ``parent_run_id = node_run_id``).

``node_span()`` must NOT be used inside LangGraph node functions: LangGraph's
``set_config_context`` resets OTel ``contextvars`` inside each node task, so any
span created with ``start_as_current_observation`` inside a node would become a
detached root span with a new, unrelated trace id — polluting Langfuse.

Requires local Langfuse at LANGFUSE_HOST with valid credentials in .env.

Run with:
    uv run pytest backend/ai_backend/tests/test_langfuse_node_spans.py -v -s
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from langchain_core.messages import AIMessage

from ai_backend.config import settings as app_settings
from ai_backend.services.clarify_guardrails.models import ClarifyGuardrailsOutput
from ai_backend.services.clarify_with_steps.models import GuidedLearningPrerequisitesOutput
from ai_backend.services.clarify_with_steps.graph import (
    StepByStepLearningState,
    build_step_by_step_learning_graph,
)
from ai_backend.langfuse.context import langfuse_trace_context, node_span

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _query_langfuse_trace(trace_id: str, *, timeout: float = 20.0) -> dict:
    """
    Poll Langfuse API until the trace has at least one observation, or timeout.

    Args:
        trace_id: The 32-char hex trace id.
        timeout:  Maximum seconds to wait.

    Returns:
        The trace dict from the API (may have empty observations on timeout).
    """
    auth = (app_settings.langfuse_public_key, app_settings.langfuse_secret_key)
    host = app_settings.langfuse_host.rstrip("/")
    url = f"{host}/api/public/traces/{trace_id}"

    deadline = time.monotonic() + timeout
    last_data: dict = {}

    async with httpx.AsyncClient(timeout=15) as client:
        while time.monotonic() < deadline:
            r = await client.get(url, auth=auth)
            if r.status_code == 200:
                data = r.json()
                last_data = data
                if data.get("observations"):
                    return data
            await asyncio.sleep(1)

    return last_data


def _make_completion_mock_llm() -> MagicMock:
    """
    Return an LLM mock where:
    - ``with_structured_output(ClarifyGuardrailsOutput)`` → allow pass (first graph node).
    - ``with_structured_output(GuidedLearningPrerequisitesOutput)`` → one prerequisite.
    - ``ainvoke`` → returns AIMessage with "putem trece" (triggers graph completion).
    - ``astream`` → used when stream_queue is set in configurable.
    """
    mock_llm = MagicMock()

    def _with_structured_output(schema: Any, **kwargs: Any) -> MagicMock:
        name = getattr(schema, "__name__", type(schema).__name__)
        chain = MagicMock()
        if name == "ClarifyGuardrailsOutput":
            chain.ainvoke = AsyncMock(
                return_value={
                    "raw": MagicMock(content=""),
                    "parsed": ClarifyGuardrailsOutput(
                        allow=True,
                        reason_code="allowed",
                        student_facing_message_ro="",
                    ),
                    "parsing_error": None,
                }
            )
        else:
            chain.ainvoke = AsyncMock(
                return_value={
                    "raw": MagicMock(content=""),
                    "parsed": GuidedLearningPrerequisitesOutput(prerequisites=["Concept A"]),
                    "parsing_error": None,
                }
            )
        return chain

    mock_llm.with_structured_output = MagicMock(side_effect=_with_structured_output)

    # "putem trece" is in the completion_indicators list → should_advance=True
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="Foarte bine! Putem trece la pasul următor.")
    )

    async def _completion_astream(*args: Any, **kwargs: Any):
        """Yield a chunk that contains a completion indicator (triggers should_advance=True)."""
        chunk = MagicMock()
        chunk.content = "Foarte bine! Putem trece la pasul următor."
        yield chunk

    mock_llm.astream = MagicMock(side_effect=_completion_astream)
    return mock_llm


def _langfuse_singleton_exports_traces(client: Any) -> bool:
    """
    Return True when ``client`` is the process singleton already wired for OTel export.

    Creating a second ``Langfuse()`` instance triggers the SDK guard that skips LangChain
    tracing entirely (\"multiple langfuse clients\"), which breaks these integration tests
    when the FastAPI lifespan has already called ``create_langfuse_client``.
    """
    if client is None:
        return False
    if not getattr(client, "_tracing_enabled", False):
        return False
    resources = getattr(client, "_resources", None)
    if resources is None:
        return False
    pk = getattr(resources, "public_key", None)
    if not pk or pk == "fake":
        return False
    if getattr(resources, "tracer", None) is None:
        return False
    return True


# ---------------------------------------------------------------------------
# Module-scoped fixtures: real Langfuse client + prompt composer
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_langfuse_client():
    """
    Use the existing Langfuse singleton when it already exports traces (e.g. after app
    lifespan); otherwise initialise once. Avoids a second client that disables tracing.
    """
    import ai_backend.langfuse.client as client_mod
    from ai_backend.langfuse.client import create_langfuse_client

    if not app_settings.langfuse_public_key or not app_settings.langfuse_secret_key:
        pytest.skip("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set — skipping integration test")

    previous = client_mod._client

    if _langfuse_singleton_exports_traces(previous):
        yield previous
        return

    lf = create_langfuse_client(app_settings)
    try:
        yield lf
    finally:
        # If nothing was installed before, keep the new client for the rest of the suite.
        if previous is not None:
            client_mod._client = previous


@pytest.fixture(scope="module")
def real_prompt_composer(real_langfuse_client):
    """PromptComposer backed by the real Langfuse client (YAML fallback for missing prompts)."""
    from ai_backend.common.prompts import PROMPTS
    from ai_backend.langfuse.prompts import create_prompt_composer
    import ai_backend.langfuse.prompts as prompts_mod

    previous = prompts_mod._composer
    composer = create_prompt_composer(real_langfuse_client, PROMPTS)
    yield composer
    prompts_mod._composer = previous


# ---------------------------------------------------------------------------
# Test 1 — node_span() actually calls start_as_current_observation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_node_span_calls_start_as_current_observation(real_langfuse_client):
    """
    node_span() must delegate to client.start_as_current_observation and return a
    non-None span object.  If get_langfuse_client() fails, it should return nullcontext
    instead — so this test also confirms the client IS initialized.
    """
    calls: list[str] = []
    original = real_langfuse_client.start_as_current_observation

    def _spy_start(*args: Any, **kwargs: Any):
        calls.append(kwargs.get("name", "?"))
        return original(*args, **kwargs)

    real_langfuse_client.start_as_current_observation = _spy_start  # type: ignore[method-assign]

    try:
        with node_span("smoke_test_node") as span:
            assert span is not None, (
                "node_span() returned None — get_langfuse_client() raised RuntimeError "
                "or start_as_current_observation is broken"
            )
        assert "smoke_test_node" in calls, f"start_as_current_observation not called. calls={calls}"
    finally:
        real_langfuse_client.start_as_current_observation = original


# ---------------------------------------------------------------------------
# Test 2 — llm_config strips LangGraph-specific keys from the node config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_config_strips_langgraph_keys():
    """
    llm_config() must return only 'callbacks' and 'metadata'.

    Keeping 'callbacks' preserves the child AsyncCallbackManagerForChainRun (which
    carries parent_run_id=node_run_id), so on_chat_model_start fires with the right
    parent and LLM generations nest correctly under node observations.

    Stripping 'run_id' is critical: if the node's run_id were forwarded to the LLM,
    on_chat_model_start would register the generation with that same id, overwriting
    the node's entry in CallbackHandler._runs and breaking the observation tree.
    """
    from ai_backend.langfuse.context import llm_config

    node_config = {
        "configurable": {"stream_queue": "queue_object"},
        "callbacks": ["handler_a"],
        "metadata": {"langfuse_user_id": "u1"},
        "run_id": "some-run-id",
        "parent_run_id": "parent-id",
        "recursion_limit": 25,
    }
    result = llm_config(node_config)

    assert list(result.keys()) == ["callbacks", "metadata"], (
        f"llm_config() must return only 'callbacks' and 'metadata', got {list(result.keys())}"
    )
    assert result["callbacks"] == ["handler_a"]
    assert result["metadata"] == {"langfuse_user_id": "u1"}


# ---------------------------------------------------------------------------
# Test 2b — node_span() as child of a manually created parent span
# This verifies that node_span() creates a visible child span when an OTel
# parent span is already active (as it would be inside a LangGraph node callback).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_node_span_as_child_of_parent_span(real_langfuse_client):
    """
    Simulate what happens inside a LangGraph node:
    1. Create a parent span (like the CallbackHandler creates for a node).
    2. Call node_span() inside it.
    3. Check that BOTH spans appear in Langfuse under the same trace_id.
    """
    trace_id = uuid.uuid4().hex

    with real_langfuse_client.start_as_current_observation(
        trace_context={"trace_id": trace_id},
        name="parent_node_sim",
        as_type="span",
    ) as parent_span:
        print(f"\n[DEBUG] parent_span={parent_span}, type={type(parent_span).__name__}")
        print(f"[DEBUG] parent otel span trace_id={hex(parent_span._otel_span.get_span_context().trace_id)}")

        with node_span("child_node_span") as child_span:
            print(f"[DEBUG] child_span={child_span}, type={type(child_span).__name__ if child_span else 'None'}")
            if child_span is not None:
                child_span_ctx = child_span._otel_span.get_span_context()
                print(f"[DEBUG] child otel trace_id={hex(child_span_ctx.trace_id)}")
                child_span.update(output={"status": "ok"})

        parent_span.update(output={"done": True})

    real_langfuse_client.flush()
    await asyncio.sleep(5)

    trace_data = await _query_langfuse_trace(trace_id, timeout=20)
    observations = trace_data.get("observations", [])
    obs_names = [o["name"] for o in observations]

    print(f"\n[DEBUG] trace_id={trace_id}")
    print(f"[DEBUG] observation names={obs_names}")

    assert "parent_node_sim" in obs_names, (
        f"parent_node_sim not found in Langfuse! Got: {obs_names}\n"
        f"(The parent span itself is not appearing — fundamental export issue)"
    )
    assert "child_node_span" in obs_names, (
        f"child_node_span not found as child of parent_node_sim!\n"
        f"  Got observations: {obs_names}\n"
        f"  This means node_span() does NOT create visible child spans inside an active OTel context.\n"
        f"  Likely cause: node_span() creates span with a detached/different trace_id."
    )


# ---------------------------------------------------------------------------
# Test 3 — full graph: graph-level chain span must appear in Langfuse
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_graph_chain_span_visible_in_langfuse(real_langfuse_client, real_prompt_composer):
    """
    When graph.ainvoke() is called inside langfuse_trace_context, at minimum the
    graph-level chain span (CompiledStateGraph / LangGraph) must appear in Langfuse.
    This proves: connectivity, credentials, OTel export pipeline, and trace_id linkage.
    """
    trace_id = uuid.uuid4().hex
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000098")
    mock_llm = _make_completion_mock_llm()
    graph = build_step_by_step_learning_graph(mock_llm, real_prompt_composer)

    initial_state: StepByStepLearningState = {
        "messages": [],
        "original_query": "Ce este integrala?",
        "prerequisites": [],
        "current_prerequisite_index": 0,
        "prerequisites_completed": False,
        "progress_preview_sent": False,
        "guardrails_context": "",
        "guardrails_allowed": False,
        "guardrails_block_message_ro": "",
    }

    async with langfuse_trace_context(
        trace_id=trace_id,
        name="test_graph_chain_span",
        user_id=str(user_id),
        session_id="test-session-graph-chain",
    ) as lf_config:
        # No stream_queue → nodes use ainvoke path, graph terminates deterministically
        config = {"configurable": {}, **lf_config}
        result = await graph.ainvoke(initial_state, config=config)

    print(f"\n[DEBUG] graph result keys: {list(result.keys())}")

    real_langfuse_client.flush()
    await asyncio.sleep(5)

    trace_data = await _query_langfuse_trace(trace_id, timeout=20)
    observations = trace_data.get("observations", [])
    obs_names = [o["name"] for o in observations]

    print(f"\n[DEBUG] trace_id={trace_id}")
    print(f"[DEBUG] observation names={obs_names}")
    print(f"[DEBUG] full observations={observations}")

    assert observations, (
        f"No observations at all in trace {trace_id}.\n"
        f"  - Check Langfuse host is running and accepting spans.\n"
        f"  - Check OTEL exporter logs for errors.\n"
        f"  - trace_data={trace_data}"
    )


# ---------------------------------------------------------------------------
# Test 4 — full graph: NODE-LEVEL spans must appear in Langfuse
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clarify_with_steps_graph_node_spans_in_langfuse(
    real_langfuse_client, real_prompt_composer
):
    """
    End-to-end: run clarify_with_steps graph and confirm that individual node spans
    appear in Langfuse.

    Graph path:
      clarify_guardrails → generate_prerequisites → ask_question  (ainvoke returns "putem trece" → completes)
      → final_explanation → END

    The LangGraph ``CallbackHandler`` automatically creates per-node observations via
    ``on_chain_start`` / ``on_chain_end``.  No explicit ``node_span()`` calls are needed
    inside node functions (and doing so would create detached ghost traces).

    No stream_queue is used so nodes fall back to ainvoke, keeping the flow synchronous
    and deterministic.
    """
    trace_id = uuid.uuid4().hex
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    mock_llm = _make_completion_mock_llm()
    graph = build_step_by_step_learning_graph(mock_llm, real_prompt_composer)

    initial_state: StepByStepLearningState = {
        "messages": [],
        "original_query": "Ce este derivata?",
        "prerequisites": [],
        "current_prerequisite_index": 0,
        "prerequisites_completed": False,
        "progress_preview_sent": False,
        "guardrails_context": "",
        "guardrails_allowed": False,
        "guardrails_block_message_ro": "",
    }

    async with langfuse_trace_context(
        trace_id=trace_id,
        name="test_node_spans",
        user_id=str(user_id),
        session_id="test-session-nodes",
    ) as lf_config:
        config = {"configurable": {}, **lf_config}
        result = await graph.ainvoke(initial_state, config=config)

    print(f"\n[INFO] graph result: prerequisites={result.get('prerequisites')}, "
          f"completed={result.get('prerequisites_completed')}")

    # Flush and wait for the OTel exporter to ship the batch
    real_langfuse_client.flush()
    await asyncio.sleep(5)

    trace_data = await _query_langfuse_trace(trace_id, timeout=25)
    observations = trace_data.get("observations", [])
    obs_names = [o["name"] for o in observations]

    print(f"[INFO] trace_id={trace_id}")
    print(f"[INFO] observation names={obs_names}")

    # LangGraph's CallbackHandler creates observations named after the node names
    # registered via workflow.add_node("name", ...) — not the Python function names.
    expected_nodes = {
        "clarify_guardrails",
        "generate_prerequisites",
        "ask_question",
        "final_explanation",
    }
    missing = expected_nodes - set(obs_names)

    assert not missing, (
        f"Missing LangGraph node-level spans in Langfuse: {missing}\n"
        f"  trace_id={trace_id}\n"
        f"  observations found (names): {obs_names}\n"
        f"  Hints:\n"
        f"  - If only 'LangGraph' appears: config is missing callbacks in graph.ainvoke().\n"
        f"  - If no observations at all: OTel export failed (check MinIO bucket / credentials)."
    )


# ---------------------------------------------------------------------------
# Test 5 — service invocation pattern: asyncio.create_task + stream_queue
# This mirrors how stream_clarify_step_by_step actually calls the graph.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clarify_with_steps_graph_node_spans_via_create_task(
    real_langfuse_client, real_prompt_composer
):
    """
    Reproduce the exact service invocation pattern:
      - asyncio.create_task(graph.ainvoke(...)) — graph runs as a background task
      - stream_queue in configurable — nodes use astream path
      - consume the queue until the first None (like the service does)
      - await the task to completion

    Node-level spans must still appear in Langfuse after flush.
    If this test fails but Test 4 passes, the issue is specific to the
    asyncio.create_task + stream_queue pattern used by the service.
    """
    trace_id = uuid.uuid4().hex
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000097")
    mock_llm = _make_completion_mock_llm()
    graph = build_step_by_step_learning_graph(mock_llm, real_prompt_composer)

    initial_state: StepByStepLearningState = {
        "messages": [],
        "original_query": "Ce este trigonometria?",
        "prerequisites": [],
        "current_prerequisite_index": 0,
        "prerequisites_completed": False,
        "progress_preview_sent": False,
        "guardrails_context": "",
        "guardrails_allowed": False,
        "guardrails_block_message_ro": "",
    }

    async with langfuse_trace_context(
        trace_id=trace_id,
        name="test_node_spans_create_task",
        user_id=str(user_id),
        session_id="test-session-create-task",
    ) as lf_config:
        stream_queue: asyncio.Queue = asyncio.Queue()
        config = {"configurable": {"stream_queue": stream_queue}, **lf_config}

        # Exact pattern from stream_clarify_step_by_step in the service
        invoke_task = asyncio.create_task(graph.ainvoke(initial_state, config=config))

        # Consume from the queue until the first None (generate_prerequisites done)
        stream_timeout = 1.0
        while True:
            try:
                item = await asyncio.wait_for(stream_queue.get(), timeout=stream_timeout)
            except asyncio.TimeoutError:
                if invoke_task.done():
                    break
                continue
            if item is None:
                break

        # Wait for the rest of the graph (ask_question, final_explanation) to complete
        await invoke_task

    print(f"\n[INFO] graph result (via create_task): completed={invoke_task.result().get('prerequisites_completed')}")

    # Flush and wait for the OTel exporter to ship the batch
    real_langfuse_client.flush()
    await asyncio.sleep(5)

    trace_data = await _query_langfuse_trace(trace_id, timeout=25)
    observations = trace_data.get("observations", [])
    obs_names = [o["name"] for o in observations]

    print(f"[INFO] trace_id={trace_id}")
    print(f"[INFO] observation names (create_task pattern)={obs_names}")

    expected_nodes = {
        "clarify_guardrails",
        "generate_prerequisites",
        "ask_question",
        "final_explanation",
    }
    missing = expected_nodes - set(obs_names)

    assert not missing, (
        f"Missing node spans when graph runs via asyncio.create_task: {missing}\n"
        f"  trace_id={trace_id}\n"
        f"  observations found (names): {obs_names}\n"
        f"  This is the exact pattern the service uses! If this fails but Test 4 passes,\n"
        f"  the issue is specific to asyncio.create_task wrapping (context propagation)."
    )
