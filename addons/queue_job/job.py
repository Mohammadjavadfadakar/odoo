"""Provide a light-weight drop-in replacement for the OCA queue_job decorator."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


@overload
def job(func: F) -> F: ...


@overload
def job(*, channel: Optional[str] = None, **options: Any) -> Callable[[F], F]: ...


def job(func: Optional[F] = None, /, *, channel: Optional[str] = None, **options: Any):
    """Return a decorator marking a function as an async job.

    The real :mod:`queue_job` module adds a number of behaviours. Our stub keeps
    things deliberately small by storing the requested options on the wrapped
    function so that callers can introspect them if needed.
    """

    def decorator(wrapped: F) -> F:
        metadata: Dict[str, Any] = {"channel": channel} if channel else {}
        metadata.update(options)
        setattr(wrapped, "_queue_job_options", metadata)

        @wraps(wrapped)
        def wrapper(*args: Any, **kwargs: Any):
            return wrapped(*args, **kwargs)

        setattr(wrapper, "_queue_job_options", metadata)
        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


job_decorator = job

__all__ = ["job", "job_decorator"]
