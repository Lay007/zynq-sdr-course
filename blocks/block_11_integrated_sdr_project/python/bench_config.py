"""Shared environment-backed defaults for the local ZynqSDR bench."""

from __future__ import annotations

import os


DEFAULT_HOST = os.environ.get("ZYNQ_SSH_HOST", "192.168.40.1")
DEFAULT_USER = os.environ.get("ZYNQ_SSH_USER", "root")
DEFAULT_PASSWORD = os.environ.get("ZYNQ_SSH_PASSWORD", "analog")
DEFAULT_PORT = int(os.environ.get("ZYNQ_SSH_PORT", "22"))
DEFAULT_TIMEOUT_S = float(os.environ.get("ZYNQ_SSH_TIMEOUT_S", "10.0"))
DEFAULT_IIO_URI = os.environ.get("ZYNQ_IIO_URI", f"ip:{DEFAULT_HOST}")
