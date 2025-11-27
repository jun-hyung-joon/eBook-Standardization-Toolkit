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

@dataclass
class FixResult:
    success: bool
    original_content: str
    fixed_content: str
    applied_fixes: List[str]
    error_messages: List[str]
    delete_file: bool = False

@dataclass
class ErrorInfo:
    tool: str
    error_code: str
    file_path: str
    line_number: Optional[int]
    column_number: Optional[int]
    message: str
    severity: str

class IntelligentEPUBFixer:
    def __init__(self, ai_model: str = None, verbose: bool = False, standards_dir: Optional[Path] = None):
        self.ai_client = None
        self.hints = {}
        self.target_overrides = {}
        self.verbose = verbose
        self.global_rules = {}
        
        possible_paths = []
        if standards_dir: possible_paths.append(Path(standards_dir) / "error_fix_guide.json")
        possible_paths.extend([
            Path(__file__).parent.parent / "standards" / "error_fix_guide.json",
            Path.cwd() / "standards" / "error_fix_guide.json",
            Path.cwd() / "error_fix_guide.json",
        ])
        
        guide_path = None
        for path in possible_paths:
            if path.exists():
                guide_path = path
                break
        
        if guide_path:
            try:
                with open(guide_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.hints = data.get('hints', {})
                    self.target_overrides = data.get('target_overrides', {})
                    self.global_rules = data.get('global_rules', {})
                if self.verbose:
                    logger.info(f"Guide loaded: {len(self.hints)} hints")
            except Exception as e:
                logger.warning(f"Failed to load guide: {e}")
        
    def set_ai_client(self, ai_client):
        self.ai_client = ai_client
    
    def _clean_markdown(self, text: str) -> str:
        text = text.strip()
        if text.startswith('```'):
            first_newline = text.find('\n')
            if first_newline != -1: text = text[first_newline+1:]
        if text.endswith('```'): text = text[:-3]
        return text.strip()

    def fix_file_with_intelligence(self, file_path: str, file_content: str, 
                                  relevant_errors: List[ErrorInfo]) -> FixResult:
        if not self.ai_client:
            return FixResult(False, file_content, file_content, [], ["AI not configured"])
        
        try:
            file_type = self._detect_file_type(file_path)
            prompt = self._create_simple_prompt(file_path, file_type, file_content, relevant_errors)
            
            logger.debug(f"Sending AI request: {file_path}")
            
            ai_result = self.ai_client.generate_content(prompt)
            
            if not ai_result.success:
                return FixResult(False, file_content, file_content, [], [ai_result.error_message])
            
            # Check for deletion marker
            if "<<<DELETE_FILE>>>" in ai_result.content:
                return FixResult(True, file_content, "", ["File marked for deletion"], [], delete_file=True)
            
            improved_content = self._clean_markdown(ai_result.content)
            is_changed = file_content != improved_content
            applied_fixes = [f"{len(relevant_errors)} errors fixed"] if is_changed else ["No fix suggested"]
            
            return FixResult(True, file_content, improved_content, applied_fixes, [])
            
        except Exception as e:
            return FixResult(False, file_content, file_content, [], [str(e)])
    
    def _create_simple_prompt(self, file_path: str, file_type: str, file_content: str, errors: List[ErrorInfo]) -> str:
        error_details = ""
        for i, err in enumerate(errors, 1):
            loc = f"(L{err.line_number})" if err.line_number else ""
            error_details += f"{i}. [{err.error_code}] {err.message} {loc}\n"

        prompt = f"""You are an expert in EPUB 3.3 standard. Fix the errors in the following file.

=== File: {file_path} ({file_type}) ===
{file_content}


=== Error List ===
{error_details}

=== Fix Hints (mandatory) ===
{self._get_hints(errors)}
"""

        prompt += "\n=== Core Principles ===\n"
        if self.global_rules:
            for i, (key, rule) in enumerate(self.global_rules.items(), 1):
                prompt += f"{i}. {rule}\n"
        else:
            prompt += """1. Comply with the W3C EPUB 3.3 standard.
2. Preserve Base64 strings inside CSS/fonts.
3. Return only raw code without Markdown.
4. If the file is corrupted or should be deleted, output ONLY: <<<DELETE_FILE>>>
"""

        prompt += """
=== Instructions ===
Follow the 'Core Principles' above and output only the full file code with errors fixed.
"""
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