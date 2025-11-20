#!/usr/bin/env python3
"""
Gemini AI client 
"""

import os
import logging
from typing import Dict, Any

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

logger = logging.getLogger(__name__)

class APIValidationError(Exception):
    pass

class GeminiClient:
    def __init__(self, api_key: str, model: str):
        if not HAS_GEMINI:
            raise ImportError("google-generativeai package is required")
        if not api_key:
            raise APIValidationError("API key required")
        
        # Use default model if none specified
        if not model:
            logger.warning("Model not specified -> using 'gemini-1.5-flash'")
            model = "gemini-1.5-flash"
        
        self.api_key = api_key
        self.model = model
        
        if "pro" in self.model:
            logger.info(f"ℹ️ Using '{self.model}'. If blocked, consider 'gemini-1.5-flash'.")
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # NOTE: Do not log initialization completion here to avoid duplicate logs with the coordinator
            # self._test_connection()  # Optional connection test (can be skipped for speed)
            
        except Exception as e:
            raise APIValidationError(f"Gemini initialization failed: {e}")
    
    def _test_connection(self) -> None:
        try:
            self.client.generate_content("Hi", safety_settings=self.safety_settings)
        except Exception as e:
            raise e
    
    def generate(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        try:
            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.1,
                top_p=0.9,
                top_k=40
            )
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            if not response:
                raise Exception("No response")

            try:
                text = response.text
            except ValueError:
                if response.parts:
                    logger.warning("⚠️ Partially blocked; using partial response.")
                    text = response.parts[0].text
                else:
                    feedback = getattr(response, 'prompt_feedback', 'N/A')
                    msg = f"⛔ Gemini({self.model}) blocked (Feedback: {feedback})"
                    logger.error(msg)
                    raise Exception(msg)

            tokens = 0
            if hasattr(response, 'usage_metadata'):
                tokens = response.usage_metadata.total_token_count
            
            return {
                'text': text,
                'tokens': tokens,
                'model': self.model,
                'provider': 'gemini'
            }
            
        except Exception as e:
            raise e