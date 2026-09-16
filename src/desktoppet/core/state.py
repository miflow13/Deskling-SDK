# Learning notes:
# A state is the pet's current mode, such as "idle", "walking", or "dragging".
# The StateController does not decide *when* the pet should change state.
# It only owns the current state and enforces the transition rules loaded from
# pet.toml. This keeps state validation separate from behavior, animation, and GTK.
#
# Data flow:
# pet.toml [transitions] -> PetManifest.transitions -> StateController
#
# Example:
#   idle -> walking       allowed
#   walking -> dragging   allowed
#   dragging -> reaction  rejected if pet.toml does not list it


class InvalidTransitionError(RuntimeError):
    """Raised when code tries to perform a state change that pet.toml forbids."""

    pass


class StateController:
    """Owns the pet's current state and validates transitions."""

    def __init__(self, initial_state: str, transitions: dict[str, set[str]]) -> None:
        if not initial_state:
            raise ValueError("initial_state cannot be empty")

        # current_state is the single source of truth for what the pet is doing
        # right now. Pet reads this value instead of each subsystem keeping its
        # own competing idea of the current state.
        self.current_state = initial_state

        # Make our own sets so callers cannot accidentally mutate the controller's
        # rules after construction by changing the original dictionary.
        self._transitions = {
            state: set(targets) for state, targets in transitions.items()
        }

    def can_transition(self, target: str) -> bool:
        """Check whether a transition is legal without changing any state."""
        if target == self.current_state:
            return True

        # Example: if current_state == "idle", look up the set of states that
        # pet.toml allows idle to enter and ask whether target is in that set.
        return target in self._transitions.get(self.current_state, set())

    def transition(self, target: str) -> str:
        """Move to target, or raise if that state change is not allowed."""
        if not self.can_transition(target):
            raise InvalidTransitionError(
                f"Cannot transition from {self.current_state!r} to {target!r}"
            )

        previous = self.current_state
        self.current_state = target

        # Returning the previous state lets Pet emit useful events such as:
        # state.changed(previous="idle", current="walking")
        return previous

    def try_transition(self, target: str) -> bool:
        """Attempt a transition without raising an exception on failure."""
        if not self.can_transition(target):
            return False
        self.current_state = target
        return True
