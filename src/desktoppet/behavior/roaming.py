import random
from dataclasses import dataclass

from desktoppet.movement import Direction


@dataclass(frozen=True, slots=True)
class RoamEvent:
    kind: str
    direction: Direction | None = None


class RoamController:
    """Schedule short autonomous left/right walks without knowing about rendering."""

    def __init__(
        self,
        *,
        min_delay_ms: int,
        max_delay_ms: int,
        min_walk_ms: int,
        max_walk_ms: int,
        rng: random.Random | None = None,
    ) -> None:
        if min_delay_ms < 0 or max_delay_ms < min_delay_ms:
            raise ValueError("Invalid roam delay range")
        if min_walk_ms <= 0 or max_walk_ms < min_walk_ms:
            raise ValueError("Invalid roam walk duration range")

        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.min_walk_ms = min_walk_ms
        self.max_walk_ms = max_walk_ms
        self._rng = rng or random.Random()
        self.direction: Direction | None = None
        self._remaining_ms = 0
        self._schedule_idle()

    @property
    def is_walking(self) -> bool:
        return self.direction is not None

    def tick(self, delta_ms: int, *, active: bool = True) -> RoamEvent | None:
        if delta_ms < 0:
            raise ValueError("delta_ms cannot be negative")

        if not active:
            if self.direction is not None:
                old_direction = self.direction
                self.cancel()
                return RoamEvent("stopped", old_direction)
            return None

        self._remaining_ms -= delta_ms
        if self._remaining_ms > 0:
            return None

        if self.direction is None:
            self.direction = self._rng.choice([Direction.LEFT, Direction.RIGHT])
            self._remaining_ms = self._rng.randint(self.min_walk_ms, self.max_walk_ms)
            return RoamEvent("started", self.direction)

        old_direction = self.direction
        self.direction = None
        self._schedule_idle()
        return RoamEvent("stopped", old_direction)

    def reverse(self) -> Direction:
        if self.direction is None:
            raise RuntimeError("Cannot reverse while not roaming")
        self.direction = (
            Direction.RIGHT if self.direction is Direction.LEFT else Direction.LEFT
        )
        return self.direction

    def cancel(self) -> None:
        self.direction = None
        self._schedule_idle()

    def _schedule_idle(self) -> None:
        self._remaining_ms = self._rng.randint(self.min_delay_ms, self.max_delay_ms)
