from dataclasses import dataclass
from .frame import Frame


@dataclass
class Animation:
    name: str
    frames: list[Frame]
    loop: bool = True