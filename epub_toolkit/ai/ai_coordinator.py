#!/usr/bin/env python3
"""
AI Coordinator - Configuration-based management (ImportError fix and restored functions)

Features:
- Create and manage AI clients
- Load model and token settings from configuration
- Provide factory function (get_ai_coordinator) and utility helpers
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import config_manager from parent package; adjust path if package import fails
try:
    from epub_toolkit.config_manager import config_manager
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from epub_toolkit.config_manager import config_manager

logger = logging.getLogger(__name__)

class APIKeyRequiredError(Exception):
    pass

class APIValidationError(Exception):
    pass

@dataclass
class AIResult:
    success: bool
    content: str
    model_used: str
    provider: str
    tokens_used: int
    processing_time: float
    changes_made: List[str]
    error_message: Optional[str] = None

class SimpleAICoordinator:
    """Unified AI manager"""
    
    api_key_mappings = {
        'claude': 'ANTHROPIC_API_KEY',
        'gpt': 'OPENAI_API_KEY', 
        'gemini': 'GOOGLE_API_KEY',
        'grok': 'XAI_API_KEY'
    }

    def __init__(self, selected_ai: Optional[str] = None):
        self.selected_ai = selected_ai or 'claude'
        self.client = None
        self.default_max_tokens = 4000
        self._initialize()
        
    def _initialize(self) -> None:
        env_var = self.api_key_mappings.get(self.selected_ai)
        if not env_var:
            raise APIKeyRequiredError(f"Unsupported AI provider: {self.selected_ai}")
            
        api_key = os.getenv(env_var)
        if not api_key or len(api_key.strip()) < 10:
            raise APIKeyRequiredError(f"The environment variable {env_var} is not properly set.")
            
        # Read max_tokens from config if present
        config_tokens = config_manager.get(f"models.{self.selected_ai}.max_tokens")
        if config_tokens:
            self.default_max_tokens = int(config_tokens)
            
        self.client = self._create_client(api_key.strip())
        logger.info(f"{self.selected_ai} initialized (Max Tokens: {self.default_max_tokens})")
    
    def _create_client(self, api_key: str):
        """Client factory"""
        model_name = config_manager.get(f"models.{self.selected_ai}.default")
        
        # Fallback logic
        if not model_name:
            if self.selected_ai == 'claude': model_name = "claude-3-5-sonnet-20240620"
            elif self.selected_ai == 'gpt': model_name = "gpt-4o"
            elif self.selected_ai == 'gemini': model_name = "gemini-1.5-flash"
            elif self.selected_ai == 'grok': model_name = "grok-2"
            
        try:
            if self.selected_ai == 'claude':
                from .claude_client import ClaudeClient
                return ClaudeClient(api_key, model=model_name)
            elif self.selected_ai == 'gpt':
                from .gpt_client import GPTClient
                return GPTClient(api_key, model=model_name)
            elif self.selected_ai == 'gemini':
                from .gemini_client import GeminiClient
                return GeminiClient(api_key, model=model_name)
            elif self.selected_ai == 'grok':
                from .grok_client import GrokClient
                return GrokClient(api_key, model=model_name)
            else:
                raise APIKeyRequiredError(f"Unsupported AI provider: {self.selected_ai}")
        except Exception as e:
            raise APIValidationError(f"Failed to initialize {self.selected_ai}: {e}")
    
    def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> AIResult:
        """Request content generation"""
        if not self.client:
            return AIResult(False, prompt, self.selected_ai, self.selected_ai, 0, 0.0, [], "AI initialization failed")
        
        # Use config value if max_tokens not provided
        effective_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        start_time = time.time()
        try:
            result = self.client.generate(prompt, effective_tokens)
            
            return AIResult(
                True, result['text'], 
                result.get('model', self.selected_ai), 
                self.selected_ai, 
                result.get('tokens', 0), 
                time.time() - start_time, 
                ["AI content generated"]
            )
        except Exception as e:
            return AIResult(False, prompt, self.selected_ai, self.selected_ai, 0, time.time() - start_time, [], str(e))

    def improve_content_with_ai(self, html_content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """(Legacy compatibility) Improve HTML using AI"""
        result = self.generate_content(f"Improve HTML:\n\n{html_content}")
        return {
            'improved_html': result.content if result.success else html_content, 
            'success': result.success, 
            'error_message': result.error_message
        }
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def get_available_models(self) -> List[str]:
        return [self.selected_ai] if self.client else []
    
    def test_connection(self, verbose: bool = False) -> Dict[str, Any]:
        """Test the currently configured AI connection"""
        results = {}
        # Test only the currently selected AI (by design)
        if self.client:
             try:
                 res = self.client.generate("Hi", 10)
                 results[self.selected_ai] = {'success': True, 'model': res.get('model')}
             except Exception as e:
                 results[self.selected_ai] = {'success': False, 'error': str(e)}
        return results

# =============================================================================
# Convenience functions (required by external modules)
# =============================================================================

_ai_coordinator_instance = None

def get_ai_coordinator(selected_ai: Optional[str] = None) -> SimpleAICoordinator:
    """Return singleton AI coordinator instance (required function)"""
    global _ai_coordinator_instance
    # Create a new instance if none exists or if requested AI differs from existing instance
    if _ai_coordinator_instance is None or (selected_ai and selected_ai != _ai_coordinator_instance.selected_ai):
        _ai_coordinator_instance = SimpleAICoordinator(selected_ai)
    return _ai_coordinator_instance

def test_all_ai_connections(verbose: bool = True) -> Dict[str, Any]:
    """Test connections for all AI providers (used by main.py)"""
    results = {}
    api_map = SimpleAICoordinator.api_key_mappings
    
    if verbose:
        print("🧪 Testing AI connections...")
    
    for provider, env_var in api_map.items():
        api_key = os.getenv(env_var)
        if not api_key:
            results[provider] = {'success': False, 'error': 'API Key Missing', 'available': False}
            if verbose: print(f"   ❌ {provider}: API Key missing")
            continue
            
        try:
            # Test with a temporary coordinator
            coord = SimpleAICoordinator(provider)
            res = coord.generate_content("Hi", max_tokens=5)
            if res.success:
                results[provider] = {'success': True, 'model': res.model_used, 'available': True}
                if verbose: print(f"   ✅ {provider}: connection successful ({res.model_used})")
            else:
                results[provider] = {'success': False, 'error': res.error_message, 'available': False}
                if verbose: print(f"   ❌ {provider}: failed - {res.error_message}")
        except Exception as e:
            results[provider] = {'success': False, 'error': str(e), 'available': False}
            if verbose: print(f"   ❌ {provider}: error - {e}")
            
    return results

def check_ai_availability() -> bool:
    """Check whether AI is available"""
    try:
        coordinator = get_ai_coordinator()
        return coordinator.is_available()
    except Exception:
        return False

def get_available_ai_providers() -> List[str]:
    """List available AI providers"""
    available = []
    for provider, env_var in SimpleAICoordinator.api_key_mappings.items():
        if os.getenv(env_var):
            available.append(provider)
    return available