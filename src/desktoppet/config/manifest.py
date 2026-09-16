from dataclasses import dataclass
from pathlib import Path

from desktoppet.animation import Animation
from desktoppet.behavior import BehaviorAction


@dataclass(frozen=True, slots=True)
class PetSettings:
    name: str
    width: int
    height: int
    scale: float
    default_state: str
    default_animation: str


@dataclass(frozen=True, slots=True)
class BehaviorConfig:
    min_delay_ms: int
    max_delay_ms: int
    actions: list[BehaviorAction]


@dataclass(slots=True)
class PetManifest:
    root: Path
    pet: PetSettings
    animations: dict[str, Animation]
    transitions: dict[str, set[str]]
    idle_behavior: BehaviorConfig | None = None
