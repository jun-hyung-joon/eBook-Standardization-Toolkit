"""
Intelligent EPUB accessibility fixer powered by AI 
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
        return prompt

    def _get_hints(self, errors):
        """Search hints for error codes (direct match)"""
        hints = ""
        codes = set(e.error_code for e in errors)
        
        for code in codes:
            if code in self.hints:
                hints += f"- {code}: {self.hints[code]['hint']}\n"
        return hints

    def get_target_override(self, error_code: str) -> Optional[str]:
        """Return target file override info defined in JSON (direct match)"""
        return self.target_overrides.get(error_code)

    def _detect_file_type(self, file_path: str) -> str:
        path = file_path.lower()
        if path.endswith('.opf'): return 'OPF'
        if path.endswith('.html') or path.endswith('.xhtml'): return 'XHTML'
        if path.endswith('.css'): return 'CSS'
        return 'Unknown'