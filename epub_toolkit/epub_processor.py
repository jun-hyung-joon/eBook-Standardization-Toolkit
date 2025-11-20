#!/usr/bin/env python3
"""
🚀 EPUB Processor - Timestamped output version

Features:
1. Run EPUBCheck (text mode, absolute paths, includes -u option)
2. Parse errors and output detailed list
3. Intelligent target file routing (JSON-driven)
4. I/O optimization: Read-Once, Modify-Loop, Write-Once per file
5. Integrated logging
6. ✅ Append timestamp to result filename to avoid overwrites
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
import logging
import zipfile
import re
from pathlib import Path
from datetime import datetime  # ✅ import for timestamp
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .config_manager import config_manager
from .ai.intelligent_fixer import IntelligentEPUBFixer, ErrorInfo

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """EPUB processing result data class"""
    success: bool
    output_file: str = ""
    epubcheck_errors: int = 0
    error_message: str = ""
    processing_time: float = 0.0
    improvements_made: List[str] = field(default_factory=list)
    final_errors_list: List[str] = field(default_factory=list)

class EPUBProcessor:
    """Manages EPUB processing and fixes"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = logging.getLogger("epub_processor")
        
        try:
            self.file_config = config_manager.get('file_processing')
        except Exception as e:
            self.logger.critical(f"Failed to load configuration: {e}")
            sys.exit(1)
        
        self.epubcheck_jar = self._setup_epubcheck_robust()
        if not self.epubcheck_jar:
            self.logger.error("❌ EPUBCheck not found. (epubcheck.jar)")
            sys.exit(1)
    
    def _setup_epubcheck_robust(self) -> str:
        """Locate EPUBCheck JAR path"""
        search_paths = [
            Path.cwd() / "epubcheck.jar",
            Path.cwd() / "tools" / "epubcheck.jar",
            Path.home() / ".epub_toolkit" / "epubcheck" / "epubcheck.jar",
        ]
        
        epubcheck_base = Path.home() / ".epub_toolkit" / "epubcheck"
        if epubcheck_base.exists():
            jars = list(epubcheck_base.glob("**/epubcheck.jar"))
            if jars: return str(jars[0])

        for path in search_paths:
            if path.exists(): return str(path.absolute())
        return ""

    def improve_epub(self, input_file: str, output_file: str = None, ai_model: str = None) -> ProcessingResult:
        """Main EPUB improvement workflow"""
        start_time = time.time()
        
        # 1. Pre-checks
        if not ai_model:
            ai_model = config_manager.get('ai_behavior.default_provider')
        
        if not ai_model:
            return ProcessingResult(False, error_message="AI model not specified", processing_time=0)
        
        if not Path(input_file).exists():
            return ProcessingResult(False, error_message=f"File not found: {input_file}", processing_time=0)
        
        # ✅ If output filename not provided, auto-generate with timestamp
        if not output_file:
            p = Path(input_file)
            suffix = self.file_config.get('output_suffix', '_standardized')
            # Example: 2511201414 (YYMMDDHHMM)
            timestamp = datetime.now().strftime("%y%m%d%H%M")
            output_file = str(p.parent / f"{p.stem}{suffix}_{timestamp}.epub")
        
        # Initialize AI (before processing logs)
        try:
            from .ai.ai_coordinator import get_ai_coordinator
            ai_coordinator = get_ai_coordinator(selected_ai=ai_model)
        except Exception as e:
            return ProcessingResult(False, error_message=f"AI initialization failed: {e}", processing_time=0)

        self.logger.info(f"🚀 Processing start: {input_file}")
        self.logger.info(f"💾 Intended output: {output_file}")
        
        temp_dir = None
        try:
            # 2. Prepare workspace
            temp_prefix = self.file_config.get('temp_dir_prefix', 'epub_toolkit_')
            temp_dir = tempfile.mkdtemp(prefix=temp_prefix)
            work_file = Path(temp_dir) / "work.epub"
            shutil.copy2(input_file, work_file)
            
            standards_dir = Path(__file__).parent / "standards"
            if not standards_dir.exists(): standards_dir = Path.cwd() / "standards"
            
            intelligent_fixer = IntelligentEPUBFixer(standards_dir=standards_dir, verbose=self.verbose)
            intelligent_fixer.set_ai_client(ai_coordinator)
            
            # 3. Initial EPUBCheck run
            self.logger.info("🔍 Running EPUBCheck...")
            check_result = self._run_epubcheck(str(work_file))
            
            raw_log = check_result['stdout'] + "\n" + check_result['stderr']
            parsed_errors = self._parse_epubcheck_text(raw_log)

            if not parsed_errors:
                if check_result['returncode'] == 0:
                    self.logger.info("✅ No errors found.")
                    # Even if no errors, create the requested copy (with timestamp)
                    shutil.copy2(str(work_file), output_file)
                    return ProcessingResult(True, output_file, 0, time.time()-start_time, ["No changes"])
                else:
                    self.logger.error("\n⚠️ [ERROR] EPUBCheck failed but no parseable errors were found.")
                    self.logger.debug(raw_log)
                    return ProcessingResult(False, error_message="EPUBCheck execution failed", processing_time=time.time()-start_time)
            
            # Print detailed error list
            self.logger.info(f"🔍 Detected {len(parsed_errors)} errors:")
            for i, err in enumerate(parsed_errors, 1):
                self.logger.info(f"   {i}. [{err.error_code}] {err.message}")

            # 4. Extract and fix
            extract_dir = Path(tempfile.mkdtemp(prefix="epub_ext_"))
            self.logger.info(f"\n📂 Extracting archive...")
            
            try:
                with zipfile.ZipFile(str(work_file), 'r') as z:
                    z.extractall(extract_dir)
                
                opf_path = self._find_opf_file(extract_dir)
                
                # Group errors by target file (prepare for I/O optimization)
                file_map = {}
                for err in parsed_errors:
                    # Let the fixer instance influence JSON-driven routing
                    tgt = self._get_target_file(err, opf_path, intelligent_fixer)
                    if not tgt: continue
                    if tgt not in file_map: file_map[tgt] = []
                    file_map[tgt].append(err)
                
                self.logger.info(f"🔧 Starting fixes for {len(file_map)} files (sequential)")
                
                fixed_count = 0
                improvements = []
                
                # Per-file loop (minimize file I/O)
                for tgt_file, errors in file_map.items():
                    full_path = extract_dir / tgt_file
                    
                    if not full_path.exists():
                        self.logger.warning(f"   ❌ Missing file: {tgt_file} (skipping)")
                        continue
                    
                    self.logger.info(f"\n📄 Processing file: {tgt_file} (errors: {len(errors)})")
                    
                    try:
                        # Read Once
                        with open(full_path, 'r', encoding='utf-8') as f:
                            current_content = f.read()
                        
                        file_modified = False
                        
                        # Sequential in-memory fix loop
                        for i, error in enumerate(errors, 1):
                            self.logger.info(f"   [{i}/{len(errors)}] Attempting fix: {error.error_code}")
                            
                            # Provide AI with current content and single error
                            fix_res = intelligent_fixer.fix_file_with_intelligence(
                                tgt_file, current_content, [error]
                            )
                            
                            if fix_res.success and fix_res.fixed_content != current_content:
                                current_content = fix_res.fixed_content
                                file_modified = True
                                fixed_count += 1
                                improvements.extend(fix_res.applied_fixes)
                                self.logger.info(f"      ✅ AI fix applied")
                            elif fix_res.error_messages:
                                self.logger.warning(f"      ⚠️ Fix failed: {fix_res.error_messages[0]}")
                            else:
                                self.logger.info(f"      ℹ️ No changes suggested")
                        
                        # Write Once
                        if file_modified:
                            with open(full_path, 'w', encoding='utf-8') as f:
                                f.write(current_content)
                            self.logger.info(f"   💾 File saved")
                        else:
                            self.logger.info(f"   ⏭️ No changes")

                    except UnicodeDecodeError:
                        self.logger.warning(f"   ⏭️ Skipping binary file")
                        continue
                    except Exception as e:
                        self.logger.error(f"   ❌ File processing error: {e}")

                self.logger.info(f"\n📊 Total fixes applied: {fixed_count}")
                
                self.logger.info("📦 Repacking EPUB...")
                self._create_epub_zip(extract_dir, str(work_file))
                
            finally:
                if extract_dir.exists(): shutil.rmtree(extract_dir)
            
            # 5. Final validation
            shutil.copy2(str(work_file), output_file)
            self.logger.info("🔍 Performing final validation...")
            
            final_res = self._run_epubcheck(str(Path(output_file).resolve()))
            final_log = final_res.get('stdout', '') + "\n" + final_res.get('stderr', '')
            final_errors_obj = self._parse_epubcheck_text(final_log)
            
            final_errors_str = []
            for i, err in enumerate(final_errors_obj, 1):
                loc = f"({err.line_number},{err.column_number})" if err.line_number else ""
                msg = f"{i}. {err.severity}({err.error_code}): {err.file_path}{loc}: {err.message}"
                final_errors_str.append(msg)
            
            # Return result object (printing is handled by main.py)
            return ProcessingResult(
                success=True, 
                output_file=output_file, 
                epubcheck_errors=len(final_errors_obj), 
                processing_time=time.time()-start_time, 
                improvements_made=improvements,
                final_errors_list=final_errors_str
            )

        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.logger.error(f"Exception occurred: {e}", exc_info=True)
            return ProcessingResult(False, error_message=str(e), processing_time=time.time()-start_time)
        finally:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)

    def _run_epubcheck(self, epub_path: str) -> Dict[str, Any]:
        """Run EPUBCheck (ensure option order and absolute paths)"""
        cmd = []
        if self.epubcheck_jar.endswith('.jar'):
            cmd = ['java', '-jar', self.epubcheck_jar]
        else:
            cmd = [self.epubcheck_jar]
        
        # -u option: include USAGE-level messages
        cmd.append('-u')
        # File path: always convert to absolute path
        cmd.append(str(Path(epub_path).resolve()))
        
        try:
            # Use text mode only (no JSON)
            res = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                timeout=120
            )
            return {
                "mode": "text",
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode,
                "cmd_str": ' '.join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Timeout",
                "returncode": -1,
                "cmd_str": ' '.join(cmd)
            }
        except Exception as e:
            raise RuntimeError(f"EPUBCheck execution failed: {e}")

    def _parse_epubcheck_text(self, text: str) -> List[ErrorInfo]:
        """Parse text log output (regex)"""
        errors = []
        # Detect all levels including USAGE
        pattern = re.compile(r'(ERROR|WARNING|FATAL|USAGE)\(([A-Z0-9-]+)\):\s*(?:(.*?)(?:\((\d+),(\d+)\))?:\s*)?(.+)')
        
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            
            m = pattern.search(line)
            if m:
                sev, code, path, l, c, msg = m.groups()
                if not path: path = 'unknown'
                
                # Clean path: remove .epub/ prefix or extract filename from absolute path
                if '.epub/' in path: 
                    path = path.split('.epub/')[-1]
                elif path.startswith('/') or ':\\' in path:
                    path = Path(path).name
                
                errors.append(ErrorInfo(
                    tool='epubcheck',
                    error_code=code,
                    file_path=path.strip(),
                    line_number=int(l) if l else None,
                    column_number=int(c) if c else None,
                    message=msg.strip(),
                    severity=sev
                ))
        return errors

    def _get_target_file(self, error: ErrorInfo, opf_file: str, fixer: Optional[IntelligentEPUBFixer] = None) -> str:
        """Route to correct target when error location differs from fix target (JSON-driven)"""
        
        # 1. Check JSON overrides first (if fixer provided)
        if fixer:
            override_target = fixer.get_target_override(error.error_code)
            if override_target == "OPF":
                return opf_file if opf_file else error.file_path

        # 2. Default rule (OPF-based)
        if error.error_code.startswith('OPF') or error.file_path.endswith('.opf'):
            return opf_file if opf_file else error.file_path
            
        # 3. Otherwise return original path (with normalization)
        path = error.file_path
        if '.epub/' in path: path = path.split('.epub/')[-1]
        
        if not path or path == 'unknown':
            return ""
            
        return path

    def _find_opf_file(self, root_dir: Path) -> Optional[str]:
        """Recursive search for OPF file path"""
        for root, _, files in os.walk(root_dir):
            for f in files:
                if f.endswith('.opf'):
                    return os.path.relpath(os.path.join(root, f), root_dir)
        return None

    def _create_epub_zip(self, src: Path, dest: str):
        """Create EPUB zip compliant archive (store mimetype uncompressed)"""
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
            mime = src / 'mimetype'
            if mime.exists():
                z.write(mime, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            for root, _, files in os.walk(src):
                for f in files:
                    if f == 'mimetype': continue
                    fp = os.path.join(root, f)
                    ap = os.path.relpath(fp, src)
                    z.write(fp, ap, compress_type=zipfile.ZIP_DEFLATED)