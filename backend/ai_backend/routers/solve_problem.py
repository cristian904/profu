"""
Solve Problem Router - Guided problem solving with image upload and OCR.
Uses LangGraph to manage the conversation flow with intent detection and hint generation.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel
import asyncio
import time
import json
import re
import base64
import logging
from io import BytesIO

from ai_backend.config import settings
from .common import get_llm, Message, PROMPTS

# Set up logger
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/solve-problem", tags=["solve_problem"])


class ProblemSolvingState(TypedDict):
    """State for the problem solving graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    problem_text: str
    intent: str
    student_work: str
    hint_level: int
    full_solution_requested: bool


class ProblemSolveRequest(BaseModel):
    """Request model for problem solving conversation"""
    query: str
    problem_text: str
    history: list[Message] = []


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
    logger.info(f"[OCR] Starting OCR for image of {len(image_bytes)} bytes")

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from PIL import Image

    if not settings.google_api_key:
        logger.error("[OCR] GOOGLE_API_KEY not found in environment")
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    logger.info("[OCR] Initializing Gemini Vision model")
    vision_llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )
    
    prompt = """Extrage textul din această imagine. Dacă există formule matematice, grafice sau diagrame, 
descrie-le în detaliu. Returnează doar textul problemei, fără comentarii suplimentare.
Dacă există grafice sau diagrame, descrie-le clar și precis."""
    
    try:
        logger.info("[OCR] Converting image bytes to PIL Image")
        # Convert bytes to PIL Image
        image = Image.open(BytesIO(image_bytes))
        logger.info(f"[OCR] Image opened: size={image.size}, mode={image.mode}")
        
        # For langchain-google-genai, we can pass PIL Image directly in the content
        # The library will handle the conversion
        logger.info("[OCR] Creating message with PIL Image")
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                image  # Pass PIL Image directly
            ]
        )
        
        logger.info("[OCR] Calling Gemini Vision API with PIL Image")
        response = await vision_llm.ainvoke([message])
        logger.info(f"[OCR] OCR completed successfully, extracted {len(response.content)} characters")
        return response.content.strip()
    except Exception as e:
        logger.warning(f"[OCR] Failed with PIL Image, trying base64 fallback: {str(e)}")
        # Fallback: try with base64
        try:
            logger.info("[OCR] Encoding image to base64")
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"[OCR] Base64 encoded, length: {len(image_base64)}")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
                ]
            )
            logger.info("[OCR] Calling Gemini Vision API with base64")
            response = await vision_llm.ainvoke([message])
            logger.info(f"[OCR] OCR completed with base64 fallback, extracted {len(response.content)} characters")
            return response.content.strip()
        except Exception as e2:
            logger.error(f"[OCR] Both methods failed. Base64 error: {str(e2)}")
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e2)}")


@router.post("/upload")
async def upload_problem_image(
    file: UploadFile = File(...)
):
    """
    Upload an image of a problem and perform OCR.
    Returns the extracted problem text.
    """
    logger.info(f"[UPLOAD] ===== Upload request received =====")
    logger.info(f"[UPLOAD] Filename: {file.filename}, Content-Type: {file.content_type}")
    
    try:
        # Read image bytes first (before validation, to ensure we can read it)
        logger.info("[UPLOAD] Reading file bytes...")
        image_bytes = await file.read()
        
        if len(image_bytes) == 0:
            logger.error("[UPLOAD] File is empty")
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        logger.info(f"[UPLOAD] Read {len(image_bytes)} bytes from file")
        
        # Validate file is an image - check content_type first, but fall back to file extension
        # Be lenient - accept if either content_type OR file extension indicates it's an image
        is_valid_image = False
        validation_method = ""
        
        # First check content_type
        if file.content_type and file.content_type.startswith('image/'):
            is_valid_image = True
            validation_method = f"content_type: {file.content_type}"
            print(f"[UPLOAD] Validated by {validation_method}")
        elif file.filename:
            # If content_type doesn't indicate image, check file extension
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            if f'.{file_ext}' in valid_extensions:
                is_valid_image = True
                validation_method = f"file extension: .{file_ext}"
                print(f"[UPLOAD] Validated by {validation_method}")
                if file.content_type:
                    print(f"[UPLOAD] Note: content_type was {file.content_type}, but file extension is valid")
            else:
                print(f"[UPLOAD] Warning: file extension not recognized: .{file_ext}")
        
        if not is_valid_image:
            # Only reject if we can't validate it as an image by either method
            raise HTTPException(
                status_code=400, 
                detail=f"File must be an image. content_type={file.content_type}, filename={file.filename}. "
                       f"Valid extensions: .jpg, .jpeg, .png, .gif, .bmp, .webp"
            )
        
        # Perform OCR
        logger.info("[UPLOAD] Starting OCR process...")
        problem_text = await perform_ocr(image_bytes)
        logger.info(f"[UPLOAD] OCR completed successfully, extracted {len(problem_text)} characters")
        logger.info(f"[UPLOAD] Problem text preview: {problem_text[:100]}...")
        
        logger.info("[UPLOAD] ===== Upload completed successfully =====")
        return {
            "problem_text": problem_text,
            "filename": file.filename,
            "content_type": file.content_type
        }
    except HTTPException:
        logger.error("[UPLOAD] HTTPException raised, re-raising")
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[UPLOAD] Error processing image: {str(e)}")
        logger.error(f"[UPLOAD] Traceback: {error_trace}")
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
async def suggest_problem(body: SuggestProblemRequest):
    """
    Vector search in documents table; return top 5 similar problem statements.
    Used when the user taps "vreau probleme similare" after the first AI response.
    """
    problem_text = (body.problem_text or "").strip()
    if not problem_text:
        raise HTTPException(status_code=400, detail="problem_text is required and cannot be empty")

    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set",
        )

    try:
        query_embedding = _embed_query(problem_text)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[SUGGEST] Embedding failed")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_key)
        r = client.rpc("match_documents", {"query_embedding": query_embedding, "match_count": 5}).execute()
        rows = (r.data or []) if hasattr(r, "data") else []
    except Exception as e:
        logger.exception("[SUGGEST] match_documents RPC failed")
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")

    doc_ids = [row.get("id") for row in rows]
    logger.info("[SUGGEST] document ids shown to user (check in DB): %s", doc_ids)

    problems = [SuggestedProblemItem(statement=(row.get("content") or "")) for row in rows]
    # Build message with full problem text for each
    if not problems:
        message = "Nu am găsit probleme similare în baza de date."
    else:
        parts = [f"{i + 1}. {p.statement}" for i, p in enumerate(problems)]
        message = "Uite " + str(len(problems)) + " probleme asemanatoare cu acesta:\n\n" + "\n\n".join(parts)

    return SuggestProblemResponse(message=message, problems=problems)


async def detect_intent(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 1: Detect user intent (solve, new_hint, progress)"""
    logger.info("[LANGGRAPH] ===== Node 1: detect_intent =====")
    logger.info(f"[LANGGRAPH] Messages in state: {len(state.get('messages', []))}")
    
    llm = get_llm()
    
    # Check if this is the initial message (no explicit intent yet)
    # If so, ask the user about their preference
    messages_list = state.get('messages', [])
    
    # #region agent log - Hypothesis A: Check initial message detection
    import json
    log_data = {
        "location": "solve_problem.py:detect_intent",
        "message": "Checking for initial message",
        "data": {
            "messages_count": len(messages_list),
            "first_message_type": type(messages_list[0]).__name__ if messages_list else "None",
            "first_message_content": messages_list[0].content[:100] if messages_list and hasattr(messages_list[0], 'content') else "N/A",
            "problem_text_length": len(state.get('problem_text', ''))
        },
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "A"
    }
    try:
        with open(r'd:\_CRISTIAN\profu\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
    except Exception:
        pass
    # #endregion
    
    # Check if this is the first user message (initial upload message)
    # We check if there's exactly one HumanMessage and it's likely the initial "Am încărcat problema" message
    if len(messages_list) == 1 and isinstance(messages_list[0], HumanMessage):
        user_message = messages_list[0].content.lower()
        # Check if it's the initial message pattern
        if 'încărcat' in user_message or 'problem' in user_message or len(user_message) < 50:
            logger.info("[LANGGRAPH] Initial message detected - returning initial question")
            # Initial state - ask about solution preference
            problem_text = state.get('problem_text', '')
            if problem_text:
                initial_message = AIMessage(
                    content=f"Pare o problemă interesantă!\n\n**Problema:**\n{problem_text}\n\nAi vrea o rezolvare completă sau un hint?"
                )
            else:
                initial_message = AIMessage(
                    content="Pare o problemă interesantă! Ai vrea o rezolvare completă sau un hint?"
                )
            logger.info("[LANGGRAPH] Returning initial_question intent")
            
            # #region agent log - Hypothesis A: Initial message created
            log_data = {
                "location": "solve_problem.py:detect_intent",
                "message": "Initial message created",
                "data": {
                    "has_problem_text": bool(problem_text),
                    "initial_message_length": len(initial_message.content)
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }
            try:
                with open(r'd:\_CRISTIAN\profu\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
            except Exception:
                pass
            # #endregion
            
            # Return state with initial message
            # Note: add_messages will merge this with existing messages, so we need to be careful
            new_state = {
                **state,
                "intent": "initial_question",  # Special intent for initial question
            }
            # Set messages to only contain the initial message (don't merge with existing)
            new_state["messages"] = [initial_message]
            
            # #region agent log - Hypothesis A: State returned with initial message
            log_data = {
                "location": "solve_problem.py:detect_intent",
                "message": "Returning state with initial message",
                "data": {
                    "intent": new_state.get('intent'),
                    "messages_count": len(new_state.get('messages', [])),
                    "message_content_preview": new_state.get('messages', [])[0].content[:100] if new_state.get('messages') else "None"
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            }
            try:
                with open(r'd:\_CRISTIAN\profu\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_data) + '\n')
            except Exception:
                pass
            # #endregion
            
            return new_state
    
    logger.info("[LANGGRAPH] Not initial message - detecting intent from user message")
    
    system_prompt = PROMPTS['problem_solving']['intent_detector']['system_prompt']
    
    # Build conversation context
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])  # Last 10 messages for context
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    # Add current query if available
    if state.get('messages') and len(state['messages']) > 0:
        last_message = state['messages'][-1]
        if isinstance(last_message, HumanMessage):
            logger.info(f"[LANGGRAPH] Last user message: {last_message.content[:50]}...")
            messages.append(HumanMessage(content=f"Mesajul elevului: {last_message.content}"))
    
    logger.info("[LANGGRAPH] Calling LLM for intent detection...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] LLM response received: {response.content[:100]}...")
    
    # Extract intent from response
    try:
        result = extract_json_from_text(response.content)
        intent = result.get('intent', 'new_hint')
        logger.info(f"[LANGGRAPH] Intent extracted from JSON: {intent}")
    except:
        logger.warning("[LANGGRAPH] Failed to extract JSON, using keyword detection")
        # Fallback: simple keyword detection
        content_lower = response.content.lower()
        if any(word in content_lower for word in ['solve', 'soluție', 'completă', 'arătă']):
            intent = 'solve'
        elif any(word in content_lower for word in ['progres', 'rezolvat', 'făcut']):
            intent = 'progress'
        else:
            intent = 'new_hint'
        logger.info(f"[LANGGRAPH] Intent detected via keywords: {intent}")
    
    logger.info(f"[LANGGRAPH] ===== Node 1 complete: intent={intent} =====")
    return {
        **state,
        "intent": intent,
        "messages": [response] if state.get('messages') else []
    }


async def provide_hint(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 2: Provide a new hint with explanation and follow-up questions"""
    logger.info("[LANGGRAPH] ===== Node 2: provide_hint =====")
    
    # #region agent log - Hypothesis B: Check if initial question should be returned
    import json
    log_data = {
        "location": "solve_problem.py:provide_hint",
        "message": "Checking if initial question present",
        "data": {
            "intent": state.get('intent'),
            "has_messages": bool(state.get('messages')),
            "messages_count": len(state.get('messages', [])),
            "last_message_type": type(state.get('messages', [])[-1]).__name__ if state.get('messages') else "None"
        },
        "timestamp": int(time.time() * 1000),
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "B"
    }
    try:
        with open(r'd:\_CRISTIAN\profu\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data) + '\n')
    except Exception:
        pass
    # #endregion
    
    # If we already have a message (initial question), just return it
    if state.get('intent') == 'initial_question' and state.get('messages'):
        logger.info("[LANGGRAPH] Initial question already present, returning state")
        # #region agent log - Hypothesis B: Returning initial question
        log_data = {
            "location": "solve_problem.py:provide_hint",
            "message": "Returning initial question without LLM call",
            "data": {
                "message_content_preview": state.get('messages', [])[-1].content[:100] if state.get('messages') else "None"
            },
            "timestamp": int(time.time() * 1000),
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B"
        }
        try:
            with open(r'd:\_CRISTIAN\profu\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data) + '\n')
        except Exception:
            pass
        # #endregion
        return state
    
    llm = get_llm()
    
    system_prompt = PROMPTS['problem_solving']['hint_provider']['system_prompt']
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Add problem text
    if state.get('problem_text'):
        messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
        logger.info(f"[LANGGRAPH] Added problem text ({len(state['problem_text'])} chars)")
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    # Add hint level context
    hint_level = state.get('hint_level', 0) + 1
    messages.append(SystemMessage(content=f"Nivelul hint-ului curent: {hint_level}"))
    logger.info(f"[LANGGRAPH] Hint level: {hint_level}")
    
    # Add student work if available
    if state.get('student_work'):
        messages.append(SystemMessage(content=f"Progresul elevului până acum: {state['student_work']}"))
        logger.info(f"[LANGGRAPH] Added student work: {state['student_work'][:50]}...")
    
    logger.info("[LANGGRAPH] Calling LLM to generate hint...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] Hint generated: {len(response.content)} characters")
    logger.info(f"[LANGGRAPH] ===== Node 2 complete =====")
    
    return {
        **state,
        "messages": [response],
        "hint_level": hint_level,
    }


async def evaluate_progress(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 3: Evaluate student's progress/work"""
    logger.info("[LANGGRAPH] ===== Node 3: evaluate_progress =====")
    
    llm = get_llm()
    
    system_prompt = PROMPTS['problem_solving']['progress_evaluator']['system_prompt']
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Add problem text
    if state.get('problem_text'):
        messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
        logger.info(f"[LANGGRAPH] Added problem text")
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    # Extract student work from last message
    if state.get('messages') and len(state['messages']) > 0:
        last_message = state['messages'][-1]
        if isinstance(last_message, HumanMessage):
            student_work = last_message.content
            messages.append(SystemMessage(content=f"Progresul elevului: {student_work}"))
            logger.info(f"[LANGGRAPH] Evaluating student work: {student_work[:50]}...")
    
    logger.info("[LANGGRAPH] Calling LLM to evaluate progress...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] Progress evaluation complete: {len(response.content)} characters")
    logger.info(f"[LANGGRAPH] ===== Node 3 complete =====")
    
    return {
        **state,
        "messages": [response],
        "student_work": state.get('messages', [])[-1].content if state.get('messages') else "",
    }


async def detect_progress_intent(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 4: Detect if progress is good or bad"""
    logger.info("[LANGGRAPH] ===== Node 4: detect_progress_intent =====")
    
    llm = get_llm()
    
    system_prompt = PROMPTS['problem_solving']['progress_intent_detector']['system_prompt']
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    logger.info("[LANGGRAPH] Calling LLM to detect progress intent...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] LLM response: {response.content[:100]}...")
    
    # Extract progress intent
    try:
        result = extract_json_from_text(response.content)
        progress_intent = result.get('progress_intent', 'good')
        logger.info(f"[LANGGRAPH] Progress intent extracted from JSON: {progress_intent}")
    except:
        logger.warning("[LANGGRAPH] Failed to extract JSON, using keyword detection")
        # Fallback: keyword detection
        content_lower = response.content.lower()
        if any(word in content_lower for word in ['greșit', 'incorect', 'eroare', 'nu e bine']):
            progress_intent = 'bad'
        else:
            progress_intent = 'good'
        logger.info(f"[LANGGRAPH] Progress intent detected via keywords: {progress_intent}")
    
    logger.info(f"[LANGGRAPH] ===== Node 4 complete: progress_intent={progress_intent} =====")
    return {
        **state,
        "intent": progress_intent,
        "messages": [response],
    }


async def explain_error(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 5: Explain errors without giving hints"""
    logger.info("[LANGGRAPH] ===== Node 5: explain_error =====")
    
    llm = get_llm()
    
    system_prompt = PROMPTS['problem_solving']['error_explainer']['system_prompt']
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Add problem text
    if state.get('problem_text'):
        messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
        logger.info(f"[LANGGRAPH] Added problem text")
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    logger.info("[LANGGRAPH] Calling LLM to explain errors...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] Error explanation generated: {len(response.content)} characters")
    logger.info(f"[LANGGRAPH] ===== Node 5 complete =====")
    
    return {
        **state,
        "messages": [response],
    }


async def provide_solution(state: ProblemSolvingState) -> ProblemSolvingState:
    """Node 6: Provide full solution"""
    logger.info("[LANGGRAPH] ===== Node 6: provide_solution =====")
    
    llm = get_llm()
    
    system_prompt = PROMPTS['problem_solving']['solution_provider']['system_prompt']
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Add problem text
    if state.get('problem_text'):
        messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))
        logger.info(f"[LANGGRAPH] Added problem text")
    
    # Add conversation history
    if state.get('messages'):
        messages.extend(state['messages'][-10:])
        logger.info(f"[LANGGRAPH] Added {len(state['messages'][-10:])} messages to context")
    
    logger.info("[LANGGRAPH] Calling LLM to generate full solution...")
    response = await llm.ainvoke(messages)
    logger.info(f"[LANGGRAPH] Full solution generated: {len(response.content)} characters")
    logger.info(f"[LANGGRAPH] ===== Node 6 complete =====")
    
    return {
        **state,
        "messages": [response],
        "full_solution_requested": True,
    }


def route_after_intent(state: ProblemSolvingState) -> str:
    """Route after initial intent detection"""
    intent = state.get('intent', 'new_hint')
    logger.info(f"[LANGGRAPH] Routing after intent detection: intent={intent}")
    
    if intent == 'initial_question':
        logger.info("[LANGGRAPH] Routing to provide_hint (initial question)")
        return 'provide_hint'  # This will be skipped, message already in state
    elif intent == 'solve':
        logger.info("[LANGGRAPH] Routing to provide_solution")
        return 'provide_solution'
    elif intent == 'new_hint':
        logger.info("[LANGGRAPH] Routing to provide_hint")
        return 'provide_hint'
    elif intent == 'progress':
        logger.info("[LANGGRAPH] Routing to evaluate_progress")
        return 'evaluate_progress'
    else:
        logger.info(f"[LANGGRAPH] Unknown intent, defaulting to provide_hint")
        return 'provide_hint'


def route_after_progress_eval(state: ProblemSolvingState) -> str:
    """Route after progress evaluation"""
    logger.info("[LANGGRAPH] Routing to detect_progress_intent after progress evaluation")
    return 'detect_progress_intent'


def route_after_progress_intent(state: ProblemSolvingState) -> str:
    """Route after progress intent detection"""
    intent = state.get('intent', 'good')
    logger.info(f"[LANGGRAPH] Routing after progress intent: intent={intent}")
    
    if intent == 'bad':
        logger.info("[LANGGRAPH] Routing to explain_error (bad progress)")
        return 'explain_error'
    else:
        logger.info("[LANGGRAPH] Routing to provide_hint (good progress)")
        return 'provide_hint'


def build_problem_solving_graph():
    """Build the problem solving state graph"""
    workflow = StateGraph(ProblemSolvingState)
    
    # Add nodes
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("provide_hint", provide_hint)
    workflow.add_node("evaluate_progress", evaluate_progress)
    workflow.add_node("detect_progress_intent", detect_progress_intent)
    workflow.add_node("explain_error", explain_error)
    workflow.add_node("provide_solution", provide_solution)
    
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
async def solve_problem_stream(request: ProblemSolveRequest):
    """
    Streaming endpoint for guided problem solving.
    Uses LangGraph to manage conversation flow with intent detection and hint generation.
    """
    logger.info(f"[STREAM] ===== Stream request received =====")
    logger.info(f"[STREAM] Query: {request.query[:50]}...")
    logger.info(f"[STREAM] Problem text length: {len(request.problem_text)}")
    logger.info(f"[STREAM] History length: {len(request.history)}")
    
    async def generate():
        try:
            start_time = time.time()
            first_token_received = False
            
            logger.info("[STREAM] Building initial state...")
            # Build initial state
            initial_state: ProblemSolvingState = {
                "messages": [],
                "problem_text": request.problem_text,
                "intent": "",
                "student_work": "",
                "hint_level": 0,
                "full_solution_requested": False,
            }
            
            # Build conversation history
            if request.history:
                logger.info(f"[STREAM] Adding {len(request.history)} messages from history")
                for msg in request.history:
                    if msg.role == "user":
                        initial_state["messages"].append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        initial_state["messages"].append(AIMessage(content=msg.content))
            
            # Add current query
            logger.info(f"[STREAM] Adding current query to state")
            initial_state["messages"].append(HumanMessage(content=request.query))
            logger.info(f"[STREAM] Total messages in state: {len(initial_state['messages'])}")
            
            # Run the graph
            logger.info("[STREAM] Building and invoking LangGraph...")
            graph = build_problem_solving_graph()
            result = await graph.ainvoke(initial_state)
            logger.info(f"[STREAM] Graph execution complete. Final intent: {result.get('intent')}")
            
            # Stream the response
            if result.get('messages'):
                response_message = result['messages'][-1]
                logger.info(f"[STREAM] Response message ready: {len(response_message.content)} characters")
                
                # Send metadata
                time_to_first_token = time.time() - start_time
                metadata = json.dumps({"ttft": round(time_to_first_token, 3)})
                logger.info(f"[STREAM] Time to first token: {time_to_first_token:.3f}s")
                yield f"data: [META]{metadata}\n\n"
                
                # Stream the content character by character
                logger.info("[STREAM] Starting to stream response...")
                char_count = 0
                for char in response_message.content:
                    content = char.replace('\n', '\\n')
                    yield f"data: {content}\n\n"
                    char_count += 1
                    await asyncio.sleep(0.01)
                logger.info(f"[STREAM] Streamed {char_count} characters")
            else:
                logger.warning("[STREAM] No messages in result!")
            
            # Small delay to ensure all content is flushed before sending [DONE]
            await asyncio.sleep(0.1)
            
            # Signal completion - ensure it's sent
            logger.info("[STREAM] Sending [DONE] signal...")
            done_signal = "data: [DONE]\n\n"
            yield done_signal
            logger.info("[STREAM] [DONE] signal sent")
            
            # Additional delay to ensure [DONE] is flushed
            await asyncio.sleep(0.05)
            logger.info("[STREAM] ===== Stream completed successfully =====")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[STREAM] Error in stream: {str(e)}")
            logger.error(f"[STREAM] Traceback: {error_trace}")
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