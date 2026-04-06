"""
OCR helpers for solve-problem.

Uses Gemini Vision via LangChain to extract problem text from uploaded images.
"""

import base64
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from ai_backend.config import settings
from ai_backend.langfuse.context import langfuse_trace_context
from profu_logging.feature_logger import get_feature_logger


async def perform_ocr(
    image_bytes: bytes,
    *,
    user_id: Optional[UUID] = None,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Use Gemini Vision API to extract text from an image.

    Args:
        image_bytes: Raw uploaded image bytes.
        user_id: Authenticated user id (for Langfuse tracing).
        trace_id: Optional Langfuse trace id (32-char hex).
        session_id: Optional Langfuse session id for grouping traces.

    Returns:
        Extracted problem text.

    Raises:
        HTTPException: When OCR fails or configuration is missing.
    """
    log = get_feature_logger(source="ocr")
    log.info(f"Starting OCR for image of {len(image_bytes)} bytes", user_id=user_id)

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from PIL import Image

    if not settings.google_api_key:
        log.error("GOOGLE_API_KEY not found in environment", user_id=user_id, traceback=None)
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    log.info("Initializing Gemini Vision model", user_id=user_id)
    vision_llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )

    prompt = (
        "Extrage textul din această imagine. Dacă există formule matematice, grafice sau diagrame, \n"
        "descrie-le în detaliu. Returnează doar textul problemei, fără comentarii suplimentare.\n"
        "Dacă există grafice sau diagrame, descrie-le clar și precis."
    )

    async with langfuse_trace_context(
        trace_id=trace_id,
        session_id=session_id,
        user_id=str(user_id) if user_id else None,
        name="solve_problem_ocr",
        tags=["solve_problem", "ocr"],
    ) as langfuse_config:
        try:
            log.info("Converting image bytes to PIL Image", user_id=user_id)
            image = Image.open(BytesIO(image_bytes))
            log.info(f"Image opened: size={image.size}, mode={image.mode}", user_id=user_id)

            log.info("Creating message with PIL Image", user_id=user_id)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    image,
                ]
            )

            log.info("Calling Gemini Vision API with PIL Image", user_id=user_id)
            response = await vision_llm.ainvoke([message], config=langfuse_config)
            log.info(
                f"OCR completed successfully, extracted {len(response.content)} characters",
                user_id=user_id,
            )
            return (response.content or "").strip()
        except Exception as e:
            log.warning(f"Failed with PIL Image, trying base64 fallback: {e!s}", user_id=user_id)
            try:
                log.info("Encoding image to base64", user_id=user_id)
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                log.info(f"Base64 encoded, length: {len(image_base64)}", user_id=user_id)
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"},
                    ]
                )
                log.info("Calling Gemini Vision API with base64", user_id=user_id)
                response = await vision_llm.ainvoke([message], config=langfuse_config)
                log.info(
                    f"OCR completed with base64 fallback, extracted {len(response.content)} characters",
                    user_id=user_id,
                )
                return (response.content or "").strip()
            except Exception as e2:
                log.error(f"Both methods failed. Base64 error: {e2!s}", user_id=user_id)
                raise HTTPException(status_code=500, detail=f"OCR failed: {str(e2)}") from e2

