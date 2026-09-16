from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import tempfile

from desktoppet.config import PetManifest, PetSettings, validate_manifest
from desktoppet.config.writer import manifest_to_toml
from desktoppet.package import pack_pet


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


def export_manifest_package(manifest: PetManifest, output: str | Path) -> Path:
    """Export a manifest and its referenced assets through the normal packer."""
    validate_manifest(manifest)
    destination = Path(output)

    with tempfile.TemporaryDirectory(prefix="deskling-studio-") as temp_name:
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
