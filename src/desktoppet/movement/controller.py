from .model import Bounds, Direction, Position, Size


class MovementController:
    """Platform-independent position and boundary logic."""

    def __init__(
        self,
        bounds: Bounds,
        size: Size,
        *,
        position: Position | None = None,
        speed_px_s: float = 80.0,
    ) -> None:
        if speed_px_s < 0:
            raise ValueError("speed_px_s cannot be negative")
        self.bounds = bounds
        self.size = size
        self.speed_px_s = speed_px_s
        self.position = bounds.clamp(position or Position(bounds.left, bounds.top), size)

    def set_position(self, position: Position) -> Position:
        self.position = self.bounds.clamp(position, self.size)
        return self.position

    def move(self, direction: Direction, delta_s: float) -> Position:
        if delta_s < 0:
            raise ValueError("delta_s cannot be negative")

        distance = self.speed_px_s * delta_s
        dx = dy = 0.0
        if direction is Direction.LEFT:
            dx = -distance
        elif direction is Direction.RIGHT:
            dx = distance
        elif direction is Direction.UP:
            dy = -distance
        elif direction is Direction.DOWN:
            dy = distance

        return self.set_position(Position(self.position.x + dx, self.position.y + dy))
