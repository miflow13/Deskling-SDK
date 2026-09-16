from pathlib import Path

import pytest

from desktoppet.config import load_manifest, manifest_to_toml
from desktoppet.studio import (
    add_animation,
    add_frames,
    clone_manifest_to_workspace,
    create_new_pet_manifest,
    edit_pet_settings,
    export_manifest_package,
    move_frame,
    remove_frame,
    set_animation_mode,
    set_frame_duration,
)


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


def test_studio_clones_open_pet_into_isolated_workspace(tmp_path: Path) -> None:
    manifest = load_manifest(BOO)
    cloned = clone_manifest_to_workspace(manifest, tmp_path / "workspace")

    assert cloned.root != manifest.root
    assert cloned.pet == manifest.pet
    assert cloned.animations == manifest.animations
    for animation in cloned.animations.values():
        for frame in animation.frames:
            assert (cloned.root / frame.file).is_file()


def test_studio_creates_new_pet_from_first_frame(tmp_path: Path) -> None:
    manifest = create_new_pet_manifest(
        tmp_path / "new-pet",
        BOO / "sprites" / "idle_01.svg",
        name="Pebble",
        width=64,
        height=64,
        scale=2.0,
    )

    assert manifest.pet.name == "Pebble"
    assert manifest.pet.default_animation == "idle"
    assert set(manifest.animations) == {"idle"}
    assert manifest.animations["idle"].mode == "loop"
    assert len(manifest.animations["idle"].frames) == 1
    assert manifest.animations["idle"].frames[0].duration_ms == 500
    assert (manifest.root / manifest.animations["idle"].frames[0].file).is_file()


def test_studio_adds_animation_and_edits_frames(tmp_path: Path) -> None:
    manifest = create_new_pet_manifest(
        tmp_path / "new-pet",
        BOO / "sprites" / "idle_01.svg",
    )
    manifest = add_frames(
        manifest,
        "idle",
        [
            BOO / "sprites" / "idle_02.svg",
            BOO / "sprites" / "blink.svg",
        ],
        duration_ms=180,
    )

    assert len(manifest.animations["idle"].frames) == 3
    assert [frame.duration_ms for frame in manifest.animations["idle"].frames] == [
        500,
        180,
        180,
    ]

    original_last = manifest.animations["idle"].frames[2].file
    manifest = move_frame(manifest, "idle", 2, 0)
    assert manifest.animations["idle"].frames[0].file == original_last

    manifest = set_frame_duration(manifest, "idle", 0, 75)
    assert manifest.animations["idle"].frames[0].duration_ms == 75

    manifest = set_animation_mode(manifest, "idle", "pingpong")
    assert manifest.animations["idle"].mode == "pingpong"

    manifest = remove_frame(manifest, "idle", 1)
    assert len(manifest.animations["idle"].frames) == 2

    manifest = add_animation(
        manifest,
        "wave",
        [BOO / "sprites" / "spook.svg"],
        mode="once",
        duration_ms=140,
    )
    assert manifest.animations["wave"].mode == "once"
    assert manifest.animations["wave"].frames[0].duration_ms == 140
    assert (manifest.root / manifest.animations["wave"].frames[0].file).is_file()


def test_studio_rejects_removing_last_frame(tmp_path: Path) -> None:
    manifest = create_new_pet_manifest(
        tmp_path / "new-pet",
        BOO / "sprites" / "idle_01.svg",
    )

    with pytest.raises(ValueError, match="at least one frame"):
        remove_frame(manifest, "idle", 0)


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


def test_new_studio_pet_exports_and_reloads(tmp_path: Path) -> None:
    manifest = create_new_pet_manifest(
        tmp_path / "workspace",
        BOO / "sprites" / "idle_01.svg",
        name="Pebble",
    )
    manifest = add_frames(
        manifest,
        "idle",
        [BOO / "sprites" / "idle_02.svg"],
        duration_ms=220,
    )
    manifest = add_animation(
        manifest,
        "wave",
        [BOO / "sprites" / "spook.svg"],
        mode="once",
    )

    package = export_manifest_package(manifest, tmp_path / "pebble.deskling")
    loaded = load_manifest(package)

    assert loaded.pet.name == "Pebble"
    assert list(loaded.animations) == ["idle", "wave"]
    assert len(loaded.animations["idle"].frames) == 2
    assert loaded.animations["wave"].mode == "once"
