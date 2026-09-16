from dataclasses import dataclass
from pathlib import Path


@dataclass
class Frame:
    path: Path
    duration_ms: int

    