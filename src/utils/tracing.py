"""
Enhanced LangSmith Tracing for Multi-Agent Visualization
Provides proper parent-child relationships between agents
"""
import os
import logging
from typing import Optional, Any, Dict, Callable
from functools import wraps
from contextlib import contextmanager
import time
import uuid

logger = logging.getLogger(__name__)

# Check if langsmith is available
try:
    from langsmith import Client, traceable
    from langsmith.run_trees import RunTree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    traceable = lambda *args, **kwargs: lambda f: f  # no-op decorator


def get_langsmith_client() -> Optional[Any]:
    """Get LangSmith client if available and configured"""
    if not LANGSMITH_AVAILABLE:
        return None
    
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        return None
    
    try:
        return Client()
    except Exception as e:
        logger.warning(f"Failed to create LangSmith client: {e}")
        return None


class AgentTracer:
    """
    Enhanced tracer for multi-agent systems.
    Creates proper parent-child relationships in LangSmith.
    """
    
    def __init__(self, project_name: str = "tradl-hackathon"):
        self.project_name = project_name
        self.client = get_langsmith_client()
        self.enabled = self.client is not None
        self._current_run: Optional[RunTree] = None
    
    @contextmanager
    def trace_pipeline(self, name: str, metadata: Optional[Dict] = None):
        """
        Context manager for tracing an entire pipeline.
        Creates a parent run that contains all agent runs.
        """
        if not self.enabled:
            yield None
            return
        
        try:
            run_id = str(uuid.uuid4())
            self._current_run = RunTree(
                name=name,
                run_type="chain",
                project_name=self.project_name,
                id=run_id,
                inputs=metadata or {},
            )
            self._current_run.__enter__()
            yield self._current_run
        except Exception as e:
            logger.error(f"Tracing error: {e}")
            yield None
        finally:
            if self._current_run:
                try:
                    self._current_run.__exit__(None, None, None)
                except:
                    pass
                self._current_run = None
    
    @contextmanager
    def trace_agent(self, agent_name: str, inputs: Optional[Dict] = None):
        """
        Context manager for tracing an individual agent.
        Creates a child run under the current pipeline.
        """
        if not self.enabled or not self._current_run:
            yield None
            return
        
        start_time = time.time()
        child_run = None
        
        try:
            child_run = self._current_run.create_child(
                name=agent_name,
                run_type="chain",
                inputs=inputs or {},
            )
            child_run.__enter__()
            yield child_run
        except Exception as e:
            logger.error(f"Agent tracing error: {e}")
            yield None
        finally:
            if child_run:
                try:
                    duration_ms = (time.time() - start_time) * 1000
                    child_run.end(outputs={"duration_ms": duration_ms})
                    child_run.__exit__(None, None, None)
                except:
                    pass


def trace_agent(agent_name: str, run_type: str = "chain"):
    """
    Decorator to trace agent functions with proper naming.
    
    Usage:
        @trace_agent("NER Agent")
        async def extract_entities(content: str) -> dict:
            ...
    """
    def decorator(func: Callable):
        if not LANGSMITH_AVAILABLE:
            return func
        
        @wraps(func)
        @traceable(name=agent_name, run_type=run_type)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @wraps(func)
        @traceable(name=agent_name, run_type=run_type)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def trace_tool(tool_name: str):
    """
    Decorator to trace tool calls (LLM, vector search, etc.)
    
    Usage:
        @trace_tool("ChromaDB Search")
        def search_vectors(query: str) -> list:
            ...
    """
    def decorator(func: Callable):
        if not LANGSMITH_AVAILABLE:
            return func
        
        @wraps(func)
        @traceable(name=tool_name, run_type="tool")
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @wraps(func)
        @traceable(name=tool_name, run_type="tool")
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def trace_llm(model_name: str = "LLM"):
    """
    Decorator to trace LLM calls.
    
    Usage:
        @trace_llm("GPT-4o-mini")
        def generate_response(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable):
        if not LANGSMITH_AVAILABLE:
            return func
        
        @wraps(func)
        @traceable(name=model_name, run_type="llm")
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @wraps(func)
        @traceable(name=model_name, run_type="llm")
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Global tracer instance
_tracer: Optional[AgentTracer] = None


def get_tracer() -> AgentTracer:
    """Get or create global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = AgentTracer()
    return _tracer
