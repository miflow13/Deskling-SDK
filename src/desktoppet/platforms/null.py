from pathlib import Path

from desktoppet.movement import Bounds, Position


class NullBackend:
    """Headless backend used by tests, CLI simulation, and SDK consumers."""

    def __init__(self, bounds: Bounds | None = None) -> None:
        self._bounds = bounds or Bounds(0, 0, 1920, 1080)
        self.last_frame: Path | None = None
        self.position = Position(0, 0)
        self.frame_history: list[Path] = []

    def get_bounds(self) -> Bounds:
        return self._bounds

    def show_frame(self, path: Path) -> None:
        self.last_frame = path
        self.frame_history.append(path)

    def set_position(self, position: Position) -> None:
        self.position = position
