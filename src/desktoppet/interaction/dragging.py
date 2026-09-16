from desktoppet.movement import MovementController, Position


class DragController:
    """Tracks pointer-to-pet offset while the platform owns raw pointer input."""

    def __init__(self, movement: MovementController) -> None:
        self.movement = movement
        self.is_dragging = False
        self._offset_x = 0.0
        self._offset_y = 0.0

    def start(self, pointer_x: float, pointer_y: float) -> None:
        self.is_dragging = True
        self._offset_x = pointer_x - self.movement.position.x
        self._offset_y = pointer_y - self.movement.position.y

    def update(self, pointer_x: float, pointer_y: float) -> Position:
        if not self.is_dragging:
            return self.movement.position
        return self.movement.set_position(
            Position(pointer_x - self._offset_x, pointer_y - self._offset_y)
        )

    def end(self) -> Position:
        self.is_dragging = False
        return self.movement.position
