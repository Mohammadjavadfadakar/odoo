"""Compatibility helpers for the OCA queue job decorator.

This module looks up the :func:`job` decorator introduced by the OCA
``queue_job`` addon.  The module layout changed between the 16.0 and 18.0
series, so we attempt multiple import locations before failing with a clear
message for administrators.
"""

from importlib import import_module
from typing import Callable, Iterable, Tuple

JobDecorator = Callable[..., Callable]


def _candidate_paths() -> Iterable[Tuple[str, str]]:
    """Yield possible module paths and attribute names for the job decorator."""

    return (
        ("odoo.addons.queue_job", "job"),
        ("odoo.addons.queue_job.job", "job"),
        ("odoo.addons.queue_job.services.job", "job"),
        ("odoo.addons.queue_job.job", "job_decorator"),
    )


def _load_job_decorator() -> JobDecorator:
    """Import the queue job decorator from supported module locations."""

    errors = []
    for module_path, attr_name in _candidate_paths():
        try:
            module = import_module(module_path)
            decorator = getattr(module, attr_name)
        except ModuleNotFoundError as exc:
            errors.append(f"{module_path}: {exc}")
            continue
        except AttributeError as exc:
            errors.append(f"{module_path}.{attr_name}: {exc}")
            continue
        if callable(decorator):
            return decorator  # type: ignore[return-value]
    raise ImportError(
        "The OCA queue_job addon could not be located using the expected "
        "module paths. Ensure that the 18.0 version of queue_job is "
        "installed and reachable. Checked paths: %s. Errors: %s"
        % (
            ", ".join(module for module, _ in _candidate_paths()),
            "; ".join(errors),
        )
    )


queue_job: JobDecorator = _load_job_decorator()
