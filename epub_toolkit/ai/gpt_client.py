#!/usr/bin/env python3
"""
GPT AI client
"""

import os
import logging
from typing import Dict, Any

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)

class APIValidationError(Exception):
    pass

class GPTClient:
    def __init__(self, api_key: str, model: str):
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        if not api_key:
            raise APIValidationError("API key required")
            
        if not model:
            raise APIValidationError("Model name required")
        
        self.api_key = api_key
        self.model = model
        
        try:
            self.client = openai.OpenAI(api_key=self.api_key)
            self._test_connection()
            
            # Note: initialization success log removed to avoid duplicate logging
            
        except Exception as e:
            raise APIValidationError(f"GPT initialization failed: {e}")
    
    def _test_connection(self) -> None:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}]
            )
            if not response or not response.choices:
                raise Exception("No response")
        except Exception as e:
            raise APIValidationError(f"Connection test failed: {e}")
    
    def generate(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response or not response.choices:
                raise Exception("No response")
            
            tokens = response.usage.total_tokens if getattr(response, "usage", None) else 0
            
            return {
                'text': (response.choices[0].message.content if response.choices and getattr(response.choices[0], "message", None) else "") or "",
                'tokens': tokens,
                'model': self.model,
                'provider': 'gpt'
            }
        except Exception as e:
            raise e

