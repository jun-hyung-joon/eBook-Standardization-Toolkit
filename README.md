# eBook Standardization Toolkit 

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![EPUB 3.3](https://img.shields.io/badge/Standard-EPUB%203.3-green.svg)](https://www.w3.org/TR/epub-33/)

A Python-based automation tool that validates and automatically repairs EPUB files to comply with the W3C EPUB 3.3 standard. It detects issues using EPUBCheck and intelligently fixes problems using modern LLMs (Claude, GPT, Gemini, Grok).

This toolkit prioritizes high repair accuracy over raw speed. It analyzes and fixes errors sequentially, and is designed to minimize disk I/O by performing in-memory edits.

## Key Features

* Full EPUBCheck integration: Uses the official W3C EPUBCheck tool for precise validation (including Usage-level messages with `-u`).
* Multi-LLM support: Choose between Anthropic Claude, OpenAI GPT, Google Gemini, and xAI Grok.
* Sequential error fixes: Processes detected issues one at a time to reduce hallucinations and increase accuracy.
* I/O optimization: Read-once, modify-in-memory, write-once per file to minimize disk operations.
* Rule customization: Define error-specific fix instructions and routing logic via a JSON guide.
* Intelligent routing: Automatically determine the actual file to modify when an error's reported location differs from the fix target (e.g., modify content.opf for missing resources).

## Installation

### Requirements
* Python 3.8 or newer
* Java Runtime Environment (JRE) 8+ for running EPUBCheck

### Setup Steps
1. Clone the repository:
    ```bash
    git clone https://github.com/jun-hyung-joon/eBook-Standardization-Toolkit.git
    cd eBook-Standardization-Toolkit
    ```

2. Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Install external tools (EPUBCheck):
    ```bash
    python main.py --install-tools
    ```

## Configuration

### 1. API keys (.env)
Create a `.env` file in the project root and add your API keys. This file is ignored by Git for security.

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
XAI_API_KEY=xai-...
```

(Optional) Set the default AI provider:
```
DEFAULT_AI_MODEL=Gemini
```

### 2. Model settings (config/ai_models_config.yaml)
Adjust default model names or token limits in this YAML file.
```yaml
models:
  gemini:
    default: "gemini-2.5-flash"
    max_tokens: 8192
  claude:
    default: "claude-sonnet-4-20250514"
    max_tokens: 4096
```

### 3. Fix logic (epub_toolkit/standards/error_fix_guide.json)
Define how the AI should handle specific EPUBCheck error codes. The JSON controls:
* hints: detailed fix instructions per error code
* target_overrides: force routing to a different file (e.g., modify content.opf for certain errors)

## Usage

Basic conversion using the configured default AI model:
```bash
python main.py book.epub
```

Specify an AI provider (claude, gpt, gemini, grok):
```bash
python main.py book.epub --ai claude
```

Run validation only (no AI fixes):
```bash
python main.py book.epub --check-only
```

### Main options
* -o, --output: specify output filename
* -v, --verbose: enable verbose logging (for debugging)
* -q, --quiet: minimal output

## License
This project is distributed under the MIT License. See the LICENSE file for details.

## Acknowledgments
This project builds upon several outstanding tools and research efforts in the EPUB ecosystem:
* **[epubcheck](https://github.com/w3c/epubcheck)** — the official EPUB validation tool by W3C (used as the core validation engine)

## Dependencies
This toolkit integrates with and requires:
* **[epubcheck](https://github.com/w3c/epubcheck)** (BSD 3-Clause License) - Official EPUB validation tool

## Legal Notice
This project is an independent automation toolkit and is not affiliated with, endorsed by, or sponsored by the W3C, the EPUBCheck project, or any LLM provider(OpenAI, Anthropic, Google, xAI).
