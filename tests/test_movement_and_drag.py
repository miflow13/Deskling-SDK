from desktoppet.interaction import DragController
from desktoppet.movement import Bounds, Direction, MovementController, Position, Size


def test_movement_clamps_to_bounds() -> None:
    movement = MovementController(Bounds(0, 0, 100, 100), Size(20, 20), speed_px_s=100)
    movement.move(Direction.RIGHT, 5)
    movement.move(Direction.DOWN, 5)
    assert movement.position == Position(80, 80)


def test_drag_preserves_pointer_offset() -> None:
    movement = MovementController(
        Bounds(0, 0, 500, 500),
        Size(20, 20),
        position=Position(100, 100),
    )
    drag = DragController(movement)
    drag.start(110, 115)
    assert drag.update(210, 215) == Position(200, 200)
