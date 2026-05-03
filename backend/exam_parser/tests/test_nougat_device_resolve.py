"""Unit tests for Nougat device resolution (no model download)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from exam_parser.parsers.nougat_local_gpu import resolve_nougat_device


def test_resolve_auto_prefers_cuda_when_available() -> None:
    """When CUDA is available, auto should return cuda."""
    with patch("exam_parser.parsers.nougat_local_gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = False
        assert resolve_nougat_device("auto") == "cuda"


def test_resolve_auto_falls_back_to_cpu() -> None:
    """When neither CUDA nor MPS, auto returns cpu."""
    with patch("exam_parser.parsers.nougat_local_gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_mps = MagicMock()
        mock_mps.is_available.return_value = False
        mock_torch.backends.mps = mock_mps
        assert resolve_nougat_device("auto") == "cpu"


def test_resolve_cuda_raises_when_unavailable() -> None:
    """Explicit cuda should fail if CUDA is not available."""
    with patch("exam_parser.parsers.nougat_local_gpu.torch") as mock_torch:
        mock_torch.cuda.is_available.return_value = False
        mock_torch.__version__ = "test"
        mock_torch.version.cuda = None
        with pytest.raises(RuntimeError, match="CUDA"):
            resolve_nougat_device("cuda")


def test_resolve_cpu_always() -> None:
    """cpu should not require GPU."""
    assert resolve_nougat_device("cpu") == "cpu"
