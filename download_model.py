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

def verify_file_size(file_path: Path, expected_min_size_mb: int = 2000) -> bool:
    """Verify the downloaded file meets minimum size requirements"""
    if not file_path.exists():
        return False
    actual_size_mb = file_path.stat().st_size / (1024 * 1024)  # Convert to MB
    return actual_size_mb >= expected_min_size_mb

def download_file(url: str, dest: Path, chunk_size: int = 8192):
    """Download a file with progress bar and verification"""
    # First check if URL is accessible
    try:
        head_response = requests.head(url, allow_redirects=True, timeout=10)
        head_response.raise_for_status()
        expected_size = int(head_response.headers.get('content-length', 0))
        if expected_size < 2000 * 1024 * 1024:  # Less than 2GB
            raise ValueError(f"Model file seems too small: {expected_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"Error checking model URL: {e}")
        raise

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))

    with open(dest, 'wb') as f:
        with tqdm.tqdm(
            desc=dest.name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    size = f.write(chunk)
                    progress_bar.update(size)
    
    # Verify file size after download
    if not verify_file_size(dest):
        dest.unlink()  # Delete incomplete/corrupt file
        raise RuntimeError(f"Downloaded file is too small. Expected at least 2GB")


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
        
        # Verify the downloaded file
        file_size_gb = model_path.stat().st_size / (1024**3)
        print(f"✓ Model downloaded successfully to {model_path}")
        print(f"  Size: {file_size_gb:.2f} GB")
        
        if file_size_gb < 2.0:  # Model should be at least 2GB
            raise RuntimeError(f"Downloaded model is too small ({file_size_gb:.2f} GB)")
            
    except Exception as e:
        print(f"Error downloading model: {e}")
        if model_path.exists():
            model_path.unlink()  # Clean up partial download
        sys.exit(1)
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