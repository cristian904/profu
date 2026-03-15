"""
Solve Problem Router - Guided problem solving with image upload and OCR.
Uses LangGraph to manage the conversation flow with intent detection and hint generation.
"""
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from typing import TypedDict, Annotated, Sequence, Optional, NotRequired
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
import asyncio
import time
import json
import re
import base64
from io import BytesIO

from ai_backend.config import settings
from ai_backend.log_utils import log_json
from .common import (
    get_llm,
    get_supabase_client,
    Message,
    PROMPTS,
    get_current_user_id,
    get_solve_quota_count,
    load_conversation_history_for_user,
)

# Message shown when user exceeds monthly solve-problem quota
QUOTA_LIMIT_MESSAGE = (
    "Ai atins limita lunară de probleme pe care le poți rezolva cu Profu. "
    "Revino luna viitoare pentru mai multe."
)

router = APIRouter(prefix="/solve-problem", tags=["solve_problem"])


class ProblemSolvingState(TypedDict):
    """State for the problem solving graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    problem_text: str
    intent: str
    student_work: str
    hint_level: int
    full_solution_requested: bool
    user_id: NotRequired[Optional[str]]  # Set by stream endpoint for logging


def _user_id_from_state(state: ProblemSolvingState) -> Optional[UUID]:
    """Extract user_id from graph state for logging (stream endpoint sets it)."""
    uid = state.get("user_id")
    if not uid:
        return None
    if isinstance(uid, UUID):
        return uid
    try:
        return UUID(uid) if isinstance(uid, str) else None
    except (ValueError, TypeError):
        return None


class ProblemSolveRequest(BaseModel):
    """Request model for problem solving conversation"""
    query: str
    problem_text: str
    history: list[Message] = []  # Optional; BE may load from DB instead
    conversation_id: int | None = None  # Optional Supabase conversation id (preferred for history loading)


class SuggestProblemRequest(BaseModel):
    """Request model for similar problem suggestions"""
    problem_text: str


class SuggestedProblemItem(BaseModel):
    """One suggested problem (statement only for FE buttons)"""
    statement: str


class SuggestProblemResponse(BaseModel):
    """Response for /suggest-problem: message + list of problems for FE buttons"""
    message: str
    problems: list[SuggestedProblemItem]


def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text that might contain markdown code blocks"""
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    
    raise ValueError("No JSON found in response")


async def perform_ocr(image_bytes: bytes) -> str:
    """Use Gemini Vision API to extract text from image"""
    log_json(
        source="ocr",
        level="info",
        message=f"Starting OCR for image of {len(image_bytes)} bytes",
        user_id=None,
        traceback=None,
    )

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from PIL import Image

    if not settings.google_api_key:
        log_json(
            source="ocr",
            level="error",
            message="GOOGLE_API_KEY not found in environment",
            user_id=None,
            traceback=None,
        )
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    log_json(
        source="ocr",
        level="info",
        message="Initializing Gemini Vision model",
        user_id=None,
        traceback=None,
    )
    vision_llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )
    
    prompt = """Extrage textul din această imagine. Dacă există formule matematice, grafice sau diagrame, 
descrie-le în detaliu. Returnează doar textul problemei, fără comentarii suplimentare.
Dacă există grafice sau diagrame, descrie-le clar și precis."""
    
    try:
        log_json(
            source="ocr",
            level="info",
            message="Converting image bytes to PIL Image",
            user_id=None,
            traceback=None,
        )
        # Convert bytes to PIL Image
        image = Image.open(BytesIO(image_bytes))
        log_json(
            source="ocr",
            level="info",
            message=f"Image opened: size={image.size}, mode={image.mode}",
            user_id=None,
            traceback=None,
        )
        
        # For langchain-google-genai, we can pass PIL Image directly in the content
        # The library will handle the conversion
        log_json(
            source="ocr",
            level="info",
            message="Creating message with PIL Image",
            user_id=None,
            traceback=None,
        )
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                image  # Pass PIL Image directly
            ]
        )
        
        log_json(
            source="ocr",
            level="info",
            message="Calling Gemini Vision API with PIL Image",
            user_id=None,
            traceback=None,
        )
        response = await vision_llm.ainvoke([message])
        log_json(
            source="ocr",
            level="info",
            message=f"OCR completed successfully, extracted {len(response.content)} characters",
            user_id=None,
            traceback=None,
        )
        return response.content.strip()
    except Exception as e:
        log_json(
            source="ocr",
            level="warning",
            message=f"Failed with PIL Image, trying base64 fallback: {e!s}",
            user_id=None,
            traceback=None,
        )
        # Fallback: try with base64
        try:
            log_json(
                source="ocr",
                level="info",
                message="Encoding image to base64",
                user_id=None,
                traceback=None,
            )
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            log_json(
                source="ocr",
                level="info",
                message=f"Base64 encoded, length: {len(image_base64)}",
                user_id=None,
                traceback=None,
            )
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
                ]
            )
            log_json(
                source="ocr",
                level="info",
                message="Calling Gemini Vision API with base64",
                user_id=None,
                traceback=None,
            )
            response = await vision_llm.ainvoke([message])
            log_json(
                source="ocr",
                level="info",
                message=f"OCR completed with base64 fallback, extracted {len(response.content)} characters",
                user_id=None,
                traceback=None,
            )
            return response.content.strip()
        except Exception as e2:
            import traceback as tb
            log_json(
                source="ocr",
                level="error",
                message=f"Both methods failed. Base64 error: {e2!s}",
                user_id=None,
                traceback=tb.format_exc(),
            )
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e2)}")


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
    log_json(
        source="solve_problem_upload",
        level="info",
        message=f"Upload request received. Filename: {file.filename}, Content-Type: {file.content_type}",
        user_id=user_id,
        traceback=None,
    )
    
    # Auth and quota check before any file read or OCR
    threshold = getattr(settings, "solve_monthly_quota_threshold", 0) or 0
    if threshold > 0:
        count = get_solve_quota_count(user_id, supabase)
        if count >= threshold:
            log_json(
                source="solve_problem_upload",
                level="info",
                message=f"Quota exceeded: user={user_id} count={count} threshold={threshold}",
                user_id=user_id,
                traceback=None,
            )
            raise HTTPException(
                status_code=403,
                detail=QUOTA_LIMIT_MESSAGE,
            )
    
    try:
        # Read image bytes first (before validation, to ensure we can read it)
        log_json(
            source="solve_problem_upload",
            level="info",
            message="Reading file bytes...",
            user_id=user_id,
            traceback=None,
        )
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            log_json(
                source="solve_problem_upload",
                level="error",
                message="File is empty",
                user_id=user_id,
                traceback=None,
            )
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        log_json(
            source="solve_problem_upload",
            level="info",
            message=f"Read {len(image_bytes)} bytes from file",
            user_id=user_id,
            traceback=None,
        )
        
        # Validate file is an image - check content_type first, but fall back to file extension
        # Be lenient - accept if either content_type OR file extension indicates it's an image
        is_valid_image = False
        validation_method = ""
        
        # First check content_type
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
            validation_method = f"content_type: {file.content_type}"
            log_json(
                source="solve_problem_upload",
                level="info",
                message=f"Validated by {validation_method}",
                user_id=user_id,
                traceback=None,
            )
        elif file.filename:
            # If content_type doesn't indicate image, check file extension
            valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            file_ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
            if f".{file_ext}" in valid_extensions:
                is_valid_image = True
                validation_method = f"file extension: .{file_ext}"
                log_json(
                    source="solve_problem_upload",
                    level="info",
                    message=f"Validated by {validation_method}",
                    user_id=user_id,
                    traceback=None,
                )
                if file.content_type:
                    log_json(
                        source="solve_problem_upload",
                        level="info",
                        message=f"Note: content_type was {file.content_type}, but file extension is valid",
                        user_id=user_id,
                        traceback=None,
                    )
            else:
                log_json(
                    source="solve_problem_upload",
                    level="warning",
                    message=f"File extension not recognized: .{file_ext}",
                    user_id=user_id,
                    traceback=None,
                )
        
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
        problem_text = await perform_ocr(image_bytes)
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
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


def _normalize_embedding(values: list[float]) -> list[float]:
    """Normalize embedding to unit length for cosine / inner-product similarity."""
    import math
    norm = math.sqrt(sum(x * x for x in values))
    if norm <= 0:
        return values
    return [x / norm for x in values]


def _embed_query(text: str) -> list[float]:
    """Embed a single query string with Gemini (1024-dim, RETRIEVAL_QUERY, normalized)."""
    from google import genai
    from google.genai import types

    if not settings.google_api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    client = genai.Client(api_key=settings.google_api_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=[text],
        config=types.EmbedContentConfig(
            output_dimensionality=1024,
            task_type="RETRIEVAL_QUERY",
        ),
    )
    if not result.embeddings or len(result.embeddings) == 0:
        raise HTTPException(status_code=500, detail="Embedding returned no result")
    vals = list(result.embeddings[0].values)
    return _normalize_embedding(vals)


@router.post("/suggest-problem", response_model=SuggestProblemResponse)
async def suggest_problem(
    body: SuggestProblemRequest,
    supabase=Depends(get_supabase_client),
):
    """
    Vector search in documents table; return top 5 similar problem statements.
    Used when the user taps "vreau probleme similare" after the first AI response.
    """
    problem_text = (body.problem_text or "").strip()
    if not problem_text:
        raise HTTPException(status_code=400, detail="problem_text is required and cannot be empty")

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
            user_id=None,
            traceback=tb.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    try:
        r = supabase.rpc("match_documents", {"query_embedding": query_embedding, "match_count": 5}).execute()
        rows = (r.data or []) if hasattr(r, "data") else []
    except Exception as e:
        import traceback as tb
        log_json(
            source="solve_problem_suggest",
            level="error",
            message=f"match_documents RPC failed: {e!s}",
            user_id=None,
            traceback=tb.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")

    doc_ids = [row.get("id") for row in rows]
    log_json(
        source="solve_problem_suggest",
        level="info",
        message=f"Document ids shown to user (check in DB): {doc_ids}",
        user_id=None,
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


def _make_detect_intent(llm):
    """Factory: Node 1 - Detect user intent (uses injected llm)."""

    async def detect_intent(state: ProblemSolvingState) -> ProblemSolvingState:
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"Node 1: detect_intent. Messages in state: {len(state.get('messages', []))}",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        messages_list = state.get("messages", [])

        # Check if this is the first user message (initial upload message)
        # We check if there's exactly one HumanMessage and it's likely the initial "Am încărcat problema" message
        if len(messages_list) == 1 and isinstance(messages_list[0], HumanMessage):
            user_message = messages_list[0].content.lower()
            # Check if it's the initial message pattern
            if "încărcat" in user_message or "problem" in user_message or len(user_message) < 50:
                log_json(
                    source="solve_problem_langgraph",
                    level="info",
                    message="Initial message detected - returning initial question",
                    user_id=_user_id_from_state(state),
                    traceback=None,
                )
                problem_text = state.get("problem_text", "")
                if problem_text:
                    initial_message = AIMessage(
                        content=f"Pare o problemă interesantă!\n\n**Problema:**\n{problem_text}\n\nAi vrea o rezolvare completă sau un hint?"
                    )
                else:
                    initial_message = AIMessage(
                        content="Pare o problemă interesantă! Ai vrea o rezolvare completă sau un hint?"
                    )
                log_json(
                    source="solve_problem_langgraph",
                    level="info",
                    message="Returning initial_question intent",
                    user_id=_user_id_from_state(state),
                    traceback=None,
                )
                new_state = {
                    **state,
                    "intent": "initial_question",
                }
                new_state["messages"] = [initial_message]
                return new_state

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Not initial message - detecting intent from user message",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        system_prompt = PROMPTS['problem_solving']['intent_detector']['system_prompt']

        # Build conversation context
        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add current query if available
        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                log_json(
                    source="solve_problem_langgraph",
                    level="info",
                    message=f"Last user message: {last_message.content[:50]}...",
                    user_id=_user_id_from_state(state),
                    traceback=None,
                )
                messages.append(HumanMessage(content=f"Mesajul elevului: {last_message.content}"))

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Calling LLM for intent detection...",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        response = await llm.ainvoke(messages)
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"LLM response received: {response.content[:100]}...",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        # Extract intent from response
        try:
            result = extract_json_from_text(response.content)
            intent = result.get("intent", "new_hint")
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Intent extracted from JSON: {intent}",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        except Exception:
            log_json(
                source="solve_problem_langgraph",
                level="warning",
                message="Failed to extract JSON, using keyword detection",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            content_lower = response.content.lower()
            if any(word in content_lower for word in ["solve", "soluție", "completă", "arătă"]):
                intent = "solve"
            elif any(word in content_lower for word in ["progres", "rezolvat", "făcut"]):
                intent = "progress"
            else:
                intent = "new_hint"
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Intent detected via keywords: {intent}",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"Node 1 complete: intent={intent}",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return {
            **state,
            "intent": intent,
            "messages": [response] if state.get('messages') else []
        }

    return detect_intent


def _make_provide_hint(llm):
    """Factory: Node 2 - Provide hint (uses injected llm)."""

    async def provide_hint(state: ProblemSolvingState, config=None) -> ProblemSolvingState:
        """Node 2: Provide a new hint with explanation and follow-up questions"""
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 2: provide_hint",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        # If we already have a message (initial question), just return it
        if state.get("intent") == "initial_question" and state.get("messages"):
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Initial question already present, returning state",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            if stream_queue is not None:
                existing_content = state["messages"][-1].content
                stream_queue.put_nowait(existing_content)
                stream_queue.put_nowait(None)
            return state

        system_prompt = PROMPTS['problem_solving']['hint_provider']['system_prompt']

        messages = [SystemMessage(content=system_prompt)]

        # Add problem text
        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added problem text ({len(state['problem_text'])} chars)",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add hint level context
        hint_level = state.get("hint_level", 0) + 1
        messages.append(SystemMessage(content=f"Nivelul hint-ului curent: {hint_level}"))
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"Hint level: {hint_level}",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        # Add student work if available
        if state.get("student_work"):
            messages.append(SystemMessage(content=f"Progresul elevului până acum: {state['student_work']}"))
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added student work: {state['student_work'][:50]}...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Streaming hint...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            accumulated = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Hint generated: {len(full_content)} characters (streamed)",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        else:
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Calling LLM to generate hint...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            response = await llm.ainvoke(messages)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Hint generated: {len(response.content)} characters",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 2 complete",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        return {
            **state,
            "messages": [response],
            "hint_level": hint_level,
        }

    return provide_hint


def _make_evaluate_progress(llm):
    """Factory: Node 3 - Evaluate progress (uses injected llm)."""

    async def evaluate_progress(state: ProblemSolvingState) -> ProblemSolvingState:
        """Node 3: Evaluate student's progress/work"""
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 3: evaluate_progress",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        system_prompt = PROMPTS["problem_solving"]["progress_evaluator"]["system_prompt"]
        messages = [SystemMessage(content=system_prompt)]

        # Add problem text
        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Added problem text",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Extract student work from last message
        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                student_work = last_message.content
                messages.append(SystemMessage(content=f"Progresul elevului: {student_work}"))
                log_json(
                    source="solve_problem_langgraph",
                    level="info",
                    message=f"Evaluating student work: {student_work[:50]}...",
                    user_id=_user_id_from_state(state),
                    traceback=None,
                )

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Calling LLM to evaluate progress...",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        response = await llm.ainvoke(messages)
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"Progress evaluation complete: {len(response.content)} characters. Node 3 complete",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        return {
            **state,
            "messages": [response],
            "student_work": state.get('messages', [])[-1].content if state.get('messages') else "",
        }

    return evaluate_progress


def _make_detect_progress_intent(llm):
    """Factory: Node 4 - Detect progress intent (uses injected llm)."""

    async def detect_progress_intent(state: ProblemSolvingState) -> ProblemSolvingState:
        """Node 4: Detect if progress is good or bad"""
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 4: detect_progress_intent",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        system_prompt = PROMPTS["problem_solving"]["progress_intent_detector"]["system_prompt"]
        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Calling LLM to detect progress intent...",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        response = await llm.ainvoke(messages)
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"LLM response: {response.content[:100]}...",
            user_id=_user_id_from_state(state),
            traceback=None,
        )

        # Extract progress intent
        try:
            result = extract_json_from_text(response.content)
            progress_intent = result.get("progress_intent", "good")
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Progress intent extracted from JSON: {progress_intent}",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        except Exception:
            log_json(
                source="solve_problem_langgraph",
                level="warning",
                message="Failed to extract JSON, using keyword detection",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            content_lower = response.content.lower()
            if any(word in content_lower for word in ["greșit", "incorect", "eroare", "nu e bine"]):
                progress_intent = "bad"
            else:
                progress_intent = "good"
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Progress intent detected via keywords: {progress_intent}",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        log_json(
            source="solve_problem_langgraph",
            level="info",
            message=f"Node 4 complete: progress_intent={progress_intent}",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return {
            **state,
            "intent": progress_intent,
            "messages": [response],
        }

    return detect_progress_intent


def _make_explain_error(llm):
    """Factory: Node 5 - Explain errors (uses injected llm)."""

    async def explain_error(state: ProblemSolvingState, config=None) -> ProblemSolvingState:
        """Node 5: Explain errors without giving hints"""
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 5: explain_error",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        system_prompt = PROMPTS["problem_solving"]["error_explainer"]["system_prompt"]
        messages = [SystemMessage(content=system_prompt)]

        # Add problem text
        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Added problem text",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Streaming error explanation...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            accumulated = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Error explanation generated: {len(full_content)} characters (streamed). Node 5 complete",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        else:
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Calling LLM to explain errors...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            response = await llm.ainvoke(messages)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Error explanation generated: {len(response.content)} characters. Node 5 complete",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        return {
            **state,
            "messages": [response],
        }

    return explain_error


def _make_provide_solution(llm):
    """Factory: Node 6 - Provide full solution (uses injected llm)."""

    async def provide_solution(state: ProblemSolvingState, config=None) -> ProblemSolvingState:
        """Node 6: Provide full solution"""
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Node 6: provide_solution",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        system_prompt = PROMPTS["problem_solving"]["solution_provider"]["system_prompt"]
        messages = [SystemMessage(content=system_prompt)]

        # Add problem text
        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Added problem text",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        # Add conversation history
        if state.get("messages"):
            messages.extend(state["messages"][-10:])
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Added {len(state['messages'][-10:])} messages to context",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Streaming full solution...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            accumulated = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Full solution generated: {len(full_content)} characters (streamed). Node 6 complete",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
        else:
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message="Calling LLM to generate full solution...",
                user_id=_user_id_from_state(state),
                traceback=None,
            )
            response = await llm.ainvoke(messages)
            log_json(
                source="solve_problem_langgraph",
                level="info",
                message=f"Full solution generated: {len(response.content)} characters. Node 6 complete",
                user_id=_user_id_from_state(state),
                traceback=None,
            )

        return {
            **state,
            "messages": [response],
            "full_solution_requested": True,
        }

    return provide_solution


def route_after_intent(state: ProblemSolvingState) -> str:
    """Route after initial intent detection"""
    intent = state.get("intent", "new_hint")
    log_json(
        source="solve_problem_langgraph",
        level="info",
        message=f"Routing after intent detection: intent={intent}",
        user_id=_user_id_from_state(state),
        traceback=None,
    )
    if intent == "initial_question":
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to provide_hint (initial question)",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "provide_hint"
    elif intent == "solve":
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to provide_solution",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "provide_solution"
    elif intent == "new_hint":
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to provide_hint",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "provide_hint"
    elif intent == "progress":
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to evaluate_progress",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "evaluate_progress"
    else:
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Unknown intent, defaulting to provide_hint",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "provide_hint"


def route_after_progress_eval(state: ProblemSolvingState) -> str:
    """Route after progress evaluation"""
    log_json(
        source="solve_problem_langgraph",
        level="info",
        message="Routing to detect_progress_intent after progress evaluation",
        user_id=_user_id_from_state(state),
        traceback=None,
    )
    return "detect_progress_intent"


def route_after_progress_intent(state: ProblemSolvingState) -> str:
    """Route after progress intent detection"""
    intent = state.get("intent", "good")
    log_json(
        source="solve_problem_langgraph",
        level="info",
        message=f"Routing after progress intent: intent={intent}",
        user_id=_user_id_from_state(state),
        traceback=None,
    )
    if intent == "bad":
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to explain_error (bad progress)",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "explain_error"
    else:
        log_json(
            source="solve_problem_langgraph",
            level="info",
            message="Routing to provide_hint (good progress)",
            user_id=_user_id_from_state(state),
            traceback=None,
        )
        return "provide_hint"


def build_problem_solving_graph(llm):
    """Build the problem solving state graph with injected LLM."""
    workflow = StateGraph(ProblemSolvingState)

    # Add nodes (each node is created with the injected llm)
    workflow.add_node("detect_intent", _make_detect_intent(llm))
    workflow.add_node("provide_hint", _make_provide_hint(llm))
    workflow.add_node("evaluate_progress", _make_evaluate_progress(llm))
    workflow.add_node("detect_progress_intent", _make_detect_progress_intent(llm))
    workflow.add_node("explain_error", _make_explain_error(llm))
    workflow.add_node("provide_solution", _make_provide_solution(llm))
    
    # Set entry point
    workflow.set_entry_point("detect_intent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "provide_solution": "provide_solution",
            "provide_hint": "provide_hint",
            "evaluate_progress": "evaluate_progress",
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate_progress",
        route_after_progress_eval,
        {
            "detect_progress_intent": "detect_progress_intent",
        }
    )
    
    workflow.add_conditional_edges(
        "detect_progress_intent",
        route_after_progress_intent,
        {
            "explain_error": "explain_error",
            "provide_hint": "provide_hint",
        }
    )
    
    # Terminal nodes
    workflow.add_edge("provide_solution", END)
    workflow.add_edge("provide_hint", END)
    workflow.add_edge("explain_error", END)
    
    return workflow.compile()


@router.post("/stream")
async def solve_problem_stream(
    request: ProblemSolveRequest,
    user_id: UUID = Depends(get_current_user_id),
    llm=Depends(get_llm),
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
    if threshold > 0:
        count = get_solve_quota_count(user_id, supabase)
        if count > threshold:
            log_json(
                source="solve_problem_stream",
                level="info",
                message=f"Quota exceeded: user={user_id} count={count} threshold={threshold}",
                user_id=user_id,
                traceback=None,
            )

            async def quota_limit_stream():
                for char in QUOTA_LIMIT_MESSAGE:
                    content = char.replace("\n", "\\n")
                    yield f"data: {content}\n\n"
                    await asyncio.sleep(0.01)
                yield "data: [DONE]\n\n"

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
            first_token_received = False

            # Prefer loading history from Supabase by conversation_id when provided,
            # fall back to the history array from the client for backwards compatibility.
            history = request.history
            if request.conversation_id is not None:
                loaded = load_conversation_history_for_user(user_id, request.conversation_id, supabase)
                if loaded:
                    history = loaded
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
            config = {"configurable": {"stream_queue": stream_queue}}
            log_json(
                source="solve_problem_stream",
                level="info",
                message="Building and invoking LangGraph (streaming)...",
                user_id=user_id,
                traceback=None,
            )
            graph = build_problem_solving_graph(llm)
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
                    time_to_first_token = time.time() - start_time
                    metadata = json.dumps({"ttft": round(time_to_first_token, 3)})
                    log_json(
                        source="solve_problem_stream",
                        level="info",
                        message=f"Time to first token: {time_to_first_token:.3f}s",
                        user_id=user_id,
                        traceback=None,
                    )
                    yield f"data: [META]{metadata}\n\n"
                    first_content_chunk = False
                content = item.replace("\n", "\\n")
                yield f"data: {content}\n\n"

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
            yield "data: [DONE]\n\n"
            
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
            error_message = f"Eroare: {str(e)}"
            yield f"data: {error_message}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )