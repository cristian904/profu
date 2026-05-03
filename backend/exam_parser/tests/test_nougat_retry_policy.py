"""Unit tests for Nougat CUDA->CPU retry policy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from exam_parser.parsers.nougat_local_gpu import (
    _should_retry_pdf_on_cpu_after_cuda_failure,
    clear_nougat_cache_for_tests,
    write_markdown_local_gpu,
)


def test_retry_policy_allows_auto_when_auto_resolves_to_cuda() -> None:
    """Retry should be enabled when NOUGAT_DEVICE=auto resolves to CUDA."""
    retryable_exc = RuntimeError("CUDA error: device-side assert triggered")
    with patch(
        "exam_parser.parsers.nougat_local_gpu.resolve_nougat_device",
        return_value="cuda",
    ):
        assert _should_retry_pdf_on_cpu_after_cuda_failure("auto", retryable_exc) is True


def test_retry_policy_blocks_cpu_when_auto_resolves_to_cpu() -> None:
    """Retry should not run when NOUGAT_DEVICE=auto resolves to CPU."""
    retryable_exc = RuntimeError("CUDA error: device-side assert triggered")
    with patch(
        "exam_parser.parsers.nougat_local_gpu.resolve_nougat_device",
        return_value="cpu",
    ):
        assert _should_retry_pdf_on_cpu_after_cuda_failure("auto", retryable_exc) is False


def test_retry_policy_blocks_non_retryable_cuda_errors() -> None:
    """Retry should stay disabled for unknown/non-retryable failures."""
    non_retryable_exc = RuntimeError("CUDA out of memory")
    with patch(
        "exam_parser.parsers.nougat_local_gpu.resolve_nougat_device",
        return_value="cuda",
    ):
        assert _should_retry_pdf_on_cpu_after_cuda_failure("auto", non_retryable_exc) is False


def test_write_markdown_resets_gpu_cache_before_cpu_retry(tmp_path: Path) -> None:
    """Retryable CUDA failures should release GPU cache before CPU fallback."""
    pdf_path = tmp_path / "sample.pdf"
    md_out = tmp_path / "sample.md"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    calls: list[str] = []

    def _fake_pdf_to_markdown_local(
        _pdf_path: Path,
        *,
        model_id: str,
        device_setting: str,
        feature_logger: object | None = None,
    ) -> str:
        calls.append(device_setting)
        if device_setting == "auto":
            raise RuntimeError("CUDA error: device-side assert triggered")
        return f"ok:{model_id}:{device_setting}"

    with patch(
        "exam_parser.parsers.nougat_local_gpu.resolve_nougat_device",
        return_value="cuda",
    ), patch(
        "exam_parser.parsers.nougat_local_gpu.pdf_to_markdown_local",
        side_effect=_fake_pdf_to_markdown_local,
    ), patch(
        "exam_parser.parsers.nougat_local_gpu.release_nougat_gpu_resources"
    ) as mock_release:
        write_markdown_local_gpu(
            pdf_path,
            md_out,
            model_id="facebook/nougat-base",
            device_setting="auto",
            feature_logger=None,
        )

    assert calls == ["auto", "cpu"]
    assert mock_release.call_count == 2
    assert md_out.read_text(encoding="utf-8") == "ok:facebook/nougat-base:cpu"


def test_clear_nougat_cache_for_tests_is_safe() -> None:
    """Cache clear helper should be callable repeatedly without errors."""
    clear_nougat_cache_for_tests()
    clear_nougat_cache_for_tests()
