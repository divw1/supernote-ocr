#!/usr/bin/env python3
"""Supernote OCR — Tkinter GUI frontend for native_qwen_ocr.py"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from native_qwen_ocr import ocr_batch_pdfs, ocr_handwritten_pdf

DEFAULT_MODEL = "qwen3-vl:8b-instruct"
PROJECT_DIR = Path(__file__).parent


class QueueWriter:
    """Redirect sys.stdout writes to a thread-safe queue."""

    def __init__(self, q: queue.Queue):
        self.queue = q

    def write(self, text: str):
        if text:
            self.queue.put(text)

    def flush(self):
        pass


def run_ocr_in_thread(target_func, args, log_queue: queue.Queue, done_event: threading.Event):
    old_stdout = sys.stdout
    sys.stdout = QueueWriter(log_queue)
    try:
        target_func(*args)
        log_queue.put("\n--- Done ---\n")
    except Exception as e:
        log_queue.put(f"\nERROR: {e}\n")
    finally:
        sys.stdout = old_stdout
        done_event.set()


class OCRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Supernote OCR")
        self.root.geometry("660x560")
        self.root.resizable(True, True)

        self.mode = tk.StringVar(value="single")
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(PROJECT_DIR / "output"))
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.add_metadata = tk.BooleanVar(value=True)
        self.plain_text = tk.BooleanVar(value=False)

        self.log_queue: queue.Queue = queue.Queue()
        self.done_event = threading.Event()

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ── Input ────────────────────────────────────────────────────────────
        input_frame = ttk.LabelFrame(self.root, text="Input", padding=6)
        input_frame.pack(fill=tk.X, **pad)

        ttk.Radiobutton(input_frame, text="Single PDF", variable=self.mode,
                        value="single", command=self._on_mode_change).grid(
            row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(input_frame, text="Batch folder", variable=self.mode,
                        value="batch", command=self._on_mode_change).grid(
            row=0, column=1, sticky=tk.W, padx=(12, 0))

        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_path, width=52)
        self.input_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(4, 0))
        self.browse_btn = ttk.Button(input_frame, text="Browse…", command=self._browse_input)
        self.browse_btn.grid(row=1, column=2, padx=(6, 0), pady=(4, 0))

        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(2, weight=0)

        # ── Output ───────────────────────────────────────────────────────────
        output_frame = ttk.LabelFrame(self.root, text="Output folder", padding=6)
        output_frame.pack(fill=tk.X, **pad)

        ttk.Entry(output_frame, textvariable=self.output_path, width=52).grid(
            row=0, column=0, sticky=tk.EW)
        ttk.Button(output_frame, text="Browse…", command=self._browse_output).grid(
            row=0, column=1, padx=(6, 0))

        output_frame.columnconfigure(0, weight=1)

        # ── Options ──────────────────────────────────────────────────────────
        opts_frame = ttk.LabelFrame(self.root, text="Options", padding=6)
        opts_frame.pack(fill=tk.X, **pad)

        ttk.Label(opts_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
        model_combo = ttk.Combobox(opts_frame, textvariable=self.model_var, width=30,
                                   values=[DEFAULT_MODEL])
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=(6, 0))

        ttk.Checkbutton(opts_frame, text="Include metadata (YAML frontmatter)",
                        variable=self.add_metadata).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        ttk.Checkbutton(opts_frame, text="Plain text output (.txt instead of .md)",
                        variable=self.plain_text).grid(
            row=2, column=0, columnspan=2, sticky=tk.W)

        # ── Run button ───────────────────────────────────────────────────────
        self.run_btn = ttk.Button(self.root, text="Run OCR", command=self._on_run)
        self.run_btn.pack(fill=tk.X, padx=8, pady=6)

        # ── Progress log ─────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self.root, text="Progress", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        _mono = "Menlo" if sys.platform == "darwin" else "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
        self.log_text = tk.Text(log_frame, font=(_mono, 11), state=tk.DISABLED,
                                wrap=tk.WORD, yscrollcommand=scrollbar.set,
                                bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

    def _on_mode_change(self):
        # Nothing special needed — Browse handler reads self.mode at call time
        pass

    def _browse_input(self):
        if self.mode.get() == "single":
            path = filedialog.askopenfilename(
                title="Select PDF", filetypes=[("PDF files", "*.pdf")])
        else:
            path = filedialog.askdirectory(title="Select input folder")
        if path:
            self.input_path.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_path.set(path)

    def _log(self, text: str):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _poll_log_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                self._log(text)
        except queue.Empty:
            pass

        if not self.done_event.is_set():
            self.root.after(100, self._poll_log_queue)
        else:
            self.run_btn.config(state=tk.NORMAL)

    def _on_run(self):
        input_val = self.input_path.get().strip()
        if not input_val:
            messagebox.showwarning("No input", "Please select a PDF file or folder.")
            return

        out_dir = Path(self.output_path.get().strip() or str(PROJECT_DIR / "output"))
        out_dir.mkdir(parents=True, exist_ok=True)

        fmt = "text" if self.plain_text.get() else "markdown"
        ext = ".txt" if self.plain_text.get() else ".md"
        model = self.model_var.get().strip() or DEFAULT_MODEL

        if self.mode.get() == "single":
            pdf_path = Path(input_val)
            if not pdf_path.exists():
                messagebox.showerror("Not found", f"File not found:\n{pdf_path}")
                return
            output_file = str(out_dir / (pdf_path.stem + ext))
            target = ocr_handwritten_pdf
            args = (str(pdf_path), output_file, 400, fmt, self.add_metadata.get(), model)
        else:
            batch_dir = Path(input_val)
            if not batch_dir.is_dir():
                messagebox.showerror("Not found", f"Folder not found:\n{batch_dir}")
                return
            target = ocr_batch_pdfs
            args = (str(batch_dir), str(out_dir), 400, fmt, self.add_metadata.get(), model)

        # Clear log and kick off processing
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.run_btn.config(state=tk.DISABLED)
        self.log_queue = queue.Queue()
        self.done_event = threading.Event()

        t = threading.Thread(
            target=run_ocr_in_thread,
            args=(target, args, self.log_queue, self.done_event),
            daemon=True,
        )
        t.start()
        self.root.after(100, self._poll_log_queue)


def main():
    root = tk.Tk()
    OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
