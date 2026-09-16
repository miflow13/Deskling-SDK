from pathlib import Path

from desktoppet.config import load_manifest, manifest_to_toml
from desktoppet.studio import edit_pet_settings, export_manifest_package


ROOT = Path(__file__).resolve().parents[1]
BOO = ROOT / "examples" / "boo"


def test_manifest_writer_round_trips_boo(tmp_path: Path) -> None:
    manifest = load_manifest(BOO)
    project = tmp_path / "boo-copy"
    project.mkdir()
    (project / "pet.toml").write_text(manifest_to_toml(manifest), encoding="utf-8")

    for animation in manifest.animations.values():
        for frame in animation.frames:
            source = manifest.root / frame.file
            target = project / frame.file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())

    loaded = load_manifest(project)
    assert loaded.pet == manifest.pet
    assert loaded.animations == manifest.animations
    assert loaded.transitions == manifest.transitions
    assert loaded.interaction == manifest.interaction
    assert loaded.idle_behavior == manifest.idle_behavior
    assert loaded.roam_behavior == manifest.roam_behavior


def test_native_studio_edits_metadata_without_changing_behavior() -> None:
    manifest = load_manifest(BOO)
    edited = edit_pet_settings(
        manifest,
        name="Boo Deluxe",
        width=56,
        height=52,
        scale=3.0,
    )

    assert edited.pet.name == "Boo Deluxe"
    assert edited.pet.width == 56
    assert edited.pet.height == 52
    assert edited.pet.scale == 3.0
    assert edited.animations == manifest.animations
    assert edited.transitions == manifest.transitions
    assert edited.interaction == manifest.interaction
    assert edited.idle_behavior == manifest.idle_behavior


def test_native_studio_exports_runnable_deskling(tmp_path: Path) -> None:
    manifest = load_manifest(BOO)
    edited = edit_pet_settings(
        manifest,
        name="Studio Boo",
        width=48,
        height=48,
        scale=2.5,
    )

    package = export_manifest_package(edited, tmp_path / "studio-boo.deskling")
    loaded = load_manifest(package)

    assert loaded.pet.name == "Studio Boo"
    assert loaded.pet.scale == 2.5
    assert set(loaded.animations) == set(manifest.animations)
    assert loaded.interaction == manifest.interaction
