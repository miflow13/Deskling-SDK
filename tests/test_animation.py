from pathlib import Path

from desktoppet.animation import Animation, AnimationPlayer, Frame, PlaybackMode


def make_animation(mode: PlaybackMode) -> Animation:
    return Animation(
        "test",
        [Frame(Path("a.png"), 100), Frame(Path("b.png"), 100), Frame(Path("c.png"), 100)],
        mode,
    )


def test_loop_wraps_to_first_frame() -> None:
    player = AnimationPlayer()
    player.play(make_animation(PlaybackMode.LOOP))
    player.tick(300)
    assert player.frame_index == 0
    assert player.is_playing


def test_once_stops_on_last_frame() -> None:
    player = AnimationPlayer()
    player.play(make_animation(PlaybackMode.ONCE))
    player.tick(300)
    assert player.frame_index == 2
    assert not player.is_playing
    assert player.just_finished


def test_pingpong_reverses_at_edges() -> None:
    player = AnimationPlayer()
    player.play(make_animation(PlaybackMode.PING_PONG))
    assert [player.advance().path.name for _ in range(5)] == ["b.png", "c.png", "b.png", "a.png", "b.png"]
