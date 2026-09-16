class ClickTracker:
    """Recognize single/double clicks without trusting platform click counts.

    Learning note:
        Some desktop/input stacks do not report multi-click counts consistently,
        especially when multiple gesture controllers share the same pointer.
        Deskling therefore tracks the previous completed click itself.

        first release -> 1
        second nearby release within the time window -> 2

    The tracker is platform-independent and easy to unit test. GTK only supplies
    timestamp/coordinates; this class decides whether the sequence is a double.
    """

    def __init__(
        self,
        *,
        double_click_ms: float = 450.0,
        max_distance_px: float = 18.0,
    ) -> None:
        if double_click_ms <= 0:
            raise ValueError("double_click_ms must be greater than zero")
        if max_distance_px < 0:
            raise ValueError("max_distance_px cannot be negative")

        self.double_click_ms = double_click_ms
        self.max_distance_px = max_distance_px
        self._last_timestamp_ms: float | None = None
        self._last_x = 0.0
        self._last_y = 0.0

    def register(self, timestamp_ms: float, x: float, y: float) -> int:
        """Record one completed click and return 1 (single) or 2 (double)."""
        if timestamp_ms < 0:
            raise ValueError("timestamp_ms cannot be negative")

        previous = self._last_timestamp_ms
        if previous is not None:
            elapsed_ms = timestamp_ms - previous
            dx = x - self._last_x
            dy = y - self._last_y
            distance_squared = (dx * dx) + (dy * dy)
            max_distance_squared = self.max_distance_px * self.max_distance_px

            if (
                0 <= elapsed_ms <= self.double_click_ms
                and distance_squared <= max_distance_squared
            ):
                self.reset()
                return 2

        self._last_timestamp_ms = timestamp_ms
        self._last_x = x
        self._last_y = y
        return 1

    def reset(self) -> None:
        """Forget any pending first click, for example when a drag begins."""
        self._last_timestamp_ms = None
        self._last_x = 0.0
        self._last_y = 0.0
