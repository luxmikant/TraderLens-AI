"""LangSmith tracing utilities."""
from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv

# Ensure .env is loaded before reading env vars
load_dotenv()

logger = logging.getLogger(__name__)


def enable_langsmith(project_name: Optional[str] = None) -> bool:
    """Enable LangSmith tracing if environment variables are available."""
    try:
        from langsmith import Client  # lazy import so package is optional
    except ImportError:
        logger.warning("LangSmith client not installed; skipping tracing setup")
        return False

    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        logger.info("LANGCHAIN_API_KEY not provided; LangSmith disabled")
        return False

    project = project_name or os.getenv("LANGCHAIN_PROJECT", "tradl-hackathon")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
    os.environ.setdefault("LANGCHAIN_PROJECT", project)

    try:
        Client()  # smoke-test credentials
        logger.info("LangSmith tracing enabled for project '%s'", project)
        return True
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Unable to initialize LangSmith tracing: %s", exc)
        return False