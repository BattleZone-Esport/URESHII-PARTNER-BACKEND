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
    # Setup headers with token if available
    headers = {}
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    # First check if URL is accessible
    try:
        head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=30)
        head_response.raise_for_status()
        expected_size = int(head_response.headers.get('content-length', 0))
        if expected_size < 500 * 1024 * 1024:  # Less than 500MB (phi-2 is smaller)
            raise ValueError(f"Model file at URL seems too small: {expected_size / (1024*1024):.2f} MB. Expected at least 500MB.")
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout("Connection timed out while checking model URL. Please verify your internet connection.")
    except requests.exceptions.RequestException as e:
        print(f"Error checking model URL: {e}")
        raise
    except ValueError as e:
        print(f"Error with model file size: {e}")
        raise

    # Download with a longer timeout for large files
    response = requests.get(url, headers=headers, stream=True, timeout=300)  # 5 minutes timeout
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
    # Get model path from environment or use default
    model_dir = Path(os.getenv("MODEL_PATH", "./models")).parent
    model_dir.mkdir(exist_ok=True, parents=True)

    model_path = model_dir / "phi-3.1-mini-4k-instruct.gguf"

    if model_path.exists():
        # Verify existing file size
        file_size_gb = model_path.stat().st_size / (1024**3)
        if file_size_gb >= 2.0:
            print(f"✓ Model already exists at {model_path} (Size: {file_size_gb:.2f} GB)")
            return
        else:
            print(f"! Found incomplete model file ({file_size_gb:.2f} GB), re-downloading...")
            model_path.unlink()

    print("Downloading Phi-3.1-mini-4k-instruct model...")
    print("This may take a while depending on your internet connection...")

    # Get model URL from environment or use default
    # Get Hugging Face token if available
    hf_token = os.getenv("HF_TOKEN")
    
    # Using the Q4_K_M quantized version for lower memory usage
    model_url = os.getenv(
        "MODEL_URL",
        "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf"  # Using phi-2 as it's publicly available
    )

    try:
        download_file(model_url, model_path)
        
        # Verify the downloaded file
        file_size_gb = model_path.stat().st_size / (1024**3)
        print(f"✓ Model downloaded successfully to {model_path}")
        print(f"  Size: {file_size_gb:.2f} GB")
        
        if file_size_gb < 2.0:  # Model should be at least 2GB
            raise RuntimeError(f"Downloaded model is too small ({file_size_gb:.2f} GB). The model might be corrupted or incomplete.")
            
    except requests.exceptions.Timeout:
        print("❌ Error: Download timed out. Please check your internet connection and try again.")
        if model_path.exists():
            model_path.unlink()
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while downloading model: {str(e)}")
        if model_path.exists():
            model_path.unlink()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        if model_path.exists():
            model_path.unlink()  # Clean up partial download
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