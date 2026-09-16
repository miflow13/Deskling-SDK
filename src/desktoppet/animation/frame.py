from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Frame:
    """One animation frame and the time it should remain visible."""

    path: Path
    duration_ms: int

    def __post_init__(self) -> None:
        if self.duration_ms <= 0:
            raise ValueError("Frame duration_ms must be greater than zero")
