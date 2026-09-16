"""Public API for Deskling SDK."""

from .animation import Animation, AnimationPlayer, Frame, PlaybackMode
from .config import (
    AnimationConfig,
    FrameConfig,
    InteractionConfig,
    ManifestError,
    PetManifest,
    load_manifest,
    validate_manifest,
)
from .core import Event, EventBus, InvalidTransitionError, Pet, StateController
from .movement import Bounds, Direction, MovementController, Position, Size
from .package import PackageError, materialize_package, pack_pet
from .platforms import NullBackend, PlatformBackend

__all__ = [
    "Animation",
    "AnimationConfig",
    "AnimationPlayer",
    "Bounds",
    "Direction",
    "Event",
    "EventBus",
    "Frame",
    "FrameConfig",
    "InteractionConfig",
    "InvalidTransitionError",
    "ManifestError",
    "MovementController",
    "NullBackend",
    "PackageError",
    "Pet",
    "PetManifest",
    "PlatformBackend",
    "PlaybackMode",
    "Position",
    "Size",
    "StateController",
    "load_manifest",
    "materialize_package",
    "pack_pet",
    "validate_manifest",
]
