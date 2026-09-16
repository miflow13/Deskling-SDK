from desktoppet.behavior import RoamController
from desktoppet.movement import Direction


class FakeRandom:
    def randint(self, low: int, _high: int) -> int:
        return low

    def choice(self, values):
        return values[1]


def test_roam_starts_moves_and_stops_on_schedule() -> None:
    roam = RoamController(
        min_delay_ms=100,
        max_delay_ms=100,
        min_walk_ms=200,
        max_walk_ms=200,
        rng=FakeRandom(),
    )

    started = roam.tick(100)
    assert started is not None
    assert started.kind == "started"
    assert started.direction is Direction.RIGHT
    assert roam.direction is Direction.RIGHT

    assert roam.tick(100) is None
    stopped = roam.tick(100)
    assert stopped is not None
    assert stopped.kind == "stopped"
    assert roam.direction is None


def test_roam_can_reverse_at_an_edge() -> None:
    roam = RoamController(
        min_delay_ms=0,
        max_delay_ms=0,
        min_walk_ms=100,
        max_walk_ms=100,
        rng=FakeRandom(),
    )
    roam.tick(0)
    assert roam.direction is Direction.RIGHT
    assert roam.reverse() is Direction.LEFT
