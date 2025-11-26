#!/usr/bin/env python3
"""Remove all emojis from Python files"""

import re
from pathlib import Path

def remove_emojis(text):
    """Remove emoji characters"""
    # Emoji pattern
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002700-\U000027BF"  # Dingbats
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols
        u"\U00002600-\U000026FF"  # Miscellaneous Symbols
        u"\U0001F018-\U0001F270"  # Various asian characters         
        "]+", flags=re.UNICODE)
    
    return emoji_pattern.sub('', text)

files_to_clean = [
    'main.py',
    'epub_toolkit/utils/epubcheck_installer.py',
    'epub_toolkit/epub_processor.py'
]

for file_path in files_to_clean:
    path = Path(file_path)
    if not path.exists():
        print(f"Skip: {file_path} (not found)")
        continue
    
    print(f"Processing: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    cleaned = remove_emojis(content)
    
    if cleaned != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f"  Cleaned!")
    else:
        print(f"  No emojis found")

print("\nDone!")
