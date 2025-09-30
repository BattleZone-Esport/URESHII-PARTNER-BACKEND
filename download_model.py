#!/usr/bin/env python3
"""
Model download script for Phi-3.1
Can be run separately to pre-download the model
"""

import os
import sys
import requests
from pathlib import Path
import tqdm

def download_file(url: str, dest: Path, chunk_size: int = 8192):
    """Download a file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(dest, 'wb') as f:
        # Use tqdm.tqdm because we imported the module, not the function directly
        with tqdm.tqdm(
            desc=dest.name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                size = f.write(chunk)
                progress_bar.update(size)


def main():
    """Main function to download the model"""
    model_dir = Path(os.getenv("MODEL_PATH", "./models")).parent
    model_dir.mkdir(exist_ok=True, parents=True)

    model_path = model_dir / "phi-3.1-mini-4k-instruct.gguf"

    if model_path.exists():
        print(f"Model already exists at {model_path}")
        return

    print("Downloading Phi-3.1-mini-4k-instruct model...")
    print("This may take a while depending on your internet connection...")

    # Using the Q4_K_M quantized version for lower memory usage
    model_url = "https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf"

    try:
        download_file(model_url, model_path)
        print(f"✓ Model downloaded successfully to {model_path}")
        print(f"  Size: {model_path.stat().st_size / (1024**3):.2f} GB")
    except Exception as e:
        print(f"✗ Error downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure tqdm is installed
    try:
        import tqdm
    except ImportError:
        print("Installing tqdm for progress bar...")
        os.system("pip install tqdm")
        import tqdm
    main()