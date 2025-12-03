"""
LLM Client - Unified interface for multiple LLM providers (Groq, OpenAI, Anthropic)
Groq provides fastest inference (~500 tokens/sec) for real-time trading applications
"""
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
import time

from src.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    
    Provider Comparison:
    - Groq (Llama 3.3 70B): ~50-100ms latency, 500+ tokens/sec
    - OpenAI (GPT-4o-mini): ~300-500ms latency, 80-100 tokens/sec  
    - Anthropic (Claude): ~400-600ms latency, similar throughput
    
    For real-time trading news, Groq is recommended.
    """
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.client = None
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client based on config"""
        
        if self.provider == "groq":
            self._init_groq()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "anthropic":
            self._init_anthropic()
        else:
            logger.warning(f"Unknown provider {self.provider}, falling back to groq")
            self._init_groq()
    
    def _init_groq(self):
        """Initialize Groq client (fastest inference)"""
        try:
            from groq import Groq
            
            if not settings.groq_api_key:
                logger.warning("GROQ_API_KEY not set - LLM features disabled")
                self.client = None
                return
            
            self.client = Groq(api_key=settings.groq_api_key)
            self.model = settings.groq_model
            self.provider = "groq"
            logger.info(f"Groq client initialized with model: {self.model}")
            
        except ImportError:
            logger.error("groq package not installed. Run: pip install groq")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            self.client = None
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            
            if not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY not set - falling back to groq")
                self._init_groq()
                return
            
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            self.provider = "openai"
            logger.info(f"OpenAI client initialized with model: {self.model}")
            
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            self._init_groq()
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self._init_groq()
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            
            if not settings.anthropic_api_key:
                logger.warning("ANTHROPIC_API_KEY not set - falling back to groq")
                self._init_groq()
                return
            
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            self.model = getattr(settings, 'anthropic_model', 'claude-3-haiku-20240307')
            self.provider = "anthropic"
            logger.info(f"Anthropic client initialized with model: {self.model}")
            
        except ImportError:
            logger.error("anthropic package not installed")
            self._init_groq()
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            self._init_groq()
    
    @property
    def is_available(self) -> bool:
        """Check if LLM client is available"""
        return self.client is not None
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Generate response from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Creativity (0-1)
            max_tokens: Max response length
            
        Returns:
            Generated text or None if failed
        """
        if not self.is_available:
            logger.warning("LLM client not available")
            return None
        
        start_time = time.time()
        
        try:
            if self.provider == "groq":
                response = self._generate_groq(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == "openai":
                response = self._generate_openai(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == "anthropic":
                response = self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
            else:
                return None
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"LLM response generated in {latency_ms:.0f}ms ({self.provider})")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
    
    def _generate_groq(self, prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int) -> str:
        """Generate with Groq"""
        if self.client is None:
            raise RuntimeError("Groq client not initialized")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content or ""
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int) -> str:
        """Generate with OpenAI"""
        if self.client is None:
            raise RuntimeError("OpenAI client not initialized")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content or ""
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int) -> str:
        """Generate with Anthropic"""
        if self.client is None:
            raise RuntimeError("Anthropic client not initialized")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
