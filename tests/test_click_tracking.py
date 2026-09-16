from desktoppet.interaction import ClickTracker


def test_click_tracker_recognizes_nearby_double_click() -> None:
    tracker = ClickTracker(double_click_ms=450, max_distance_px=18)

    assert tracker.register(1000, 10, 10) == 1
    assert tracker.register(1300, 14, 13) == 2


def test_click_tracker_restarts_after_timeout() -> None:
    tracker = ClickTracker(double_click_ms=450, max_distance_px=18)

    assert tracker.register(1000, 10, 10) == 1
    assert tracker.register(1501, 10, 10) == 1


def test_click_tracker_requires_nearby_position() -> None:
    tracker = ClickTracker(double_click_ms=450, max_distance_px=18)

    assert tracker.register(1000, 10, 10) == 1
    assert tracker.register(1200, 40, 40) == 1


def test_click_tracker_reset_forgets_pending_click() -> None:
    tracker = ClickTracker()

    assert tracker.register(1000, 10, 10) == 1
    tracker.reset()
    assert tracker.register(1100, 10, 10) == 1
