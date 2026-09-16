from dataclasses import dataclass
from pathlib import Path
from typing import Literal


PlaybackModeName = Literal["once", "loop", "pingpong"]


# Learning note:
# These dataclasses are the structured Python representation of pet.toml.
# They intentionally stay engine-agnostic: config loading describes what a pet
# wants, while the runtime layer later converts these values into live engine
# objects such as Animation, Frame, and BehaviorAction.


@dataclass(frozen=True, slots=True)
class PetSettings:
    """Basic identity and canvas/default-state settings for one pet."""

    name: str
    width: int
    height: int
    scale: float
    default_state: str
    default_animation: str


@dataclass(frozen=True, slots=True)
class FrameConfig:
    """One declarative animation frame from pet.toml."""

    file: Path
    duration_ms: int


@dataclass(frozen=True, slots=True)
class AnimationConfig:
    """Declarative animation data before runtime objects are constructed."""

    name: str
    frames: tuple[FrameConfig, ...]
    mode: PlaybackModeName = "loop"


@dataclass(frozen=True, slots=True)
class BehaviorActionConfig:
    """One weighted idle behavior declared by the pet package."""

    name: str
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class BehaviorConfig:
    """Configuration for weighted idle actions such as blinking."""

    min_delay_ms: int
    max_delay_ms: int
    actions: tuple[BehaviorActionConfig, ...]


@dataclass(frozen=True, slots=True)
class RoamConfig:
    """Configuration describing how autonomous walking should behave."""

    min_delay_ms: int
    max_delay_ms: int
    min_walk_ms: int
    max_walk_ms: int
    speed_px_s: float
    left_animation: str
    right_animation: str


@dataclass(frozen=True, slots=True)
class InteractionConfig:
    """Animations the pet should play for simple pointer interactions."""

    click_animation: str | None = None
    double_click_animation: str | None = None


@dataclass(frozen=True, slots=True)
class PetManifest:
    """The complete validated blueprint handed from config loading to the engine.

    Think of this as the boundary between configuration and runtime:

        pet.toml -> load_manifest() -> PetManifest -> runtime builder -> Pet

    `PetManifest` contains only declarative configuration. It does not contain
    live Animation/Frame objects and it does not know anything about GTK.
    """

    schema_version: int
    root: Path
    pet: PetSettings
    animations: dict[str, AnimationConfig]
    transitions: dict[str, set[str]]
    idle_behavior: BehaviorConfig | None = None
    roam_behavior: RoamConfig | None = None
    interaction: InteractionConfig | None = None
