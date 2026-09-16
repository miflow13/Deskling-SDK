from dataclasses import dataclass
from enum import StrEnum


class Direction(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True, slots=True)
class Position:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Size:
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    def clamp(self, position: Position, size: Size) -> Position:
        max_x = max(self.left, self.right - size.width)
        max_y = max(self.top, self.bottom - size.height)
        return Position(
            x=min(max(position.x, self.left), max_x),
            y=min(max(position.y, self.top), max_y),
        )
