#!/bin/bash
# Double-click this file in Finder to open the Supernote OCR GUI.
cd "$(dirname "$0")"

# Try micromamba environment (installed by install_mac.sh)
MAMBA_PYTHON="$HOME/micromamba/envs/supernote-ocr/bin/python"
if [ -x "$MAMBA_PYTHON" ]; then
    exec "$MAMBA_PYTHON" ocr_gui.py
fi

# Try via micromamba run (in case env is stored elsewhere)
MICROMAMBA="/opt/homebrew/bin/micromamba"
if [ -x "$MICROMAMBA" ]; then
    exec "$MICROMAMBA" run -n supernote-ocr python ocr_gui.py
fi

# Fall back to conda environment
find_conda() {
    for path in \
        "$HOME/miniconda3/etc/profile.d/conda.sh" \
        "$HOME/anaconda3/etc/profile.d/conda.sh" \
        "$HOME/opt/miniconda3/etc/profile.d/conda.sh" \
        "$HOME/opt/anaconda3/etc/profile.d/conda.sh" \
        "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" \
        "/usr/local/miniconda3/etc/profile.d/conda.sh" \
        "/Users/Shared/miniconda3/etc/profile.d/conda.sh"
    do
        if [ -f "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    return 1
}

CONDA_SH=$(find_conda)
if [ -n "$CONDA_SH" ]; then
    source "$CONDA_SH"
    conda activate supernote-ocr 2>/dev/null && exec python3 ocr_gui.py
fi

echo "ERROR: No Python environment found."
echo "Please run install_mac.sh first."
read -p "Press Enter to close..."
exit 1
