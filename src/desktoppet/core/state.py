class InvalidTransitionError(RuntimeError):
    pass


class StateController:
    """Owns the pet's current state and validates transitions."""

    def __init__(self, initial_state: str, transitions: dict[str, set[str]]) -> None:
        if not initial_state:
            raise ValueError("initial_state cannot be empty")
        self.current_state = initial_state
        self._transitions = {state: set(targets) for state, targets in transitions.items()}

    def can_transition(self, target: str) -> bool:
        if target == self.current_state:
            return True
        return target in self._transitions.get(self.current_state, set())

    def transition(self, target: str) -> str:
        if not self.can_transition(target):
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_state!r} to {target!r}"
            )
        previous = self.current_state
        self.current_state = target
        return previous

    def try_transition(self, target: str) -> bool:
        if not self.can_transition(target):
            return False
        self.current_state = target
        return True
