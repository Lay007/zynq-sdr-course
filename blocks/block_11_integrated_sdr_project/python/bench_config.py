"""Shared environment-backed defaults for the local ZynqSDR bench."""

from __future__ import annotations

import os


DEFAULT_HOST = os.environ.get("ZYNQ_SSH_HOST", "192.168.40.1")
DEFAULT_USER = os.environ.get("ZYNQ_SSH_USER", "root")
DEFAULT_PASSWORD = os.environ.get("ZYNQ_SSH_PASSWORD", "analog")
DEFAULT_PORT = int(os.environ.get("ZYNQ_SSH_PORT", "22"))
DEFAULT_TIMEOUT_S = float(os.environ.get("ZYNQ_SSH_TIMEOUT_S", "10.0"))
DEFAULT_IIO_URI = os.environ.get("ZYNQ_IIO_URI", f"ip:{DEFAULT_HOST}")

# Second board, for two-board labs (independent reference oscillator -> real CFO).
# Board B runs the same stock ADI/Pluto image as board A (root/analog), on its own subnet so
# both boards can share one switch without an address clash; a small init add-on pins its
# eth0 to a fixed IP/MAC across reboots (see the bench README on its SD card).
DEFAULT_HOST_B = os.environ.get("ZYNQ_SSH_HOST_B", "192.168.20.1")
DEFAULT_USER_B = os.environ.get("ZYNQ_SSH_USER_B", "root")
DEFAULT_PASSWORD_B = os.environ.get("ZYNQ_SSH_PASSWORD_B", "analog")
