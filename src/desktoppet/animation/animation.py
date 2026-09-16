from dataclasses import dataclass
from enum import StrEnum

from .frame import Frame


class PlaybackMode(StrEnum):
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "pingpong"


# Learning note:
# An Animation is still just data. It groups Frames together and describes
# how the sequence should behave when it reaches an end.
#
# Frame = one image + duration
# Animation = named list of Frames + playback mode
# AnimationPlayer = the thing that actually moves through those Frames
@dataclass(slots=True)
class Animation:
    """A named sequence of frames plus its playback mode."""

    name: str
    frames: list[Frame]
    mode: PlaybackMode = PlaybackMode.LOOP

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Animation name cannot be empty")
        if not self.frames:
            raise ValueError(f"Animation {self.name!r} must contain at least one frame")

    @property
    def loop(self) -> bool:
        """Compatibility/readability helper used by simple pet code."""
        return self.mode is not PlaybackMode.ONCE
