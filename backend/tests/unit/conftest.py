"""Shared fixtures for unit tests: block outbound network via pytest-socket."""

from __future__ import annotations

import pytest
from pytest_socket import socket_allow_hosts


@pytest.fixture(autouse=True)
def block_network() -> None:
    """Block outbound connections except loopback (asyncio's self-pipe on Windows)."""
    socket_allow_hosts(allowed=["127.0.0.1", "::1"])
    yield
