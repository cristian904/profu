"""
Run ``facebook/nougat-base`` locally for PDF → markdown (GPU via CUDA or Apple MPS when available).
"""
from __future__ import annotations

import atexit
import gc
import threading
import traceback
from pathlib import Path
from typing import Any, Callable

import fitz
import torch
from PIL import Image
from transformers import AutoProcessor, VisionEncoderDecoderModel

# Lazy singleton: one processor+model pair per (model_id, device) for the process.
_lock = threading.Lock()
_cached: dict[str, tuple[Any, Any]] = {}


def resolve_nougat_device(device_setting: str) -> str:
    """
    Map user setting to a PyTorch device string.

    Args:
        device_setting: ``auto``, ``cuda``, ``cuda:N``, ``mps``, or ``cpu``.

    Returns:
        Device string for ``tensor.to(device)``.

    Raises:
        RuntimeError: If a GPU-only choice was requested but that backend is unavailable.
        ValueError: If *device_setting* is not recognized.
    """
    s = (device_setting or "auto").strip().lower()
    if s == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if s == "cpu":
        return "cpu"
    if s == "mps":
        if getattr(torch.backends, "mps", None) is None or not torch.backends.mps.is_available():
            raise RuntimeError(
                "NOUGAT_DEVICE=mps but MPS is not available. Use NOUGAT_DEVICE=auto or cpu, "
                "or run on Apple Silicon with a PyTorch build that supports MPS."
            )
        return "mps"
    if s == "cuda" or s.startswith("cuda:"):
        if not torch.cuda.is_available():
            # Provide detailed diagnostics to make CUDA visibility issues debuggable in UI logs.
            cuda_visible = __import__("os").environ.get("CUDA_VISIBLE_DEVICES", "<unset>")
            raise RuntimeError(
                "NOUGAT_DEVICE requests CUDA but CUDA is not available. "
                "Install a CUDA-enabled PyTorch build, or set NOUGAT_DEVICE=auto|mps|cpu. "
                f"Runtime: torch={torch.__version__}, torch.version.cuda={torch.version.cuda}, "
                f"cuda_available={torch.cuda.is_available()}, CUDA_VISIBLE_DEVICES={cuda_visible}."
            )
        return "cuda" if s == "cuda" else s
    raise ValueError(f"Unknown NOUGAT_DEVICE value: {device_setting!r}")


def _pdf_to_images(pdf_path: Path) -> list[Image.Image]:
    """Rasterize each PDF page to RGB for Nougat."""
    doc = fitz.open(str(pdf_path))
    images: list[Image.Image] = []
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images


def _nougat_preprocess_bools(image_processor: Any) -> dict[str, bool]:
    """
    NougatProcessor forwards ``None`` for optional image kwargs; newer ``huggingface_hub`` strict
    validation rejects ``None`` for bool fields. Use explicit booleans from the loaded processor.
    """
    def _bool_attr(name: str, default: bool) -> bool:
        value = getattr(image_processor, name, None)
        return default if value is None else bool(value)

    return {
        "do_crop_margin": _bool_attr("do_crop_margin", True),
        "do_thumbnail": _bool_attr("do_thumbnail", True),
        "do_align_long_axis": _bool_attr("do_align_long_axis", False),
    }


def _get_processor_and_model(model_id: str, device: str, log: Any) -> tuple[Any, Any]:
    """Load or return cached Nougat processor and model (thread-safe)."""
    cache_key = f"{model_id}|{device}"
    with _lock:
        if cache_key not in _cached:
            log(f"[nougat_local] Loading {model_id} on {device} (first use may download weights)...")
            processor = AutoProcessor.from_pretrained(model_id)
            model = VisionEncoderDecoderModel.from_pretrained(model_id)
            model.to(device)
            model.eval()
            _cached[cache_key] = (processor, model)
        return _cached[cache_key]


def _is_retryable_cuda_nougat_error(exc: Exception) -> bool:
    """
    Return True for known CUDA runtime failures where retrying on CPU is safer.

    This currently targets PyTorch CUDA indexing assertions observed during
    ``model.generate(...)`` with Nougat on some driver/runtime combinations.
    """
    msg = str(exc)
    lowered = msg.lower()
    return (
        "indexselectsmallindex" in lowered
        or "srcindex < srcselectdimsize" in lowered
        or "device-side assert triggered" in lowered
        or ("cuda" in lowered and "assert" in lowered)
    )


def _should_retry_pdf_on_cpu_after_cuda_failure(device_setting: str, exc: Exception) -> bool:
    """
    Return True when this PDF run should retry on CPU after a CUDA runtime failure.

    The retry policy is intentionally conservative:
    - only for known retryable CUDA runtime assertions;
    - only when the configured/resolved device for the run is CUDA.
    """
    if not _is_retryable_cuda_nougat_error(exc):
        return False

    try:
        resolved_device = resolve_nougat_device(device_setting)
    except Exception:
        # Keep behavior safe if resolution itself fails for any reason.
        return False

    return resolved_device.startswith("cuda")


def _safe_release_nougat_resources(feature_logger: Any | None = None) -> None:
    """
    Release cached Nougat resources and log failures without raising.

    Args:
        feature_logger: Optional feature logger used by pipeline steps.
    """
    try:
        release_nougat_gpu_resources(
            log=feature_logger.info if feature_logger is not None else print
        )
    except Exception as release_exc:
        if feature_logger is not None:
            feature_logger.error(release_exc, traceback=traceback.format_exc())


def _write_text_atomically(path: Path, text: str) -> None:
    """
    Atomically write text to destination path via temporary sibling file.

    Args:
        path: Final markdown output path.
        text: Markdown body to persist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def pdf_to_markdown_local(
    pdf_path: Path,
    *,
    model_id: str,
    device_setting: str,
    feature_logger: Any | None = None,
) -> str:
    """
    Convert a PDF file to markdown using local Nougat inference.

    Args:
        pdf_path: Path to the PDF.
        model_id: Hugging Face model id (default ``facebook/nougat-base``).
        device_setting: ``auto``, ``cuda``, ``mps``, or ``cpu``.
        feature_logger: Optional ``FeatureLogger`` for progress lines.

    Returns:
        Concatenated markdown text (pages separated by blank lines).

    Raises:
        FileNotFoundError: If *pdf_path* is missing.
        RuntimeError: On invalid device or model errors.
    """
    log = feature_logger.info if feature_logger is not None else print

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    device = resolve_nougat_device(device_setting)
    if device == "cpu":
        log(
            "[nougat_local] WARNING: Using CPU — extraction will be slow. "
            "Prefer a CUDA or MPS GPU (NOUGAT_DEVICE=auto)."
        )
    else:
        log(f"[nougat_local] Using device={device}")

    processor, model = _get_processor_and_model(model_id, device, log)

    page_texts: list[str] = []
    images = _pdf_to_images(pdf_path)
    ip = processor.image_processor
    preprocess_kw = _nougat_preprocess_bools(ip)

    for idx, img in enumerate(images):
        log(f"[nougat_local] Page {idx + 1}/{len(images)} — {pdf_path.name}")
        # Call image_processor directly so optional args are not passed as ``None`` (HF hub strict typing).
        inputs = ip([img], return_tensors="pt", **preprocess_kw)
        pixel_values = inputs.pixel_values.to(device)
        with torch.no_grad():
            generated_ids = model.generate(
                pixel_values,
                min_length=1,
                max_new_tokens=4096,
            )
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        page_texts.append(text)

    return "\n\n".join(page_texts)


def write_markdown_local_gpu(
    pdf_path: Path,
    md_out: Path,
    *,
    model_id: str,
    device_setting: str,
    feature_logger: Any | None = None,
) -> None:
    """
    Run :func:`pdf_to_markdown_local` and atomically write *md_out*.

    Args:
        pdf_path: Source PDF.
        md_out: Destination ``.md`` path.
        model_id: Nougat model id on the Hub.
        device_setting: PyTorch device selection string.
        feature_logger: Optional logger.

    Raises:
        Exception: Logs traceback via *feature_logger* when present, then re-raises.
    """
    should_unload_after_cpu_fallback = False
    try:
        md_text = pdf_to_markdown_local(
            pdf_path,
            model_id=model_id,
            device_setting=device_setting,
            feature_logger=feature_logger,
        )
    except Exception as exc:
        # If CUDA generation fails with a known runtime assertion, retry on CPU
        # so the run can continue and produce output for the current PDF.
        if _should_retry_pdf_on_cpu_after_cuda_failure(device_setting, exc):
            if feature_logger is not None:
                feature_logger.warning(
                    "[nougat_local] CUDA runtime assertion detected; retrying this PDF on CPU. "
                    "Consider updating/downgrading PyTorch+CUDA if this repeats."
                )
                feature_logger.warning(
                    f"[nougat_local] Recoverable CUDA error details: {exc}"
                )
                feature_logger.warning(
                    "[nougat_local] Resetting cached Nougat GPU resources before CPU retry "
                    "to allow clean CUDA re-initialization on subsequent PDFs."
                )
            _safe_release_nougat_resources(feature_logger)
            try:
                md_text = pdf_to_markdown_local(
                    pdf_path,
                    model_id=model_id,
                    device_setting="cpu",
                    feature_logger=feature_logger,
                )
                should_unload_after_cpu_fallback = True
            except Exception as retry_exc:
                if feature_logger is not None:
                    feature_logger.error(retry_exc, traceback=traceback.format_exc())
                raise
        else:
            if feature_logger is not None:
                feature_logger.error(exc, traceback=traceback.format_exc())
            raise

    _write_text_atomically(md_out, md_text)
    if should_unload_after_cpu_fallback:
        # Do not keep CPU fallback model resident between PDFs.
        # This forces a clean model reload on the next file.
        _safe_release_nougat_resources(feature_logger)
        if feature_logger is not None:
            feature_logger.info(
                "[nougat_local] CPU fallback model unloaded after PDF completion; "
                "Nougat will reload for the next PDF."
            )


def release_nougat_gpu_resources(log: Callable[[str], None] | None = None) -> None:
    """
    Drop cached processor/model pairs and ask PyTorch to return GPU memory to the driver.

    Safe to call when the cache is empty. Use after extract steps or on process shutdown.
    ``kill -9`` cannot run this handler.

    Args:
        log: Optional callback for progress (e.g. ``logger.info``); falls back to ``print``.
    """
    emit: Callable[[str], None] = log if log is not None else print

    had_entries = False
    with _lock:
        had_entries = bool(_cached)
        for _key, (processor, model) in list(_cached.items()):
            try:
                if model is not None:
                    del model
            except Exception as exc:
                emit(f"[nougat_local] Error while releasing model from cache: {exc}")
            try:
                if processor is not None:
                    del processor
            except Exception as exc:
                emit(f"[nougat_local] Error while releasing processor from cache: {exc}")
        _cached.clear()

    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception as exc:
        # Device-side asserts poison CUDA context; cleanup may fail until restart.
        msg = str(exc).lower()
        if "device-side assert triggered" in msg:
            emit(
                "[nougat_local] CUDA cache clear skipped due to poisoned CUDA context "
                "(device-side assert). Restart process to fully reset CUDA state."
            )
        else:
            emit(f"[nougat_local] CUDA cache clear failed: {exc}")
    try:
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception as exc:
        emit(f"[nougat_local] MPS cache clear failed: {exc}")

    if had_entries:
        emit("[nougat_local] Released Nougat GPU cache and requested driver memory reclaim")


def clear_nougat_cache_for_tests() -> None:
    """Drop cached models and free GPU memory (pytest / dev), without console noise."""
    release_nougat_gpu_resources(log=lambda _msg: None)


def _atexit_release_nougat_gpu() -> None:
    """Best-effort VRAM cleanup when the interpreter exits (normal exit, uncaught error paths)."""
    try:
        release_nougat_gpu_resources(log=print)
    except Exception as exc:
        print(f"[nougat_local] atexit GPU release failed: {exc}")


atexit.register(_atexit_release_nougat_gpu)
