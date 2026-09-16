from .animation import Animation, PlaybackMode
from .frame import Frame


class AnimationPlayer:
    """Tracks animation playback without knowing anything about rendering."""

    def __init__(self) -> None:
        self.current_animation: Animation | None = None
        self.frame_index = 0
        self.is_playing = False
        self.just_finished = False
        self._elapsed_ms = 0
        self._direction = 1

    @property
    def current_frame(self) -> Frame | None:
        if self.current_animation is None:
            return None
        return self.current_animation.frames[self.frame_index]

    def play(self, animation: Animation, *, restart: bool = True) -> None:
        if not restart and self.current_animation is animation and self.is_playing:
            return
        self.current_animation = animation
        self.frame_index = 0
        self.is_playing = True
        self.just_finished = False
        self._elapsed_ms = 0
        self._direction = 1

    def stop(self) -> None:
        self.is_playing = False
        self.just_finished = False
        self._elapsed_ms = 0

    def advance(self) -> Frame | None:
        """Advance exactly one frame. Useful for tests and dev tools."""
        self.just_finished = False
        if self.current_animation is None or not self.is_playing:
            return self.current_frame
        self._advance_index()
        return self.current_frame

    def tick(self, delta_ms: int) -> Frame | None:
        """Advance playback by elapsed wall-clock milliseconds."""
        if delta_ms < 0:
            raise ValueError("delta_ms cannot be negative")

        self.just_finished = False
        remaining = delta_ms

        while self.is_playing and self.current_frame is not None:
            frame = self.current_frame
            time_left = frame.duration_ms - self._elapsed_ms
            if remaining < time_left:
                self._elapsed_ms += remaining
                break

            remaining -= time_left
            self._elapsed_ms = 0
            self._advance_index()

        return self.current_frame

    def _advance_index(self) -> None:
        animation = self.current_animation
        if animation is None:
            return

        count = len(animation.frames)
        if count == 1:
            if animation.mode is PlaybackMode.ONCE:
                self.is_playing = False
                self.just_finished = True
            return

        if animation.mode is PlaybackMode.LOOP:
            self.frame_index = (self.frame_index + 1) % count
            return

        if animation.mode is PlaybackMode.ONCE:
            if self.frame_index >= count - 1:
                self.is_playing = False
                self.just_finished = True
            else:
                self.frame_index += 1
            return

        next_index = self.frame_index + self._direction
        if next_index >= count:
            self._direction = -1
            next_index = count - 2
        elif next_index < 0:
            self._direction = 1
            next_index = 1
        self.frame_index = next_index
