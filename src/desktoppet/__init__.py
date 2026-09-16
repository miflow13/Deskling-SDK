"""Public API for Deskling SDK."""

from .animation import Animation, AnimationPlayer, Frame, PlaybackMode
from .config import ManifestError, PetManifest, load_manifest
from .core import Event, EventBus, InvalidTransitionError, Pet, StateController
from .movement import Bounds, Direction, MovementController, Position, Size
from .platforms import NullBackend, PlatformBackend

__all__ = [
    "Animation",
    "AnimationPlayer",
    "Bounds",
    "Direction",
    "Event",
    "EventBus",
    "Frame",
    "InvalidTransitionError",
    "ManifestError",
    "MovementController",
    "NullBackend",
    "Pet",
    "PetManifest",
    "PlatformBackend",
    "PlaybackMode",
    "Position",
    "Size",
    "StateController",
    "load_manifest",
]
