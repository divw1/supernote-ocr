# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Converts handwritten Supernote PDFs to Markdown using Qwen3-VL running locally via Ollama with Apple Metal GPU acceleration. Has both a CLI (`native_qwen_ocr.py`) and a Tkinter GUI (`ocr_gui.py`).

## Setup

```bash
conda activate supernote-ocr
pip install ollama pdf2image pillow
ollama pull qwen2.5vl:7b   # or whatever model is configured
```

Requires `poppler` (installed via conda) for `pdf2image`.

## Running

**GUI (recommended):** Double-click `launch_ocr_gui.command` in Finder.

**CLI:**
```bash
# Single file
python native_qwen_ocr.py input/file.pdf [output/file.md]

# Batch mode
python native_qwen_ocr.py --batch input/ [output/]

# Options
python native_qwen_ocr.py --text file.pdf        # plain text output (no YAML)
python native_qwen_ocr.py --no-meta file.pdf     # skip YAML frontmatter
python native_qwen_ocr.py --model <name> file.pdf
```

## Architecture

**Pipeline:**
1. PDF → per-page images at 400 DPI (`pdf2image`)
2. Each image → Ollama vision model (base64-encoded)
3. Raw OCR text → `merge_lines_into_sentences()` post-processing
4. Output → Markdown file with YAML frontmatter (source, date, page count)

**Key function:** `merge_lines_into_sentences(text)` joins lines that end mid-sentence (heuristic: line doesn't end with punctuation and next line starts lowercase). Recognises `→`, `①–⑳`, `-`, `•`, and numbered items as list-item starts that must not be merged.

## OCR Quality Notes

**Print handwriting vs cursive:** Print is dramatically better. Cursive causes frequent word substitutions (e.g. "Flakey"→"Flare", "Connect"→"Command", "team"→"stream") that are at the model's recognition ceiling and cannot be fixed by prompting. Print handwriting produces near-perfect output. Recommend writing in print.

**Vector vs normal PDF export:** Tested both for print and cursive — zero quality difference in either case. Use normal export. Vector exports at 400 DPI produce very large images (~150M pixels) and trigger PIL decompression warnings with no benefit.

**Prompt changes that helped (cursive):**
- Preserving first-person "I" at the start of bullet points
- Capturing marginal/parenthetical annotations (e.g. "(especially)", "(coverage)")
- Keeping circled numbers (①②③) and arrows (→) intact
- Not normalising technical terms and file extensions

**Remaining cursive errors at the model's ceiling** (not fixable by prompting):
- Visually similar cursive word substitutions
- Phantom characters added to words (e.g. "Architect" → "Architected")
- File extensions misread (e.g. `.xy` → `.txt`)
- Multi-line list structure occasionally garbled

## Output Format

Markdown with YAML frontmatter:
```yaml
---
source: filename.pdf
ocr_date: YYYY-MM-DD
pages: N
model: model-name
---
```
Designed to be compatible with Obsidian.
