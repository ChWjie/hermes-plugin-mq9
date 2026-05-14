"""Directory-plugin entrypoint shim for Hermes ecosystem installs.

This repository supports two installation styles:
1) pip entrypoint plugin (hermes_agent.plugins -> mq9)
2) directory plugin via `hermes plugins install owner/repo`

Directory mode loads this root __init__.py. We delegate to the real plugin
implementation in the `mq9` package.
"""

from __future__ import annotations

from .mq9 import register

__all__ = ["register"]
