"""
QuantX - Tracing Setup
Langfuse observability for every agent call.
Falls back to a no-op tracer if Langfuse is not configured.
"""

import os
import time
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))


class NoOpTracer:
    """No-op tracer when Langfuse is not configured."""

    def trace(self, *args, **kwargs):
        return self

    def span(self, *args, **kwargs):
        return self

    def generation(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def end(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def get_tracer():
    """Return a Langfuse tracer or a no-op fallback."""
    if not LANGFUSE_ENABLED:
        return NoOpTracer()

    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except ImportError:
        logger.warning("Langfuse not installed. Run: pip install langfuse")
        return NoOpTracer()


tracer = get_tracer()


@contextmanager
def trace_agent(agent_name: str, input_data: Optional[dict] = None):
    """Context manager to trace a single agent execution."""
    start = time.time()
    trace = None
    try:
        if LANGFUSE_ENABLED and not isinstance(tracer, NoOpTracer):
            trace = tracer.trace(name=f"quantx.{agent_name}", input=input_data or {})
        yield trace
    except Exception as e:
        if trace:
            try:
                trace.update(output={"error": str(e)}, level="ERROR")
            except Exception:
                pass
        raise
    finally:
        duration = time.time() - start
        logger.info(f"[{agent_name}] completed in {duration:.2f}s")
        if trace:
            try:
                trace.update(metadata={"duration_seconds": duration})
            except Exception:
                pass
