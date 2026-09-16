from pathlib import Path

from desktoppet import NullBackend, Pet, load_manifest


EXAMPLE = Path(__file__).parents[1] / "examples" / "boo"


def test_boo_manifest_uses_a_different_feature_mix() -> None:
    manifest = load_manifest(EXAMPLE)

    assert manifest.pet.name == "Boo"
    assert set(manifest.animations) == {"idle", "blink", "spook"}
    assert manifest.roam_behavior is None
    assert manifest.idle_behavior is not None
    assert manifest.interaction is not None
    assert manifest.interaction.click_animation == "blink"
    assert manifest.interaction.double_click_animation == "spook"


def test_boo_runs_without_sdk_specific_code() -> None:
    manifest = load_manifest(EXAMPLE)
    backend = NullBackend()
    pet = Pet(manifest, backend)

    assert pet.state == "idle"
    assert backend.last_frame.name == "idle_01.svg"

    pet.handle_click(1)
    assert pet.state == "reaction"
    assert backend.last_frame.name == "blink.svg"

    pet.tick(250)
    assert pet.state == "idle"

    pet.handle_click(2)
    assert pet.state == "reaction"
    assert backend.last_frame.name == "spook.svg"
