from .animation import Animation, PlaybackMode
from .frame import Frame


# Learning note:
# AnimationPlayer owns playback STATE, not rendering.
# It remembers which Animation is active, which frame we are on,
# how much time has elapsed inside that frame, and which direction a
# ping-pong animation is travelling.
#
# The app/runtime repeatedly calls tick(delta_ms).
# The player updates its frame_index, and Pet notices when current_frame
# changes and asks the backend to show that image.
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
        # Starting an animation resets playback to its first frame.
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

        # We accumulate real elapsed time rather than sleeping here.
        # That keeps the animation engine independent from GTK/GLib and also
        # lets a single large tick advance across more than one short frame.
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
        """Apply the current Animation's playback rule to frame_index."""
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
            # Example with 3 frames: 0 -> 1 -> 2 -> 0 -> ...
            self.frame_index = (self.frame_index + 1) % count
            return

        if animation.mode is PlaybackMode.ONCE:
            # Advance until the last frame, then mark the animation finished.
            if self.frame_index >= count - 1:
                self.is_playing = False
                self.just_finished = True
            else:
                self.frame_index += 1
            return

        # PING_PONG reverses direction at either end:
        # 0 -> 1 -> 2 -> 1 -> 0 -> 1 -> ...
        next_index = self.frame_index + self._direction
        if next_index >= count:
            self._direction = -1
            next_index = count - 2
        elif next_index < 0:
            self._direction = 1
            next_index = 1
        self.frame_index = next_index
