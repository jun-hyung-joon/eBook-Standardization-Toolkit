#!/usr/bin/env python3
"""
Batch test all sample EPUBs
Runs main.py on each EPUB and analyzes unfixed errors
"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict
import sys
import os

# Set UTF-8 for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_epub(epub_path):
    """Test single EPUB with main.py"""
    print(f"\n{'='*70}")
    print(f"Testing: {epub_path.name}")
    print('='*70)
    
    result = {
        'file': epub_path.name,
        'initial_errors': [],
        'final_errors': [],
        'unfixed_errors': [],
        'success': False
    }
    
    try:
        # Run main.py (quiet mode)
        cmd = [sys.executable, 'main.py', str(epub_path), '-q']
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            encoding='utf-8',
            errors='replace'
        )
        
        output = process.stdout + process.stderr
        
        # Parse output for error codes
        # EPUBCheck format: "ERROR(XXX-###): message"
        import re
        error_pattern = r'ERROR\(([A-Z]+-\d+[a-z]?)\):'
        
        errors_found = re.findall(error_pattern, output)
        
        if errors_found:
            result['final_errors'] = list(set(errors_found))
            result['unfixed_errors'] = result['final_errors']
            print(f"  Remaining errors: {len(result['final_errors'])}")
            for err in result['final_errors'][:5]:  # Show first 5
                print(f"    - {err}")
        else:
            print(f"  Success: No errors remaining!")
            result['success'] = True
        
        return result
        
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Timeout (>5 min)")
        result['unfixed_errors'] = ['TIMEOUT']
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        result['unfixed_errors'] = ['EXCEPTION']
        return result

# Main execution
print("="*70)
print("Batch Testing - eBook Standardization Toolkit")
print("="*70)

test_sample_dir = Path('test_sample')
epub_files = sorted(test_sample_dir.glob('*.epub'))

print(f"\nFound {len(epub_files)} EPUB files")

results = []
unfixed_by_code = defaultdict(int)

for i, epub_path in enumerate(epub_files, 1):
    print(f"\n[{i}/{len(epub_files)}] {epub_path.name}")
    
    result = test_epub(epub_path)
    results.append(result)
    
    for err_code in result['unfixed_errors']:
        unfixed_by_code[err_code] += 1

# Summary
print("\n" + "="*70)
print("RESULTS")
print("="*70)

total_tested = len(results)
total_success = sum(1 for r in results if r['success'])
total_with_errors = total_tested - total_success

print(f"\nFiles tested: {total_tested}")
print(f"Success (no errors): {total_success}")
print(f"With remaining errors: {total_with_errors}")

if total_with_errors > 0:
    print(f"\nSuccess rate: {(total_success/total_tested*100):.1f}%")
    
    print("\nMost common unfixed errors:")
    for code, count in sorted(unfixed_by_code.items(), key=lambda x: -x[1])[:15]:
        print(f"  {code:20} {count:3}x")

# Save results
output_file = 'batch_test_results.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        'summary': {
            'tested': total_tested,
            'success': total_success,
            'with_errors': total_with_errors,
            'success_rate': f"{(total_success/total_tested*100) if total_tested>0 else 0:.1f}%"
        },
        'unfixed_by_code': dict(unfixed_by_code),
        'details': results
    }, f, indent=2, ensure_ascii=False)

print(f"\nResults saved to: {output_file}")
print("="*70)
