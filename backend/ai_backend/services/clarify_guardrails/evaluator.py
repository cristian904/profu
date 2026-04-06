"""
Async guardrails evaluation: single LLM structured call shared by graphs and follow-up paths.
"""

from typing import Any, Optional
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.common.structured_output import coerce_structured_output
from ai_backend.langfuse.context import llm_config
from ai_backend.langfuse.prompts import PromptComposer
from ai_backend.services.clarify_guardrails.constants import CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
from ai_backend.services.clarify_guardrails.models import ClarifyGuardrailsOutput
from ai_backend.services.clarify_guardrails.structured_llm import get_guardrails_structured_llm
from profu_logging.feature_logger import get_feature_logger

LOG = get_feature_logger(source="clarify_guardrails")


async def evaluate_clarify_guardrails(
    *,
    llm: LangGraphChatModel,
    composer: PromptComposer,
    user_query: str,
    conversation_context: str,
    config: Optional[RunnableConfig] = None,
    user_id: str | UUID | None = None,
) -> ClarifyGuardrailsOutput:
    """
    Run the guardrails structured LLM check for one user turn.

    Args:
        llm: Chat model supporting ``with_structured_output``.
        composer: Prompt composer for ``clarify_guardrails`` system prompt.
        user_query: Latest student message to evaluate.
        conversation_context: Optional short transcript from ``format_messages_for_guardrails_context``.
        config: LangGraph/Langfuse merged config; passed through to the LLM.
        user_id: Optional user id for structured logs (string or UUID).

    Returns:
        Parsed guardrails output; on parse failure returns a blocked decision with reason_code
        ``parse_error`` and a safe default Romanian message (fail-closed).
    """
    config = config or {}
    _uid: Any = str(user_id) if user_id is not None else None
    trimmed_query = (user_query or "").strip()
    if not trimmed_query:
        LOG.warning("Guardrails received empty user_query; blocking", user_id=_uid)
        return ClarifyGuardrailsOutput(
            allow=False,
            reason_code="off_topic",
            student_facing_message_ro=CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO,
        )

    guard_llm = get_guardrails_structured_llm(llm)
    try:
        system_prompt = composer.get("clarify_guardrails")
    except KeyError as e:
        LOG.error(
            f"clarify_guardrails prompt missing from YAML/Langfuse: {e!s}",
            user_id=_uid,
            traceback=None,
        )
        return ClarifyGuardrailsOutput(
            allow=False,
            reason_code="parse_error",
            student_facing_message_ro=CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO,
        )

    context_block = (conversation_context or "").strip()
    human_body = (
        f"Mesajul curent al elevului:\n{trimmed_query}\n\n"
        f"Rezumat conversație recentă (poate fi gol):\n{context_block if context_block else '(gol)'}"
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_body)]

    try:
        LOG.info("Guardrails LLM invoke starting", user_id=_uid)
        raw_result = await guard_llm.ainvoke(messages, config=llm_config(config))
        parsed, _raw_text = coerce_structured_output(raw_result, ClarifyGuardrailsOutput)
    except Exception as e:
        import traceback as tb

        LOG.error(
            f"Guardrails LLM call failed: {e!s}",
            user_id=_uid,
            traceback=tb.format_exc(),
        )
        return ClarifyGuardrailsOutput(
            allow=False,
            reason_code="parse_error",
            student_facing_message_ro=CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO,
        )

    if parsed is None:
        LOG.warning("Guardrails structured parse failed; fail-closed", user_id=_uid)
        return ClarifyGuardrailsOutput(
            allow=False,
            reason_code="parse_error",
            student_facing_message_ro=CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO,
        )

    if parsed.allow:
        if (parsed.reason_code or "").strip() != "allowed":
            LOG.info(
                f"Guardrails normalizing reason_code to allowed (allow=true, was {parsed.reason_code})",
                user_id=_uid,
            )
        parsed = parsed.model_copy(update={"reason_code": "allowed", "student_facing_message_ro": ""})
    elif not parsed.allow:
        message_ro = (parsed.student_facing_message_ro or "").strip() or CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
        parsed = parsed.model_copy(update={"student_facing_message_ro": message_ro})

    LOG.info(
        f"Guardrails result allow={parsed.allow} reason_code={parsed.reason_code}",
        user_id=_uid,
    )
    return parsed
