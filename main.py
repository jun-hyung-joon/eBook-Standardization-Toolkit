#!/usr/bin/env python3
"""
🚀 EPUB Accessibility AI Toolkit - main execution script (output ordering optimized)
"""

import os
import sys
import argparse
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from epub_toolkit.epub_processor import EPUBProcessor
from epub_toolkit.config_manager import get_default_ai

def setup_logging(verbose: bool):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    if root_logger.handlers:
        root_logger.handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        'epub_tool.log', 
        maxBytes=5*1024*1024,
        backupCount=3, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

def main():
    parser = argparse.ArgumentParser(description='🚀 EPUB Accessibility AI Toolkit')
    
    parser.add_argument('input_file', nargs='?', help='Input EPUB file')
    parser.add_argument('-o', '--output', help='Output EPUB filename')
    parser.add_argument('--ai', default=None, 
                       choices=['claude', 'gpt', 'gemini', 'grok'],
                       help='AI provider to use')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-q', '--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--check-only', action='store_true', help='Perform validation only')
    parser.add_argument('--test-ai', action='store_true', help='Test AI connections')
    parser.add_argument('--install-tools', action='store_true', help='Install external tools')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        if not args.quiet:
            logger.info("🚀 EPUB Accessibility AI Toolkit starting")
            
        if args.ai is None:
            args.ai = get_default_ai()
        
        if args.test_ai:
            from epub_toolkit.ai.ai_coordinator import test_all_ai_connections
            test_all_ai_connections(verbose=True)
            return 0
        
        if args.install_tools:
            logger.info("🔧 Installing external tools...")
            from epub_toolkit.utils.epubcheck_installer import install_latest_epubcheck
            install_latest_epubcheck()
            return 0
        
        if not args.input_file:
            parser.print_help()
            return 1
        
        if not Path(args.input_file).exists():
            logger.error(f"❌ File not found: {args.input_file}")
            return 1
        
        processor = EPUBProcessor(verbose=args.verbose)
        
        if args.check_only:
            logger.info(f"🔍 Running EPUB validation: {args.input_file}")
            result = processor._run_epubcheck(args.input_file)
            raw_log = result.get('stdout', '') + "\n" + result.get('stderr', '')
            errors = processor._parse_epubcheck_text(raw_log)
            logger.info(f"📊 Number of errors: {len(errors)}")
            if errors:
                for i, err in enumerate(errors[:10], 1):
                    logger.info(f"   {i}. [{err.error_code}] {err.message}")
            return 0 if not errors else 1

        if not args.quiet:
            logger.info(f"📚 Starting processing")
            logger.info(f"   📁 Input: {args.input_file}")
            logger.info(f"   🤖 AI: {args.ai.upper()}")

        result = processor.improve_epub(
            input_file=args.input_file,
            output_file=args.output,
            ai_model=args.ai
        )
        
        if result.success:
            if not args.quiet:
                # ✅ Note: output ordering adjusted (repacking already handled by processor)
                logger.info(f"\n🎉 Processing complete!")
                logger.info(f"   ✅ Output: {result.output_file}")
                logger.info(f"   📊 Final errors: {result.epubcheck_errors} errors")
                
                # ✅ Print remaining errors only if any, and print at the end
                if result.epubcheck_errors > 0:
                    logger.info("\n📊 Final remaining errors list:")
                    for err_str in result.final_errors_list[:20]:
                        logger.info(f"   {err_str}")
                    if len(result.final_errors_list) > 20:
                        logger.info(f"   ... and {len(result.final_errors_list) - 20} more")
            return 0
        else:
            logger.error(f"\n❌ Processing failed: {result.error_message}")
            return 1

    except KeyboardInterrupt:
        logger.warning("\n🛑 Process interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"🔥 Fatal error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())