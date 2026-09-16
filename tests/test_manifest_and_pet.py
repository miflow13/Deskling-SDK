from pathlib import Path

import pytest

from desktoppet import AnimationConfig, Direction, NullBackend, Pet, load_manifest
from desktoppet.config import ManifestError


EXAMPLE = Path(__file__).parents[1] / "examples" / "slime"


def test_example_manifest_loads_as_declarative_config() -> None:
    manifest = load_manifest(EXAMPLE)
    assert manifest.schema_version == 1
    assert manifest.pet.name == "Slime"
    assert set(manifest.animations) == {
        "idle",
        "blink",
        "love",
        "walk_left",
        "walk_right",
    }

    idle = manifest.animations["idle"]
    assert isinstance(idle, AnimationConfig)
    assert idle.mode == "pingpong"
    assert idle.frames[0].file == Path("sprites/idle_01.svg")
    assert idle.frames[0].duration_ms == 350

    assert manifest.roam_behavior is not None
    assert manifest.roam_behavior.speed_px_s == 90
    assert manifest.interaction is not None
    assert manifest.interaction.click_animation == "blink"
    assert manifest.interaction.double_click_animation == "love"


def test_pet_builds_runtime_animation_and_renders_default_frame() -> None:
    manifest = load_manifest(EXAMPLE)
    backend = NullBackend()
    pet = Pet(manifest, backend)

    assert pet.animations["idle"].name == "idle"
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


def test_manifest_rejects_asset_path_escape(tmp_path: Path) -> None:
    project = tmp_path / "unsafe-pet"
    project.mkdir()
    (project / "pet.toml").write_text(
        """\
schema_version = 1

[pet]
name = "Unsafe"
width = 32
height = 32
default_animation = "idle"

[animations.idle]
mode = "loop"
frames = [
  { file = "../outside.png", duration_ms = 100 },
]
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="stay inside the pet package"):
        load_manifest(project, check_assets=False)


def test_manifest_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    project = tmp_path / "future-pet"
    project.mkdir()
    (project / "pet.toml").write_text(
        """\
schema_version = 999

[pet]
name = "Future"
width = 32
height = 32
default_animation = "idle"

[animations.idle]
mode = "loop"
frames = [
  { file = "idle.png", duration_ms = 100 },
]
""",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="Unsupported schema_version"):
        load_manifest(project, check_assets=False)
