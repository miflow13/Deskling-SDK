from pathlib import Path

from desktoppet import NullBackend, Pet, load_manifest


EXAMPLE = Path(__file__).parents[1] / "examples" / "slime"


def test_example_manifest_loads() -> None:
    manifest = load_manifest(EXAMPLE)
    assert manifest.pet.name == "Slime"
    assert set(manifest.animations) == {"idle", "blink"}


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
