import sys
from pathlib import Path

# Ensure project root directory is in sys.path regardless of execution CWD
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

"""
ASTRAEA Backend 1 — API & Data Flow System
Connects Frontend <-> API <-> Cryptography <-> DLT (Backend 2) <-> Watermarking <-> Forensic Audit.
"""

__version__ = "1.0.0"
