#!/usr/bin/env python3
"""
Batch test script - Proper validation using main.py
"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict
import sys
import time

def test_one_epub(epub_path):
    """Test one EPUB using main.py"""
    print(f"\n{'='*70}")
    print(f"{epub_path.name}")
    print('='*70)
    
    # Output file path
    output_path = epub_path.parent / f"{epub_path.stem}_FIXED.epub"
    
    # Run main.py (in verbose mode to get error info)
    print("  [1/2] Fixing EPUB with AI...")
    cmd = [sys.executable, "main.py", str(epub_path), "-o", str(output_path)]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'  # Prevent Unicode errors
        )
        
        output = result.stdout + result.stderr
        
        # Parse error codes (include both ERROR and USAGE)
        import re
        # EPUBCheck format: ERROR(CODE): or USAGE(CODE):
        error_pattern = r'(?:ERROR|USAGE)\(([A-Z0-9-]+)\):'
        errors_found = re.findall(error_pattern, output)
        
        # Remove duplicates
        unique_errors = sorted(set(errors_found))
        
        print(f"  [2/2] Result: {len(unique_errors)} errors found")
        
        if unique_errors:
            print("    Errors detected:")
            for err in unique_errors[:10]:
                print(f"      - {err}")
        
        # Check if fixed file was created
        fixed_exists = output_path.exists()
        
        return {
            'file': epub_path.name,
            'fixed_file_created': fixed_exists,
            'error_count': len(unique_errors),
            'errors': unique_errors,
            'success': len(unique_errors) == 0
        }
        
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout (>5 min)")
        return {
            'file': epub_path.name,
            'fixed_file_created': False,
            'error_count': -1,
            'errors': ['TIMEOUT'],
            'success': False
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'file': epub_path.name,
            'fixed_file_created': False,
            'error_count': -1,
            'errors': ['EXCEPTION'],
            'success': False
        }

def generate_report(results, output_file="test_report.md"):
    """Generate Markdown report"""
    total = len(results)
    success = sum(1 for r in results if r['success'])
    failed = total - success
    success_rate = (success / total * 100) if total > 0 else 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Batch Test Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Samples:** {total}\n")
        f.write(f"**Success Rate:** {success_rate:.1f}% ({success}/{total})\n\n")
        
        f.write("## Summary\n")
        f.write(f"Tested {total} EPUB files. ")
        f.write(f"{success} files were successfully fixed (0 errors), {failed} files still have errors.\n\n")
        
        if failed > 0:
            f.write("## Failed Sample Analysis\n\n")
            for r in results:
                if not r['success']:
                    f.write(f"### {r['file']}\n")
                    f.write(f"- **Fixed file created:** {'Yes' if r['fixed_file_created'] else 'No'}\n")
                    f.write(f"- **Error count:** {r['error_count']}\n")
                    if r['errors']:
                        f.write("- **Error list:**\n")
                        for err in r['errors']:
                            f.write(f"  - `{err}`\n")
                    f.write("\n")
        
        f.write("## All Results\n\n")
        f.write("| File | Error Count | Status |\n")
        f.write("| :--- | :---: | :--- |\n")
        for r in results:
            status = "Success" if r['success'] else "Failed"
            f.write(f"| {r['file']} | {r['error_count']} | {status} |\n")
    
    print(f"\nReport generated: {output_file}")

# Main
print("="*70)
print("Batch Test - Using main.py")
print("="*70)

test_dir = Path("test_sample")
epubs = sorted([p for p in test_dir.glob("*.epub") if "_FIXED" not in p.name])

print(f"\nTest targets: {len(epubs)} samples")

results = []
all_errors = defaultdict(int)

for i, epub in enumerate(epubs, 1):
    print(f"\n[{i}/{len(epubs)}]")
    result = test_one_epub(epub)
    results.append(result)
    
    for err in result['errors']:
        all_errors[err] += 1

# Summary
print("\n" + "="*70)
print("Results")
print("="*70)

total_tested = len(results)
total_success = sum(1 for r in results if r['success'])
total_failed = total_tested - total_success

print(f"\nFiles tested: {total_tested}")
print(f"Success: {total_success}")
print(f"Failed: {total_failed}")
print(f"Success rate: {(total_success/total_tested*100) if total_tested>0 else 0:.1f}%")

if all_errors:
    print(f"\nMost common errors:")
    for code, count in sorted(all_errors.items(), key=lambda x: -x[1])[:15]:
        print(f"  {code:30} {count:3} times")

# Save JSON
with open('test_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'summary': {
            'total': total_tested,
            'success': total_success,
            'failed': total_failed,
            'success_rate': f"{(total_success/total_tested*100) if total_tested>0 else 0:.1f}%"
        },
        'errors_by_code': dict(all_errors),
        'details': results
    }, f, indent=2, ensure_ascii=False)

print(f"\nJSON saved: test_results.json")

# Generate Markdown report
generate_report(results)
print("="*70)
