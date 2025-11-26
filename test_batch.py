#!/usr/bin/env python3
"""
배치 테스트 스크립트 - main.py를 사용한 올바른 검증
"""

import subprocess
import json
from pathlib import Path
from collections import defaultdict
import sys
import time

def test_one_epub(epub_path):
    """main.py로 EPUB 테스트"""
    print(f"\n{'='*70}")
    print(f"{epub_path.name}")
    print('='*70)
    
    # 출력 파일 경로
    output_path = epub_path.parent / f"{epub_path.stem}_FIXED.epub"
    
    # main.py 실행 (verbose 모드로 에러 정보 받기)
    print("  [1/2] AI로 EPUB 수정 중...")
    cmd = [sys.executable, "main.py", str(epub_path), "-o", str(output_path)]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'  # Unicode 에러 방지
        )
        
        output = result.stdout + result.stderr
        
        # 에러 코드 파싱 (ERROR, USAGE 모두 포함)
        import re
        # EPUBCheck 형식: ERROR(CODE): 또는 USAGE(CODE):
        error_pattern = r'(?:ERROR|USAGE)\(([A-Z0-9-]+)\):'
        errors_found = re.findall(error_pattern, output)
        
        # 중복 제거
        unique_errors = sorted(set(errors_found))
        
        print(f"  [2/2] 결과: {len(unique_errors)}개 에러 발견")
        
        if unique_errors:
            print("    발견된 에러:")
            for err in unique_errors[:10]:
                print(f"      - {err}")
        
        # Fixed 파일 생성 여부 확인
        fixed_exists = output_path.exists()
        
        return {
            'file': epub_path.name,
            'fixed_file_created': fixed_exists,
            'error_count': len(unique_errors),
            'errors': unique_errors,
            'success': len(unique_errors) == 0
        }
        
    except subprocess.TimeoutExpired:
        print(f"  ERROR: 타임아웃 (>5분)")
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
    """Markdown 리포트 생성"""
    total = len(results)
    success = sum(1 for r in results if r['success'])
    failed = total - success
    success_rate = (success / total * 100) if total > 0 else 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 배치 테스트 리포트\n\n")
        f.write(f"**날짜:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**전체 샘플:** {total}개\n")
        f.write(f"**성공률:** {success_rate:.1f}% ({success}/{total})\n\n")
        
        f.write("## 요약\n")
        f.write(f"총 {total}개의 EPUB 파일을 테스트했습니다. ")
        f.write(f"{success}개 파일이 성공적으로 수정되었고(에러 0개), {failed}개 파일에 여전히 에러가 남아있습니다.\n\n")
        
        if failed > 0:
            f.write("## 실패한 샘플 분석\n\n")
            for r in results:
                if not r['success']:
                    f.write(f"### {r['file']}\n")
                    f.write(f"- **Fixed 파일 생성:** {'예' if r['fixed_file_created'] else '아니오'}\n")
                    f.write(f"- **에러 개수:** {r['error_count']}\n")
                    if r['errors']:
                        f.write("- **에러 목록:**\n")
                        for err in r['errors']:
                            f.write(f"  - `{err}`\n")
                    f.write("\n")
        
        f.write("## 전체 결과\n\n")
        f.write("| 파일 | 에러 개수 | 상태 |\n")
        f.write("| :--- | :---: | :--- |\n")
        for r in results:
            status = "✅ 성공" if r['success'] else "❌ 실패"
            f.write(f"| {r['file']} | {r['error_count']} | {status} |\n")
    
    print(f"\n리포트 생성 완료: {output_file}")

# Main
print("="*70)
print("배치 테스트 - main.py 사용")
print("="*70)

test_dir = Path("test_sample")
epubs = sorted([p for p in test_dir.glob("*.epub") if "_FIXED" not in p.name])

print(f"\n테스트 대상: {len(epubs)}개 샘플")

results = []
all_errors = defaultdict(int)

for i, epub in enumerate(epubs, 1):
    print(f"\n[{i}/{len(epubs)}]")
    result = test_one_epub(epub)
    results.append(result)
    
    for err in result['errors']:
        all_errors[err] += 1

# 요약
print("\n" + "="*70)
print("결과")
print("="*70)

total_tested = len(results)
total_success = sum(1 for r in results if r['success'])
total_failed = total_tested - total_success

print(f"\n테스트한 파일: {total_tested}개")
print(f"성공: {total_success}개")
print(f"실패: {total_failed}개")
print(f"성공률: {(total_success/total_tested*100) if total_tested>0 else 0:.1f}%")

if all_errors:
    print(f"\n가장 많이 발견된 에러:")
    for code, count in sorted(all_errors.items(), key=lambda x: -x[1])[:15]:
        print(f"  {code:30} {count:3}회")

# JSON 저장
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

print(f"\nJSON 저장: test_results.json")

# Markdown 리포트 생성
generate_report(results)
print("="*70)
