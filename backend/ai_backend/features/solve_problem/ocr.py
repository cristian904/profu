"""
OCR helpers for solve-problem.

Uses Gemini Vision via LangChain to extract problem text from uploaded images.
"""

import base64
from io import BytesIO

from fastapi import HTTPException

from ai_backend.config import settings
from profu_logging.feature_logger import get_feature_logger


async def perform_ocr(image_bytes: bytes) -> str:
    """
    Use Gemini Vision API to extract text from an image.

    Args:
        image_bytes: Raw uploaded image bytes.

    Returns:
        Extracted problem text.

    Raises:
        HTTPException: When OCR fails or configuration is missing.
    """
    log = get_feature_logger(source="ocr")
    log.info(f"Starting OCR for image of {len(image_bytes)} bytes", user_id=None)

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI
    from PIL import Image

    if not settings.google_api_key:
        log.error("GOOGLE_API_KEY not found in environment", user_id=None, traceback=None)
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    log.info("Initializing Gemini Vision model", user_id=None)
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

    try:
        log.info("Converting image bytes to PIL Image", user_id=None)
        image = Image.open(BytesIO(image_bytes))
        log.info(f"Image opened: size={image.size}, mode={image.mode}", user_id=None)

        log.info("Creating message with PIL Image", user_id=None)
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                image,
            ]
        )

        log.info("Calling Gemini Vision API with PIL Image", user_id=None)
        response = await vision_llm.ainvoke([message])
        log.info(
            f"OCR completed successfully, extracted {len(response.content)} characters",
            user_id=None,
        )
        return (response.content or "").strip()
    except Exception as e:
        log.warning(f"Failed with PIL Image, trying base64 fallback: {e!s}", user_id=None)
        try:
            log.info("Encoding image to base64", user_id=None)
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            log.info(f"Base64 encoded, length: {len(image_base64)}", user_id=None)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"},
                ]
            )
            log.info("Calling Gemini Vision API with base64", user_id=None)
            response = await vision_llm.ainvoke([message])
            log.info(
                f"OCR completed with base64 fallback, extracted {len(response.content)} characters",
                user_id=None,
            )
            return (response.content or "").strip()
        except Exception as e2:
            log.error(f"Both methods failed. Base64 error: {e2!s}", user_id=None)
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e2)}") from e2

