#!/usr/bin/env python3
"""
Supernote PDF to Markdown OCR using Qwen3-VL via native Ollama
Fast, accurate, with GPU acceleration via Metal
"""

import ollama
from pdf2image import convert_from_path
from pathlib import Path
import sys
import os
from datetime import datetime


def _get_poppler_path():
    """Return bundled poppler path when running inside a PyInstaller .app, else None."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'poppler')
    return None


def merge_lines_into_sentences(text):
    """
    Merge lines that are part of the same sentence.
    Lines that don't end with sentence-ending punctuation (. ! ? : ;) 
    are merged with the next line.
    
    Preserves intentional line breaks (empty lines, list items, etc.)
    """
    lines = text.split('\n')
    merged_lines = []
    current_sentence = []
    
    for line in lines:
        stripped = line.strip()
        
        # Empty line - finish current sentence and add blank line
        if not stripped:
            if current_sentence:
                merged_lines.append(' '.join(current_sentence))
                current_sentence = []
            merged_lines.append('')  # Preserve blank line
            continue
        
        # List items, headers, arrows, or circled numbers - keep separate
        is_list_item = stripped.startswith(('#', '-', '*', '•', '→'))
        is_numbered = len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in '.)'
        is_alpha = len(stripped) > 2 and stripped[0].isalpha() and stripped[1] in '.)' and stripped[2] == ' '
        is_circled = stripped and ord(stripped[0]) in range(0x2460, 0x2474)  # ①-⑳
        if is_list_item or is_numbered or is_alpha or is_circled:
            if current_sentence:
                merged_lines.append(' '.join(current_sentence))
                current_sentence = []
            merged_lines.append(stripped)
            continue
        
        # Add to current sentence
        current_sentence.append(stripped)
        
        # Check if line ends with sentence-ending punctuation
        if stripped.endswith(('.', '!', '?', ':', ';')):
            merged_lines.append(' '.join(current_sentence))
            current_sentence = []
    
    # Add any remaining sentence
    if current_sentence:
        merged_lines.append(' '.join(current_sentence))
    
    return '\n'.join(merged_lines)


def ocr_handwritten_pdf(pdf_path, output_file=None, dpi=400, format='markdown', add_metadata=True, model='qwen3-vl:8b-instruct'):
    """
    Extract text from handwritten PDF using Qwen3-VL
    
    Args:
        pdf_path: Path to the PDF file
        output_file: Optional path to save the extracted text (default: None, auto-generates .md file)
        dpi: DPI for PDF to image conversion (default: 300)
        format: Output format - 'markdown' or 'text' (default: 'markdown')
        add_metadata: Add YAML frontmatter metadata to markdown (default: True)
    
    Returns:
        String containing all extracted text in specified format
    """
    
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"Processing: {pdf_path.name}")
    print(f"Converting PDF to images at {dpi} DPI...")
    
    # Convert PDF pages to images
    images = convert_from_path(str(pdf_path), dpi=dpi, poppler_path=_get_poppler_path())
    
    print(f"Found {len(images)} page(s)")
    
    all_text = []
    
    for i, image in enumerate(images, 1):
        print(f"Processing page {i}/{len(images)} with Qwen3-VL...", end=" ", flush=True)
        
        # Save temporarily
        temp_image = f"/tmp/page_{i}.png"
        image.save(temp_image, "PNG")
        
        try:
            # Use Ollama with specified model (runs with Metal GPU acceleration!)
            response = ollama.chat(
                model=model,
                messages=[{
                    'role': 'user',
                    'content': '''You are an OCR engine transcribing handwritten personal notes. Output ONLY the transcribed text — nothing else.

TRANSCRIPTION RULES:
- Transcribe every word exactly as written, including first-person "I" at the start of bullet points (e.g. "- I choose…", "- I jump…"). Never drop a leading "I".
- Preserve all parenthetical and marginal annotations, even if they appear in smaller text at the edge of a line (e.g. "(especially)", "(coverage)", "(service)").
- Preserve technical terms, file extensions (.xy, .xyz, .md), and tool names exactly as written — do not guess or normalise them.
- Preserve all structural markers exactly: arrows (→), circled numbers (①②③), bullets (•, -, ○), and bracket annotations like [TeamName:].
- If a word is ambiguous, transcribe your best reading — do not skip it or replace it with a placeholder.
- Do NOT correct grammar, spelling, or word choice.
- Do NOT add, remove, or reorder content.
- Do NOT add commentary, labels, or explanations.
- Do NOT use phrases like "let's", "first line", "next line", "Got it", or "step by step".
- Do NOT repeat any word or phrase more than twice in a row; if you notice repetition, stop and output your single best transcription.''',
                    'images': [temp_image]
                }]
            )
            
            page_text = response['message']['content']
            
            # Post-process: Merge lines into proper sentences
            # Lines that don't end with sentence-ending punctuation should merge with next line
            page_text = merge_lines_into_sentences(page_text)
            
            if format == 'markdown':
                # Format as markdown with page headers
                if len(images) > 1:
                    all_text.append(f"## Page {i}\n\n{page_text}")
                else:
                    # Single page - no page header needed
                    all_text.append(page_text)
            else:
                all_text.append(f"--- Page {i} ---\n{page_text}")
            
            print("✓")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            error_text = f"*[Error processing page: {e}]*" if format == 'markdown' else f"[Error processing page: {e}]"
            
            if format == 'markdown' and len(images) > 1:
                all_text.append(f"## Page {i}\n\n{error_text}")
            else:
                all_text.append(error_text)
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_image):
                os.remove(temp_image)
    
    # Combine all pages
    content = "\n\n".join(all_text)
    
    # Add markdown metadata if requested
    if format == 'markdown' and add_metadata:
        metadata = f"""---
title: {pdf_path.stem}
source: {pdf_path.name}
created: {datetime.now().strftime('%Y-%m-%d')}
tags: [supernote, handwritten, ocr, qwen3-vl]
ocr_method: Qwen3-VL (Metal GPU)
---

# {pdf_path.stem}

"""
        result = metadata + content
    else:
        result = content
    
    # Auto-generate output filename if not specified
    if output_file is None and format == 'markdown':
        output_file = pdf_path.with_suffix('.md')
    
    # Save to file if specified
    if output_file:
        output_path = Path(output_file)
        output_path.write_text(result, encoding='utf-8')
        print(f"\n✅ Saved output to: {output_path}")
    
    return result


def ocr_batch_pdfs(pdf_directory, output_directory=None, dpi=400, format='markdown', add_metadata=True, model='qwen3-vl:8b-instruct'):
    """
    Process multiple PDF files in a directory
    
    Args:
        pdf_directory: Directory containing PDF files
        output_directory: Directory to save extracted files (default: same as pdf_directory)
        dpi: DPI for PDF to image conversion (default: 300)
        format: Output format - 'markdown' or 'text' (default: 'markdown')
        add_metadata: Add YAML frontmatter metadata to markdown (default: True)
    """
    
    pdf_dir = Path(pdf_directory)
    
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        raise NotADirectoryError(f"Directory not found: {pdf_dir}")
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    output_dir = Path(output_directory) if output_directory else pdf_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        
        # Set output file extension based on format
        extension = '.md' if format == 'markdown' else '.txt'
        output_file = output_dir / f"{pdf_file.stem}{extension}"
        
        try:
            ocr_handwritten_pdf(pdf_file, output_file=output_file, dpi=dpi, 
                              format=format, add_metadata=add_metadata, model=model)
        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Batch processing complete. Results saved to: {output_dir}")


def main():
    """Main function with command-line interface"""
    
    if len(sys.argv) < 2:
        print("Handwritten PDF OCR to Markdown using Qwen3-VL (Native Ollama)")
        print("=" * 60)
        print("\nUsage:")
        print("  Single file: python native_qwen_ocr.py <pdf_file> [output_file]")
        print("  Batch mode:  python native_qwen_ocr.py --batch <directory> [output_directory]")
        print("\nOptions:")
        print("  --text       Output as plain text instead of markdown")
        print("  --no-meta    Skip YAML frontmatter in markdown output")
        print("  --model      Specify model (default: qwen3-vl:8b-instruct)")
        print("               Options: qwen3-vl:8b-instruct, richardyoung/olmocr2:7b-q8")
        print("\nExamples:")
        print("  # Convert to markdown (auto-named)")
        print("  python native_qwen_ocr.py notes.pdf")
        print()
        print("  # Convert to specific markdown file")
        print("  python native_qwen_ocr.py notes.pdf my_notes.md")
        print()
        print("  # Batch convert all PDFs to markdown")
        print("  python native_qwen_ocr.py --batch ./supernote_pdfs ./obsidian_vault")
        print()
        print("  # Convert to plain text without metadata")
        print("  python native_qwen_ocr.py --text --no-meta notes.pdf output.txt")
        print()
        print("Performance: ~5-15 seconds per page with Metal GPU acceleration")
        sys.exit(1)
    
    # Parse options
    format = 'markdown'
    add_metadata = True
    model = 'qwen3-vl:8b-instruct'
    args = sys.argv[1:]
    
    if '--text' in args:
        format = 'text'
        args.remove('--text')
    
    if '--no-meta' in args:
        add_metadata = False
        args.remove('--no-meta')
    
    if '--model' in args:
        model_index = args.index('--model')
        model = args[model_index + 1]
        args.pop(model_index)  # Remove --model
        args.pop(model_index)  # Remove the model name
    
    if args[0] == "--batch":
        if len(args) < 2:
            print("Error: Batch mode requires a directory path")
            sys.exit(1)
        
        pdf_directory = args[1]
        output_directory = args[2] if len(args) > 2 else None
        
        ocr_batch_pdfs(pdf_directory, output_directory, format=format, add_metadata=add_metadata, model=model)
    
    else:
        pdf_file = args[0]
        output_file = args[1] if len(args) > 1 else None
        
        result = ocr_handwritten_pdf(pdf_file, output_file=output_file, 
                                     format=format, add_metadata=add_metadata, model=model)
        
        if not output_file:
            print("\n" + "="*60)
            print("EXTRACTED TEXT:")
            print("="*60)
            print(result)


if __name__ == "__main__":
    main()
