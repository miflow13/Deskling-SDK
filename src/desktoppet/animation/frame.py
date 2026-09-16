from dataclasses import dataclass
from pathlib import Path


# Learning note:
# A Frame is pure data: which image to show, and for how long.
# It does not know how to render itself or when to advance.
# That separation lets the same animation data work with GTK, tests,
# or another platform backend later.
@dataclass(frozen=True, slots=True)
class Frame:
    """One animation frame and the time it should remain visible."""

    path: Path
    duration_ms: int

    def __post_init__(self) -> None:
        # Invalid timing is rejected as soon as the Frame is created.
        if self.duration_ms <= 0:
            raise ValueError("Frame duration_ms must be greater than zero")
