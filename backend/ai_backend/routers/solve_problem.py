"""
Solve Problem Router - Guided problem solving with image upload and OCR.
Uses LangGraph to manage the conversation flow with intent detection and hint generation.
"""
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
import time

from ai_backend.config import settings
from ai_backend.common.conversation_history import resolve_effective_history
from ai_backend.langfuse.context import langfuse_trace_context, resolve_session_id
from ai_backend.langfuse.prompts import PromptComposer, get_prompt_composer
from profu_logging.feature_logger import get_feature_logger
from profu_logging.log_utils import log_json
from ai_backend.common.streaming.sse import (
    SSE_GENERIC_USER_ERROR,
    emit_done,
    emit_meta_ttft,
    escape_sse_data,
    sse_data_line,
)
from ai_backend.services.solve_problem.ocr import perform_ocr
from ai_backend.services.solve_problem.embeddings import embed_query, normalize_embedding
from ai_backend.services.solve_problem.graph import ProblemSolvingState, build_problem_solving_graph
from ai_backend.services.solve_problem.models import (
    ProblemSolveRequest,
    SuggestProblemRequest,
    SuggestedProblemItem,
    SuggestProblemResponse,
)
from .common import (
    LangGraphChatModel,
    get_current_user_id,
    get_llm,
    get_supabase_client,
    is_solve_quota_exceeded,
)

# Message shown when user exceeds monthly solve-problem quota
QUOTA_LIMIT_MESSAGE = (
    "Ai atins limita lunară de probleme pe care le poți rezolva cu Profu. "
    "Revino luna viitoare pentru mai multe."
)

router = APIRouter(prefix="/solve-problem", tags=["solve_problem"])

LOG_SOLVE_UPLOAD = get_feature_logger(source="solve_problem_upload")
LOG_SOLVE_STREAM = get_feature_logger(source="solve_problem_stream")
LOG_SOLVE_SUGGEST = get_feature_logger(source="solve_problem_suggest")


@router.post("/upload")
async def upload_problem_image(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    supabase=Depends(get_supabase_client),
):
    """
    Upload an image of a problem and perform OCR.
    Returns the extracted problem text.
    Requires Authorization: Bearer <Supabase JWT>. Enforces monthly solve quota before OCR.
    """
    LOG_SOLVE_UPLOAD.info(
        f"Upload request received. Filename: {file.filename}, Content-Type: {file.content_type}",
        user_id=user_id,
    )
    
    # Auth and quota check before any file read or OCR
    threshold = getattr(settings, "solve_monthly_quota_threshold", 0) or 0
    if is_solve_quota_exceeded(user_id, supabase, threshold):
        LOG_SOLVE_UPLOAD.info(
            f"Quota exceeded: user={user_id} threshold={threshold}",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=403,
            detail=QUOTA_LIMIT_MESSAGE,
        )
    
    try:
        # Read image bytes first (before validation, to ensure we can read it)
        LOG_SOLVE_UPLOAD.info("Reading file bytes...", user_id=user_id)
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            LOG_SOLVE_UPLOAD.error("File is empty", user_id=user_id, traceback=None)
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        LOG_SOLVE_UPLOAD.info(f"Read {len(image_bytes)} bytes from file", user_id=user_id)
        
        # Validate file is an image - check content_type first, but fall back to file extension
        # Be lenient - accept if either content_type OR file extension indicates it's an image
        is_valid_image = False
        validation_method = ""
        
        # First check content_type
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
            validation_method = f"content_type: {file.content_type}"
            LOG_SOLVE_UPLOAD.info(f"Validated by {validation_method}", user_id=user_id)
        elif file.filename:
            # If content_type doesn't indicate image, check file extension
            valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            file_ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
            if f".{file_ext}" in valid_extensions:
                is_valid_image = True
                validation_method = f"file extension: .{file_ext}"
                LOG_SOLVE_UPLOAD.info(f"Validated by {validation_method}", user_id=user_id)
                if file.content_type:
                    LOG_SOLVE_UPLOAD.info(
                        f"Note: content_type was {file.content_type}, but file extension is valid",
                        user_id=user_id,
                    )
            else:
                LOG_SOLVE_UPLOAD.warning(f"File extension not recognized: .{file_ext}", user_id=user_id)
        
        if not is_valid_image:
            # Only reject if we can't validate it as an image by either method
            raise HTTPException(
                status_code=400, 
                detail=f"File must be an image. content_type={file.content_type}, filename={file.filename}. "
                       f"Valid extensions: .jpg, .jpeg, .png, .gif, .bmp, .webp"
            )
        
        # Perform OCR
        log_json(
            source="solve_problem_upload",
            level="info",
            message="Starting OCR process...",
            user_id=user_id,
            traceback=None,
        )
        problem_text = await perform_ocr(image_bytes, user_id=user_id)
        log_json(
            source="solve_problem_upload",
            level="info",
            message=f"OCR completed successfully, extracted {len(problem_text)} characters. Preview: {problem_text[:100]}...",
            user_id=user_id,
            traceback=None,
        )
        
        log_json(
            source="solve_problem_upload",
            level="info",
            message="Upload completed successfully",
            user_id=user_id,
            traceback=None,
        )
        return {
            "problem_text": problem_text,
            "filename": file.filename,
            "content_type": file.content_type
        }
    except HTTPException:
        log_json(
            source="solve_problem_upload",
            level="error",
            message="HTTPException raised, re-raising",
            user_id=user_id,
            traceback=None,
        )
        raise
    except Exception as e:
        import traceback as tb
        error_trace = tb.format_exc()
        log_json(
            source="solve_problem_upload",
            level="error",
            message=f"Error processing image: {e!s}",
            user_id=user_id,
            traceback=error_trace,
        )
        raise HTTPException(
            status_code=500,
            detail="Error processing image. Check server logs for details.",
        ) from e


def _normalize_embedding(values: list[float]) -> list[float]:
    """
    Backwards-compatible wrapper for embedding normalization.

    Kept to avoid changing internal call sites; implementation lives in services.solve_problem.
    """
    return normalize_embedding(values)


def _embed_query(text: str) -> list[float]:
    """
    Backwards-compatible wrapper for query embeddings.

    Kept to avoid changing internal call sites; implementation lives in services.solve_problem.
    """
    return embed_query(text)


@router.post("/suggest-problem", response_model=SuggestProblemResponse)
async def suggest_problem(
    body: SuggestProblemRequest,
    user_id: UUID = Depends(get_current_user_id),
    supabase=Depends(get_supabase_client),
):
    """
    Vector search in documents table; return top 5 similar problem statements.
    Used when the user taps "vreau probleme similare" after the first AI response.
    Requires Authorization: Bearer <Supabase JWT>. Enforces monthly solve quota when enabled.
    """
    problem_text = (body.problem_text or "").strip()
    if not problem_text:
        raise HTTPException(status_code=400, detail="problem_text is required and cannot be empty")

    threshold = getattr(settings, "solve_monthly_quota_threshold", 0) or 0
    if is_solve_quota_exceeded(user_id, supabase, threshold):
        LOG_SOLVE_SUGGEST.info(
            f"Quota exceeded for suggest-problem: user={user_id} threshold={threshold}",
            user_id=user_id,
        )
        raise HTTPException(status_code=403, detail=QUOTA_LIMIT_MESSAGE)

    if supabase is None:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set",
        )

    try:
        query_embedding = _embed_query(problem_text)
    except HTTPException:
        raise
    except Exception as e:
        import traceback as tb
        log_json(
            source="solve_problem_suggest",
            level="error",
            message=f"Embedding failed: {e!s}",
            user_id=user_id,
            traceback=tb.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail="Embedding failed. Check server logs for details.",
        ) from e

    try:
        r = supabase.rpc("match_documents", {"query_embedding": query_embedding, "match_count": 5}).execute()
        rows = (r.data or []) if hasattr(r, "data") else []
    except Exception as e:
        import traceback as tb
        log_json(
            source="solve_problem_suggest",
            level="error",
            message=f"match_documents RPC failed: {e!s}",
            user_id=user_id,
            traceback=tb.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail="Vector search failed. Check server logs for details.",
        ) from e

    doc_ids = [row.get("id") for row in rows]
    log_json(
        source="solve_problem_suggest",
        level="info",
        message=f"Document ids shown to user (check in DB): {doc_ids}",
        user_id=user_id,
        traceback=None,
    )

    problems = [SuggestedProblemItem(statement=(row.get("content") or "")) for row in rows]
    # Build message with full problem text for each
    if not problems:
        message = "Nu am găsit probleme similare în baza de date."
    else:
        parts = [f"{i + 1}. {p.statement}" for i, p in enumerate(problems)]
        message = "Uite " + str(len(problems)) + " probleme asemanatoare cu acesta:\n\n" + "\n\n".join(parts)

    return SuggestProblemResponse(message=message, problems=problems)


@router.post("/stream")
async def solve_problem_stream(
    request: ProblemSolveRequest,
    user_id: UUID = Depends(get_current_user_id),
    llm: LangGraphChatModel = Depends(get_llm),
    composer: PromptComposer = Depends(get_prompt_composer),
    supabase=Depends(get_supabase_client),
):
    """
    Streaming endpoint for guided problem solving.
    Uses LangGraph to manage conversation flow with intent detection and hint generation.
    Requires Authorization: Bearer <Supabase JWT>. Enforces monthly solve quota before running the graph.
    """
    log_json(
        source="solve_problem_stream",
        level="info",
        message=f"Stream request received. Query: {request.query[:50]}..., problem_text length: {len(request.problem_text)}, history length: {len(request.history)}",
        user_id=user_id,
        traceback=None,
    )
    
    # Auth and quota check before building state or running the graph
    threshold = getattr(settings, "solve_monthly_quota_threshold", 0) or 0
    if is_solve_quota_exceeded(user_id, supabase, threshold):
        log_json(
            source="solve_problem_stream",
            level="info",
            message=f"Quota exceeded: user={user_id} threshold={threshold}",
            user_id=user_id,
            traceback=None,
        )

        async def quota_limit_stream():
            for char in QUOTA_LIMIT_MESSAGE:
                yield sse_data_line(escape_sse_data(char))
                await asyncio.sleep(0.01)
            yield emit_done()

        return StreamingResponse(
            quota_limit_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def generate():
        try:
            start_time = time.time()

            # Prefer loading history from Supabase by conversation_id when provided,
            # fall back to the history array from the client for backwards compatibility.
            history = resolve_effective_history(
                user_id=user_id,
                request_history=request.history,
                conversation_id=request.conversation_id,
                supabase_client=supabase,
            )
            log_json(
                source="solve_problem_stream",
                level="info",
                message=f"Effective history length: {len(history)}",
                user_id=user_id,
                traceback=None,
            )

            log_json(
                source="solve_problem_stream",
                level="info",
                message="Building initial state...",
                user_id=user_id,
                traceback=None,
            )
            # Build initial state (user_id for logging in graph nodes)
            initial_state: ProblemSolvingState = {
                "messages": [],
                "problem_text": request.problem_text,
                "intent": "",
                "student_work": "",
                "hint_level": 0,
                "full_solution_requested": False,
                "user_id": str(user_id),
            }
            
            # Build conversation history
            if history:
                log_json(
                    source="solve_problem_stream",
                    level="info",
                    message=f"Adding {len(history)} messages from history",
                    user_id=user_id,
                    traceback=None,
                )
                for msg in history:
                    if msg.role == "user":
                        initial_state["messages"].append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        initial_state["messages"].append(AIMessage(content=msg.content))
            
            # Add current query
            log_json(
                source="solve_problem_stream",
                level="info",
                message="Adding current query to state",
                user_id=user_id,
                traceback=None,
            )
            initial_state["messages"].append(HumanMessage(content=request.query))
            log_json(
                source="solve_problem_stream",
                level="info",
                message=f"Total messages in state: {len(initial_state['messages'])}",
                user_id=user_id,
                traceback=None,
            )
            
            # Run the graph with a stream queue so content nodes can push chunks in real time
            stream_queue: asyncio.Queue = asyncio.Queue()
            log_json(
                source="solve_problem_stream",
                level="info",
                message="Building and invoking LangGraph (streaming)...",
                user_id=user_id,
                traceback=None,
            )
            graph = build_problem_solving_graph(llm, composer)

            async with langfuse_trace_context(
                trace_id=request.trace_id,
                session_id=resolve_session_id(request.session_id, request.conversation_id),
                user_id=str(user_id),
                name="solve_problem",
                tags=["solve_problem"],
            ) as langfuse_config:
                # Merge langfuse callbacks into the LangGraph config
                config = {
                    "configurable": {"stream_queue": stream_queue},
                    **langfuse_config,
                }
                invoke_task = asyncio.create_task(graph.ainvoke(initial_state, config=config))

                # Consume queue: [THINKING], then content chunks, then None sentinel
                first_content_chunk = True
                stream_timeout = 1.0
                while True:
                    try:
                        item = await asyncio.wait_for(stream_queue.get(), timeout=stream_timeout)
                    except asyncio.TimeoutError:
                        if invoke_task.done():
                            if invoke_task.exception() is not None:
                                raise invoke_task.exception()
                            # Task succeeded but no content node ran or no sentinel was put
                            break
                        continue
                    if item is None:
                        break
                    if item == "[THINKING]":
                        yield "data: [THINKING]\n\n"
                        continue
                    # Content chunk
                    if first_content_chunk:
                        log_json(
                            source="solve_problem_stream",
                            level="info",
                            message="Time to first token (meta emitted)",
                            user_id=user_id,
                            traceback=None,
                        )
                        yield emit_meta_ttft(start_time)
                        first_content_chunk = False
                    yield sse_data_line(escape_sse_data(item))

                await invoke_task

            log_json(
                source="solve_problem_stream",
                level="info",
                message=f"Graph execution complete. Final intent: {invoke_task.result().get('intent')}",
                user_id=user_id,
                traceback=None,
            )

            await asyncio.sleep(0.05)
            log_json(
                source="solve_problem_stream",
                level="info",
                message="Sending [DONE] signal. Stream completed successfully",
                user_id=user_id,
                traceback=None,
            )
            yield emit_done()
            
        except Exception as e:
            import traceback as tb
            error_trace = tb.format_exc()
            log_json(
                source="solve_problem_stream",
                level="error",
                message=f"Error in stream: {e!s}",
                user_id=user_id,
                traceback=error_trace,
            )
            yield sse_data_line(escape_sse_data(SSE_GENERIC_USER_ERROR))
            yield emit_done()
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )