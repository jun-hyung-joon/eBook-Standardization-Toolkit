#!/usr/bin/env python3
"""
Claude AI client 
"""

import os
import logging
from typing import Dict, Any, Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)

class APIValidationError(Exception):
    pass

class ClaudeClient:
    def __init__(self, api_key: str, model: str):
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package is required")
        
        if not api_key:
            raise APIValidationError("API key required")
            
        if not model:
            raise APIValidationError("Model name required")
        
        self.api_key = api_key
        self.model = model
        
        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            
            # Connection test (raise exception on failure to abort initialization)
            self._test_connection()
            
            # Note: removed successful initialization log (coordinator logs it)
            
        except Exception as e:
            raise APIValidationError(f"Claude initialization failed: {e}")
    
    def _test_connection(self) -> None:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}]
            )
            if not response or not response.content:
                raise Exception("No response")
        except Exception as e:
            raise APIValidationError(f"Connection test failed: {e}")
    
    def generate(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response or not response.content:
                raise Exception("No response")
            
            tokens = 0
            if response.usage:
                tokens = response.usage.input_tokens + response.usage.output_tokens
            
            return {
                'text': response.content[0].text,
                'tokens': tokens,
                'model': self.model,
                'provider': 'claude'
            }
        except Exception as e:
            # Logging should be handled by the caller or at debug level if needed
            # logger.error(f"Claude error: {e}") 
            raise e

