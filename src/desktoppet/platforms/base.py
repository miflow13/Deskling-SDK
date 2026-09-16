from pathlib import Path
from typing import Protocol, runtime_checkable

from desktoppet.movement import Bounds, Position


@runtime_checkable
class PlatformBackend(Protocol):
    """Contract implemented by desktop-specific window/rendering adapters."""

    def get_bounds(self) -> Bounds: ...

    def show_frame(self, path: Path) -> None: ...

    def set_position(self, position: Position) -> None: ...
