from pathlib import Path

from desktoppet import Direction, NullBackend, Pet, load_manifest


EXAMPLE = Path(__file__).parents[1] / "examples" / "slime"


def test_example_manifest_loads() -> None:
    manifest = load_manifest(EXAMPLE)
    assert manifest.pet.name == "Slime"
    assert set(manifest.animations) == {
        "idle",
        "blink",
        "love",
        "walk_left",
        "walk_right",
    }
    assert manifest.roam_behavior is not None
    assert manifest.roam_behavior.speed_px_s == 90
    assert manifest.interaction is not None
    assert manifest.interaction.click_animation == "blink"
    assert manifest.interaction.double_click_animation == "love"


def test_pet_renders_default_frame_and_reaction_returns_idle() -> None:
    manifest = load_manifest(EXAMPLE)
    backend = NullBackend()
    pet = Pet(manifest, backend)
    assert backend.last_frame.name == "idle_01.svg"

    pet.react("blink")
    assert pet.state == "reaction"
    pet.tick(240)
    assert pet.state == "idle"
    assert backend.last_frame.name == "idle_01.svg"


def test_configured_click_and_double_click_reactions() -> None:
    manifest = load_manifest(EXAMPLE)
    backend = NullBackend()
    pet = Pet(manifest, backend)
    seen: list[tuple[str, int | None]] = []

    pet.on("pet.clicked")(
        lambda event: seen.append((event.name, event.data.get("clicks")))
    )
    pet.on("pet.double_clicked")(
        lambda event: seen.append((event.name, event.data.get("clicks")))
    )

    pet.handle_click(1, x=8, y=10)
    assert pet.state == "reaction"
    assert backend.last_frame.name == "blink.svg"
    assert seen[-1] == ("pet.clicked", 1)

    pet.tick(240)
    pet.handle_click(2, x=8, y=10)
    assert pet.state == "reaction"
    assert backend.last_frame.name == "love.svg"
    assert seen[-2:] == [
        ("pet.clicked", 2),
        ("pet.double_clicked", None),
    ]


def test_click_reaction_can_interrupt_roaming() -> None:
    manifest = load_manifest(EXAMPLE)
    backend = NullBackend()
    pet = Pet(manifest, backend)

    pet.move(direction=Direction.RIGHT, delta_ms=16)
    assert pet.state == "walking"

    pet.handle_click(1)
    assert pet.state == "reaction"
    assert backend.last_frame.name == "blink.svg"
