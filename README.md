# Supernote OCR

Converts handwritten Supernote PDFs to Markdown using [Qwen3-VL](https://ollama.com/library/qwen3-vl) running locally via Ollama with Apple Metal GPU acceleration. Completely private — no data leaves your machine.

Has both a CLI (`native_qwen_ocr.py`) and a Tkinter GUI (`ocr_gui.py`).

> **Disclaimer:** This is an unofficial community tool and is not affiliated with or endorsed by Ratta Tech.

**Platform:** Tested on macOS (Apple Silicon). The Python code should work on Linux and Windows via Ollama, but no installers or launchers are provided for those platforms yet — PRs welcome.

## Features

- **5–15 seconds per page** with Metal GPU (vs 600s+ on CPU-only)
- **Markdown output** with YAML frontmatter, compatible with Obsidian
- **Batch mode** to process entire folders of PDFs
- **Private** — runs fully locally via Ollama

## Requirements

- macOS with Apple Silicon (for Metal GPU acceleration)
- **16 GB RAM minimum; 32 GB recommended.** The 8B model occupies ~6 GB. On 16 GB it runs but leaves little headroom; on 8 GB it will be very slow or fail to load.
- [Ollama](https://ollama.com) installed and running
- Python 3.11+

## Setup

### Option A — install script (easiest)

Requires [Homebrew](https://brew.sh). Installs micromamba, all dependencies, and downloads the model automatically. No Anaconda account or Terms of Service required.

```bash
git clone https://github.com/divw1/supernote-ocr
cd supernote-ocr
bash install_mac.command
```

### Option B — manual (micromamba)

```bash
micromamba create -n supernote-ocr -c conda-forge python=3.12 pip
micromamba install -n supernote-ocr -c conda-forge poppler
micromamba run -n supernote-ocr python -m pip install -r requirements_native.txt
ollama pull qwen3-vl:8b-instruct
chmod +x launch_ocr_gui_mac.command
```

## Usage

### GUI (recommended)

Double-click `launch_ocr_gui_mac.command` in Finder.

> **macOS Gatekeeper:** The first time you double-click it, macOS may block it. Right-click → Open to bypass, or go to System Settings → Privacy & Security → allow it.

To launch from the terminal instead:

```bash
python3 ocr_gui.py
# or, with conda:
conda activate supernote-ocr && python ocr_gui.py
```

### CLI

```bash
# Single file (auto-names output)
python native_qwen_ocr.py notes.pdf

# Single file with explicit output path
python native_qwen_ocr.py notes.pdf ~/Obsidian/Notes/meeting.md

# Batch — process all PDFs in a folder
python native_qwen_ocr.py --batch input/ output/

# Plain text output (no YAML frontmatter)
python native_qwen_ocr.py --text --no-meta notes.pdf output.txt

# Use a different model
python native_qwen_ocr.py --model qwen3-vl:8b-instruct notes.pdf
```

## Output format

Markdown with YAML frontmatter:

```markdown
---
source: my_notes.pdf
ocr_date: 2025-01-01
pages: 4
model: qwen3-vl:8b-instruct
---

Page content here...
```

## OCR quality notes

**Print handwriting** produces near-perfect output. **Cursive** works but causes occasional word substitutions that are at the model's recognition ceiling and cannot be fixed by prompting.

**Prompt tuning** that helped for cursive:
- Preserving first-person "I" at the start of bullet points
- Capturing marginal/parenthetical annotations
- Keeping circled numbers (①②③) and arrows (→) intact
- Not normalising technical terms and file extensions

## Troubleshooting



**"Model not found"** — run `ollama pull qwen3-vl:8b-instruct`

**"Ollama not running"** — run `ollama serve` (or just launch the script; Ollama auto-starts on macOS)

**Launcher won't open** — run `chmod +x launch_ocr_gui_mac.command` once after cloning, then right-click → Open the first time to pass Gatekeeper

**Slow (60+ s/page)** — check GPU usage with `ollama ps`; if no GPU memory shown, restart Ollama with `pkill ollama && ollama serve`

## Acknowledgements

- [Ollama](https://ollama.com) — local model runtime ([MIT License](https://github.com/ollama/ollama/blob/main/LICENSE))
- [Qwen3-VL](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) by Alibaba DAMO Academy — vision-language model ([Apache 2.0 License](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/blob/main/LICENSE))
- [pdf2image](https://github.com/Belval/pdf2image) — PDF to image conversion
- [Pillow](https://python-pillow.org) — image processing

This tool calls Ollama and Qwen3-VL as local services. Their respective licenses apply to those components.
