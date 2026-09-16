import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BehaviorAction:
    name: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError("BehaviorAction weight must be greater than zero")


class BehaviorScheduler:
    """Chooses weighted idle actions after randomized delays."""

    def __init__(
        self,
        actions: list[BehaviorAction],
        *,
        min_delay_ms: int,
        max_delay_ms: int,
        rng: random.Random | None = None,
    ) -> None:
        if not actions:
            raise ValueError("BehaviorScheduler requires at least one action")
        if min_delay_ms < 0 or max_delay_ms < min_delay_ms:
            raise ValueError("Invalid behavior delay range")
        self.actions = actions
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self._rng = rng or random.Random()
        self._remaining_ms = 0
        self.reset()

    def reset(self) -> None:
        self._remaining_ms = self._rng.randint(self.min_delay_ms, self.max_delay_ms)

    def tick(self, delta_ms: int, *, active: bool = True) -> str | None:
        if delta_ms < 0:
            raise ValueError("delta_ms cannot be negative")
        if not active:
            return None

        self._remaining_ms -= delta_ms
        if self._remaining_ms > 0:
            return None

        chosen = self._rng.choices(
            self.actions,
            weights=[action.weight for action in self.actions],
            k=1,
        )[0]
        self.reset()
        return chosen.name
