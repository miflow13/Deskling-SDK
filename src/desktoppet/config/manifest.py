from dataclasses import dataclass
from pathlib import Path

from desktoppet.animation import Animation
from desktoppet.behavior import BehaviorAction


# Learning note:
# These dataclasses are the structured Python representation of pet.toml.
# The loader fills them in once, then the rest of the SDK can work with clear
# attributes instead of raw dictionaries from TOML.


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
class BehaviorConfig:
    """Configuration for weighted idle actions such as blinking."""

    min_delay_ms: int
    max_delay_ms: int
    actions: list[BehaviorAction]


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


@dataclass(slots=True)
class PetManifest:
    """The complete validated blueprint handed from config loading to the engine.

    Think of this as the boundary between configuration and runtime:

        pet.toml -> load_manifest() -> PetManifest -> Pet

    `Pet` should not need to parse TOML itself. It receives this already-clean
    object and wires the engine components together from it.
    """

    root: Path
    pet: PetSettings
    animations: dict[str, Animation]
    transitions: dict[str, set[str]]
    idle_behavior: BehaviorConfig | None = None
    roam_behavior: RoamConfig | None = None
    interaction: InteractionConfig | None = None
