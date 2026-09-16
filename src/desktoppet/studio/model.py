from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import shutil
import tempfile
from collections.abc import Iterable

from desktoppet.config import (
    AnimationConfig,
    FrameConfig,
    PetManifest,
    PetSettings,
    validate_manifest,
)
from desktoppet.config.manifest import PlaybackModeName
from desktoppet.config.writer import manifest_to_toml
from desktoppet.package import pack_pet


_ANIMATION_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_PLAYBACK_MODES = {"once", "loop", "pingpong"}


def edit_pet_settings(
    manifest: PetManifest,
    *,
    name: str,
    width: int,
    height: int,
    scale: float,
) -> PetManifest:
    """Return a validated manifest with edited basic pet metadata."""
    settings = PetSettings(
        name=name,
        width=width,
        height=height,
        scale=scale,
        default_state=manifest.pet.default_state,
        default_animation=manifest.pet.default_animation,
    )
    edited = replace(manifest, pet=settings)
    validate_manifest(edited)
    return edited


def clone_manifest_to_workspace(
    manifest: PetManifest, workspace: str | Path
) -> PetManifest:
    """Copy a pet's referenced assets into an isolated Studio workspace."""
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)

    copied: set[Path] = set()
    for animation in manifest.animations.values():
        for frame in animation.frames:
            if frame.file in copied:
                continue
            copied.add(frame.file)
            source = manifest.root / frame.file
            target = root / frame.file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    cloned = replace(manifest, root=root)
    validate_manifest(cloned)
    return cloned


def _validate_animation_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise ValueError("Animation name cannot be empty")
    if not _ANIMATION_NAME_RE.fullmatch(value):
        raise ValueError(
            "Animation names may only contain letters, numbers, '_' and '-'"
        )
    return value


def _validate_mode(mode: str) -> PlaybackModeName:
    if mode not in _PLAYBACK_MODES:
        raise ValueError(f"Unsupported playback mode: {mode}")
    return mode  # type: ignore[return-value]


def _next_frame_path(root: Path, animation_name: str, source: Path) -> Path:
    suffix = source.suffix.lower() or ".png"
    directory = Path("sprites") / animation_name
    number = 1
    while True:
        candidate = directory / f"frame_{number:03d}{suffix}"
        if not (root / candidate).exists():
            return candidate
        number += 1


def _copy_frame(root: Path, animation_name: str, source: str | Path) -> FrameConfig:
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError(f"Frame file does not exist: {source_path}")
    relative = _next_frame_path(root, animation_name, source_path)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    return FrameConfig(file=relative, duration_ms=120)


def create_new_pet_manifest(
    workspace: str | Path,
    first_frame: str | Path,
    *,
    name: str = "My Deskling",
    width: int = 128,
    height: int = 128,
    scale: float = 2.0,
) -> PetManifest:
    """Create a valid new pet with one editable idle animation."""
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    frame = _copy_frame(root, "idle", first_frame)
    frame = replace(frame, duration_ms=500)

    manifest = PetManifest(
        schema_version=1,
        root=root,
        pet=PetSettings(
            name=name,
            width=width,
            height=height,
            scale=scale,
            default_state="idle",
            default_animation="idle",
        ),
        animations={
            "idle": AnimationConfig(name="idle", frames=(frame,), mode="loop")
        },
        transitions={
            "idle": {"reaction", "dragging"},
            "reaction": {"idle", "dragging"},
            "dragging": {"idle"},
        },
    )
    validate_manifest(manifest)
    return manifest


def add_animation(
    manifest: PetManifest,
    name: str,
    sources: Iterable[str | Path],
    *,
    mode: str = "once",
    duration_ms: int = 120,
) -> PetManifest:
    """Add an animation and import its initial frame files."""
    animation_name = _validate_animation_name(name)
    playback_mode = _validate_mode(mode)
    if animation_name in manifest.animations:
        raise ValueError(f"Animation {animation_name!r} already exists")
    if duration_ms <= 0:
        raise ValueError("Frame duration must be greater than zero")

    frames = tuple(
        replace(
            _copy_frame(manifest.root, animation_name, source),
            duration_ms=duration_ms,
        )
        for source in sources
    )
    if not frames:
        raise ValueError("Choose at least one frame for the animation")

    animations = dict(manifest.animations)
    animations[animation_name] = AnimationConfig(
        name=animation_name,
        frames=frames,
        mode=playback_mode,
    )
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def add_frames(
    manifest: PetManifest,
    animation_name: str,
    sources: Iterable[str | Path],
    *,
    duration_ms: int = 120,
) -> PetManifest:
    """Import one or more frames at the end of an existing animation."""
    if duration_ms <= 0:
        raise ValueError("Frame duration must be greater than zero")
    animation = manifest.animations.get(animation_name)
    if animation is None:
        raise ValueError(f"Unknown animation: {animation_name}")

    new_frames = tuple(
        replace(
            _copy_frame(manifest.root, animation_name, source),
            duration_ms=duration_ms,
        )
        for source in sources
    )
    if not new_frames:
        raise ValueError("Choose at least one frame")

    updated = replace(animation, frames=animation.frames + new_frames)
    animations = dict(manifest.animations)
    animations[animation_name] = updated
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def remove_frame(
    manifest: PetManifest, animation_name: str, index: int
) -> PetManifest:
    """Remove one frame while keeping every animation runnable."""
    animation = manifest.animations.get(animation_name)
    if animation is None:
        raise ValueError(f"Unknown animation: {animation_name}")
    if len(animation.frames) <= 1:
        raise ValueError("An animation must keep at least one frame")
    if index < 0 or index >= len(animation.frames):
        raise IndexError("Frame index out of range")

    frames = list(animation.frames)
    frames.pop(index)
    animations = dict(manifest.animations)
    animations[animation_name] = replace(animation, frames=tuple(frames))
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def move_frame(
    manifest: PetManifest,
    animation_name: str,
    index: int,
    new_index: int,
) -> PetManifest:
    """Move one animation frame to a new position."""
    animation = manifest.animations.get(animation_name)
    if animation is None:
        raise ValueError(f"Unknown animation: {animation_name}")
    count = len(animation.frames)
    if not 0 <= index < count or not 0 <= new_index < count:
        raise IndexError("Frame index out of range")
    if index == new_index:
        return manifest

    frames = list(animation.frames)
    frame = frames.pop(index)
    frames.insert(new_index, frame)
    animations = dict(manifest.animations)
    animations[animation_name] = replace(animation, frames=tuple(frames))
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def set_frame_duration(
    manifest: PetManifest,
    animation_name: str,
    index: int,
    duration_ms: int,
) -> PetManifest:
    """Set one frame's authored duration in milliseconds."""
    if duration_ms <= 0:
        raise ValueError("Frame duration must be greater than zero")
    animation = manifest.animations.get(animation_name)
    if animation is None:
        raise ValueError(f"Unknown animation: {animation_name}")
    if index < 0 or index >= len(animation.frames):
        raise IndexError("Frame index out of range")

    frames = list(animation.frames)
    frames[index] = replace(frames[index], duration_ms=duration_ms)
    animations = dict(manifest.animations)
    animations[animation_name] = replace(animation, frames=tuple(frames))
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def set_animation_mode(
    manifest: PetManifest, animation_name: str, mode: str
) -> PetManifest:
    """Change one animation's playback mode."""
    animation = manifest.animations.get(animation_name)
    if animation is None:
        raise ValueError(f"Unknown animation: {animation_name}")
    playback_mode = _validate_mode(mode)
    animations = dict(manifest.animations)
    animations[animation_name] = replace(animation, mode=playback_mode)
    edited = replace(manifest, animations=animations)
    validate_manifest(edited)
    return edited


def export_manifest_package(manifest: PetManifest, output: str | Path) -> Path:
    """Export a manifest and its referenced assets through the normal packer."""
    validate_manifest(manifest)
    destination = Path(output)

    with tempfile.TemporaryDirectory(prefix="deskling-studio-export-") as temp_name:
        project = Path(temp_name)
        (project / "pet.toml").write_text(
            manifest_to_toml(manifest),
            encoding="utf-8",
        )

        copied: set[Path] = set()
        for animation in manifest.animations.values():
            for frame in animation.frames:
                if frame.file in copied:
                    continue
                copied.add(frame.file)
                source = manifest.root / frame.file
                target = project / frame.file
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

        return pack_pet(project, destination)
