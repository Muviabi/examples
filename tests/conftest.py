import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = ROOT / "functions"
sys.path.insert(0, str(ROOT))


def function(path: str) -> Path:
    """``functions/<path>``, the pair's common name without its extension."""
    return FUNCTIONS / path
