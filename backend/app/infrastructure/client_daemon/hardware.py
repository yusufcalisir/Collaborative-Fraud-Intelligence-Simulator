"""Hardware Acceleration Detection for Local Bank PyTorch Training."""

from __future__ import annotations

import logging
import os
from typing import Any

import torch

logger = logging.getLogger(__name__)


def detect_hardware_acceleration() -> dict[str, Any]:
    """Detects available hardware accelerators (CUDA GPU, Apple Silicon MPS, or CPU fallback)

    for local PyTorch model training.
    """
    device_type = "cpu"
    device_name = "CPU"
    core_count = os.cpu_count() or 1
    is_accelerated = False

    if torch.cuda.is_available():
        device_type = "cuda"
        device_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "CUDA GPU"
        is_accelerated = True
        logger.info("Hardware acceleration detected: CUDA GPU (%s)", device_name)
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device_type = "mps"
        device_name = "Apple Silicon GPU (MPS)"
        is_accelerated = True
        logger.info("Hardware acceleration detected: Apple Silicon MPS")
    else:
        logger.info(
            "No GPU accelerator detected. Falling back to CPU training (%d threads)", core_count
        )

    return {
        "device_type": device_type,
        "device_name": device_name,
        "is_accelerated": is_accelerated,
        "core_count": core_count,
        "torch_version": torch.__version__,
    }
