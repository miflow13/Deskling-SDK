import pytest

from desktoppet.core import EventBus, InvalidTransitionError, StateController


def test_event_bus_delivers_payload() -> None:
    bus = EventBus()
    received = []
    bus.subscribe("pet.clicked", received.append)
    bus.emit("pet.clicked", button=1)
    assert received[0].data["button"] == 1


def test_state_controller_rejects_invalid_transition() -> None:
    states = StateController("idle", {"idle": {"walking"}, "walking": {"idle"}})
    states.transition("walking")
    with pytest.raises(InvalidTransitionError):
        states.transition("dragging")
