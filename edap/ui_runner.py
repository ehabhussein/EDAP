"""
UI runner for EDAP Streamlit interface.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Streamlit UI."""
    try:
        import streamlit
    except ImportError:
        print("Streamlit is not installed. Install with:")
        print("  pip install edap[ui]")
        print("  # or")
        print("  pip install streamlit pandas")
        sys.exit(1)

    ui_path = Path(__file__).parent / "ui.py"

    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(ui_path),
        "--server.headless", "true",
    ])


if __name__ == "__main__":
    main()
