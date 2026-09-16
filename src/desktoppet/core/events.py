from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


# Learning note: an Event is just a small message.
#
# Example:
#     Event("drag.started", {"x": 100, "y": 200})
#
# The event says WHAT happened and can carry extra data about it. It does not
# know who will respond. That separation is what keeps the SDK decoupled.
@dataclass(frozen=True, slots=True)
class Event:
    name: str
    data: dict[str, Any] = field(default_factory=dict)


# Learning note: EventHandler is a type alias meaning:
# "any function that receives one Event and returns nothing".
EventHandler = Callable[[Event], None]


class EventBus:
    """Very small publish/subscribe bus used to keep SDK components decoupled.

    Learning note:
        The EventBus implements the publish/subscribe pattern.

        A publisher emits an event:
            pet.events.emit("movement.edge_reached", direction="left")

        Subscribers listen for that event:
            pet.events.subscribe("movement.edge_reached", my_handler)

        The publisher does not need to know which subscribers exist. That means
        movement code does not need direct references to UI, sound, logging, or
        pet-specific behavior code.
    """

    def __init__(self) -> None:
        # Each event name maps to a list of functions that want to hear it.
        # defaultdict(list) creates an empty list automatically for new names.
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> Callable[[], None]:
        """Register a handler and return a small function that removes it later."""
        self._handlers[event_name].append(handler)

        def unsubscribe() -> None:
            self.unsubscribe(event_name, handler)

        return unsubscribe

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    def on(self, event_name: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator-friendly form of subscribe().

        This lets pet code eventually look like:

            @pet.on("pet.double_clicked")
            def show_heart(event):
                ...
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self.subscribe(event_name, handler)
            return handler

        return decorator

    def emit(self, event_name: str, **data: Any) -> Event:
        """Publish one event to every handler currently subscribed to its name."""
        event = Event(event_name, data)

        # tuple(...) makes a snapshot of the handler list before iterating.
        # That means a handler can safely unsubscribe itself while the event is
        # being delivered without changing the collection we are looping over.
        for handler in tuple(self._handlers.get(event_name, ())):
            handler(event)

        return event
