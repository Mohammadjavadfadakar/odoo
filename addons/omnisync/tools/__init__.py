"""Utility helpers for OmniSync."""

from __future__ import annotations

DEFAULT_QUEUE_CHANNEL = "root.omnisync"

try:  # pragma: no cover - exercised indirectly when queue_job is present.
    from odoo.addons.queue_job.mixins.queue_job import QueueJobMixin  # type: ignore
except ImportError as exc:  # pragma: no cover - raised during module loading.
    raise ImportError(
        "OmniSync requires the queue_job module for Odoo 18.0. "
        "Ensure the addon from https://github.com/OCA/queue/tree/18.0 is installed."
    ) from exc

__all__ = [
    "DEFAULT_QUEUE_CHANNEL",
    "QueueJobMixin",
]
