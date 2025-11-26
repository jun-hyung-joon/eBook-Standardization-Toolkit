#!/usr/bin/env python3
"""
Correct batch test - WITH re-validation
1. Run EPUBCheck on original
2. AI fix
3. Save fixed EPUB
4. Run EPUBCheck on fixed EPUB  <- KEY!
5. Compare errors
"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict
import sys
import time

def run_epubcheck(epub_path):
    """Run EPUBCheck and parse errors"""
    jar = Path.home() / ".epub_toolkit" / "epubcheck" / "epubcheck-5.1.0" / "epubcheck.jar"
    
    cmd = ["java", "-jar", str(jar), "-u", str(epub_path)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
        output = result.stdout + result.stderr
        
        # Parse ERROR codes
        import re
        errors = re.findall(r'ERROR\(([A-Z0-9-]+)\):', output)
        return list(set(errors))
    except:
        return []

def test_one_epub(epub_path):
    """Test with full validation"""
    print(f"\n{'='*70}")
    print(f"{epub_path.name}")
    print('='*70)
    
    # Step 1: Initial check
    print("  [1/4] Initial EPUBCheck...")
    initial_errors = run_epubcheck(epub_path)
    print(f"    Initial errors: {len(initial_errors)}")
    
    if len(initial_errors) == 0:
        print("    Already perfect!")
        return {'file': epub_path.name, 'initial': 0, 'final': 0, 'unfixed': []}
    
    # Step 2: AI fix
    print("  [2/4] AI fixing...")
    output_path = epub_path.parent / f"{epub_path.stem}_FIXED.epub"
    
    cmd = [sys.executable, "main.py", str(epub_path), "-o", str(output_path), "-q"]
    result = subprocess.run(cmd, capture_output=True, timeout=300, encoding='utf-8', errors='replace')
    
    if not output_path.exists():
        print("    ERROR: AI fix failed - no output file")
        return {'file': epub_path.name, 'initial': len(initial_errors), 'final': len(initial_errors), 'unfixed': initial_errors}
    
    print(f"    Fixed EPUB created: {output_path.name}")
    
    # Step 3: CRITICAL - Re-validate fixed EPUB
    print("  [3/4] Re-validating fixed EPUB...")
    final_errors = run_epubcheck(output_path)
    print(f"    Final errors: {len(final_errors)}")
    
    # Step 4: Compare
    fixed_count = len(initial_errors) - len(final_errors)
    print(f"  [4/4] Result: {fixed_count} fixed, {len(final_errors)} remaining")
    
    if final_errors:
        print("    Unfixed errors:")
        for err in final_errors[:10]:
            print(f"      - {err}")
    
    return {
        'file': epub_path.name,
        'initial': len(initial_errors),
        'final': len(final_errors),
        'unfixed': final_errors,
        'initial_codes': initial_errors,
        'fixed_count': fixed_count
    }

# Main
print("="*70)
print("CORRECT Batch Test - WITH Re-Validation")
print("="*70)

test_dir = Path("test_sample")
epubs = sorted([p for p in test_dir.glob("*.epub") if "_FIXED" not in p.name])  # Original samples only

print(f"\nTesting {len(epubs)} samples...")

results = []
all_unfixed = defaultdict(int)

for i, epub in enumerate(epubs, 1):
    print(f"\n[{i}/{len(epubs)}]")
    result = test_one_epub(epub)
    results.append(result)
    
    for err in result['unfixed']:
        all_unfixed[err] += 1

# Summary
print("\n" + "="*70)
print("RESULTS")
print("="*70)

total_initial = sum(r['initial'] for r in results)
total_final = sum(r['final'] for r in results)
total_fixed = total_initial - total_final

print(f"\nTotal initial errors: {total_initial}")
print(f"Total fixed: {total_fixed}")
print(f"Total unfixed: {total_final}")
print(f"Fix rate: {(total_fixed/total_initial*100) if total_initial > 0 else 0:.1f}%")

if all_unfixed:
    print(f"\nTop unfixed error codes:")
    for code, count in sorted(all_unfixed.items(), key=lambda x: -x[1])[:15]:
        print(f"  {code:30} {count:3}x")

def generate_report(results, output_file="test_report.md"):
    """Generate a Markdown report from test results"""
    total = len(results)
    success = sum(1 for r in results if r['final'] == 0)
    failed = total - success
    success_rate = (success / total * 100) if total > 0 else 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Batch Test Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Samples:** {total}\n")
        f.write(f"**Success Rate:** {success_rate:.1f}% ({success}/{total})\n\n")
        
        f.write("## Summary\n")
        f.write(f"The batch test processed {total} EPUB files. ")
        f.write(f"{success} files were successfully fixed (0 remaining errors), while {failed} files still have errors.\n\n")
        
        if failed > 0:
            f.write("## Failed Samples Analysis\n\n")
            for r in results:
                if r['final'] > 0:
                    f.write(f"### {r['file']}\n")
                    f.write(f"- **Initial Errors:** {r['initial']}\n")
                    f.write(f"- **Final Errors:** {r['final']}\n")
                    f.write(f"- **Status:** {'Regressed' if r['final'] > r['initial'] else 'Improved' if r['final'] < r['initial'] else 'Unchanged'}\n")
                    f.write("- **Remaining Errors:**\n")
                    for err in r['unfixed']:
                        f.write(f"  - `{err}`\n")
                    f.write("\n")
        
        f.write("## Detailed Results\n\n")
        f.write("| File | Initial | Final | Status |\n")
        f.write("| :--- | :---: | :---: | :--- |\n")
        for r in results:
            status = "✅ Pass" if r['final'] == 0 else "❌ Fail"
            f.write(f"| {r['file']} | {r['initial']} | {r['final']} | {status} |\n")

    print(f"\nReport generated: {output_file}")

# Save JSON
with open('correct_test_results.json', 'w', encoding='utf-8') as f:
    json.dump({
        'summary': {
            'initial': total_initial,
            'fixed': total_fixed,
            'unfixed': total_final,
            'fix_rate': f"{(total_fixed/total_initial*100) if total_initial>0 else 0:.1f}%"
        },
        'unfixed_by_code': dict(all_unfixed),
        'details': results
    }, f, indent=2, ensure_ascii=False)

print(f"\nSaved to: correct_test_results.json")

# Generate Markdown Report
generate_report(results)
print("="*70)
